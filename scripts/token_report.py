#!/usr/bin/env python3
"""Token and work report for one engagement run, to compare two runs (A/B).

    python3 scripts/token_report.py <session-folder> [--engagement-dir <test-run-folder>]

<session-folder> is the Claude Code project folder of the orchestrating session:
    ~/.claude/projects/<project>/<session-id>/        (with subagents/*.jsonl)
    ~/.claude/projects/<project>/<session-id>.jsonl   (the orchestrator's own log, next to the folder)
Reports, per participant (Orchestrator, Context-collector, Planner, Runners): turns, cache reads,
cache writes, uncached input, output, and a cost-equivalent. With --engagement-dir it also counts the
work done (charters, Test Notes lines, bugs, problems) so the two runs can be compared on equal work.

Cost-equivalent = tokens weighted by list-price ratios (input 1x, output 5x, cache read 0.1x, 5-min cache
write 1.25x, 1-hour cache write 2x), with Opus counted at 2x Sonnet. Use it to compare runs, not as a bill.
Output tokens in a transcript are a streaming snapshot and are undercounted; the same bias is in both runs.
"""
import argparse
import collections
import glob
import json
import re
import sys
from pathlib import Path

FAMILY_WEIGHT = {"opus": 2.0, "other": 1.0}


def load(path):
    msgs, order = {}, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                o = json.loads(line)
            except ValueError:
                continue
            m = o.get("message") or {}
            if o.get("type") != "assistant" or not m.get("usage"):
                continue
            mid = m.get("id") or o.get("uuid")
            u = m["usage"]
            cc = u.get("cache_creation") or {}
            w5 = cc.get("ephemeral_5m_input_tokens", 0)
            w1 = cc.get("ephemeral_1h_input_tokens", 0)
            if not (w5 or w1):
                w5 = u.get("cache_creation_input_tokens", 0)
            content = m.get("content") if isinstance(m.get("content"), list) else []
            rec = dict(model=m.get("model") or "", inp=u.get("input_tokens", 0), cr=u.get("cache_read_input_tokens", 0),
                       w5=w5, w1=w1, out=u.get("output_tokens", 0),
                       tools=sum(1 for b in content if b.get("type") == "tool_use"))
            if mid not in msgs:
                order.append(mid)
            if mid not in msgs or rec["out"] >= msgs[mid]["out"]:
                msgs[mid] = rec
    return [msgs[i] for i in order]


def cost(rows):
    total = 0.0
    for r in rows:
        w = FAMILY_WEIGHT["opus"] if "opus" in r["model"] else FAMILY_WEIGHT["other"]
        total += w * (r["inp"] + 5 * r["out"] + 0.1 * r["cr"] + 1.25 * r["w5"] + 2 * r["w1"])
    return total / 1e6


def classify(meta):
    kind = (meta.get("agentType") or "") + " " + (meta.get("description") or "")
    for key, name in (("planner", "Planner"), ("context-collector", "Context-collector"), ("session-runner", "Runners")):
        if key in kind:
            return name
    return "Other agents"


def work_counts(engagement_dir):
    out = collections.Counter()
    for f in sorted(Path(engagement_dir, "sessions").glob("TC-*.md")):
        if f.name.endswith(".handoff.md"):
            continue
        text = f.read_text(encoding="utf-8")
        out["charters"] += 1

        def section(name):
            m = re.search(rf"^## {name}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
            return m.group(1) if m else ""

        def rows(body):
            lines = [ln for ln in body.splitlines() if ln.strip().startswith("|")]
            return [ln for ln in lines if not re.match(r"^\s*\|[\s\-|:]*\|\s*$", ln)][1:]  # drop the header row

        out["notes lines"] += len([ln for ln in section("Test Notes").splitlines() if ln.strip() and not ln.startswith("environment:")])
        out["bugs"] += len([r for r in rows(section("Bugs")) if len(r.strip(" |")) > 3])
        out["problems"] += len([ln for ln in section("Problems").splitlines() if ln.strip()])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session_folder")
    ap.add_argument("--engagement-dir")
    a = ap.parse_args()
    folder = Path(a.session_folder.rstrip("/"))
    groups = collections.defaultdict(list)
    calls = collections.Counter()
    for jl in sorted(glob.glob(str(folder / "subagents" / "*.jsonl"))):
        meta_path = Path(jl.replace(".jsonl", ".meta.json"))
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        rows = load(jl)
        g = classify(meta)
        groups[g] += rows
        calls[g] += sum(r["tools"] for r in rows)
    main_log = folder.parent / (folder.name + ".jsonl")
    if main_log.exists():
        rows = load(main_log)
        groups["Orchestrator"] += rows
        calls["Orchestrator"] += sum(r["tools"] for r in rows)
    if not groups:
        sys.exit("no transcripts found under " + str(folder))
    print(f"{'participant':20}{'turns':>7}{'tool calls':>11}{'cache read':>14}{'cache write':>13}{'uncached in':>13}{'output':>10}{'cost-eq':>10}")
    total = collections.Counter()
    total_cost = 0.0
    for g in ("Orchestrator", "Context-collector", "Planner", "Runners", "Other agents"):
        rows = groups.get(g)
        if not rows:
            continue
        v = dict(t=len(rows), c=calls[g], cr=sum(r["cr"] for r in rows), cw=sum(r["w5"] + r["w1"] for r in rows),
                 i=sum(r["inp"] for r in rows), o=sum(r["out"] for r in rows), k=cost(rows))
        print(f"{g:20}{v['t']:>7}{v['c']:>11}{v['cr']:>14,}{v['cw']:>13,}{v['i']:>13,}{v['o']:>10,}{v['k']:>10.2f}")
        for key in ("t", "c", "cr", "cw", "i", "o"):
            total[key] += v[key]
        total_cost += v["k"]
    print(f"{'TOTAL':20}{total['t']:>7}{total['c']:>11}{total['cr']:>14,}{total['cw']:>13,}{total['i']:>13,}{total['o']:>10,}{total_cost:>10.2f}")
    if a.engagement_dir:
        w = work_counts(a.engagement_dir)
        print("\nwork done: " + ", ".join(f"{k}={w[k]}" for k in ("charters", "notes lines", "bugs", "problems")))
        if w["charters"]:
            print(f"cost-eq per charter: {total_cost / w['charters']:.2f}")


if __name__ == "__main__":
    main()
