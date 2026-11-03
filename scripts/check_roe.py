#!/usr/bin/env python3
"""Check the project's rules-of-engagement.md against the config.

Usage:
    check_roe.py --config <config.yaml> [--env NAME] [--rules FILE] [--template FILE]

The rules file is <config folder>/rules-of-engagement.md unless --rules is given. It must:
  - have a 'rules_version: N' line,
  - have a '## <kind>' section for every safety.kind the config uses (with --env, only that
    environment's kind), each with '### Allowed', '### Sandboxed' and '### Forbidden' lists,
  - have a '## Modifiers' section that mentions allow_destructive and allow_account_creation,
  - start every rule with a unique ID ('- R-01 ...'); an empty list is written '- (none)'.
It does not judge whether the rules are sensible: the file belongs to the user.
A WARN is printed when the plugin's template has a newer rules_version than the project's file.

Prints one line per problem ('ERROR ...' or 'WARN ...'), then 'OK' when there is no ERROR.
Exit codes: 0 = no ERROR, 1 = at least one ERROR, 2 = could not run.
"""
import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Missing dependency 'pyyaml'. Run: pip install pyyaml jsonschema", file=sys.stderr)
    sys.exit(2)

SCRIPTS = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = (SCRIPTS.parent / "skills" / "setup" / "references"
                    / "workspace-template" / "rules-of-engagement.md")
LISTS = ("Allowed", "Sandboxed", "Forbidden")
EXTRA_SECTIONS = ("Modifiers", "General")
VERSION_RE = re.compile(r"^rules_version:\s*(\d+)\s*$", re.M)
ITEM_RE = re.compile(r"^[-*]\s+(.*)$")
ID_RE = re.compile(r"^(R-\d+)\b")


def parse(text):
    """Return (sections, items). sections: {h2: {"lines": [...], "lists": {h3: [item numbers]}}}.
    items: [(line number, h2, h3, text)] for every bullet. Fenced code blocks are skipped."""
    sections, items = {}, []
    h2 = h3 = None
    in_fence = False
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## "):
            h2, h3 = line[3:].strip(), None
            sections.setdefault(h2, {"lines": [], "lists": {}})
            continue
        if line.startswith("### "):
            h3 = line[4:].strip()
            if h2 is not None:
                sections[h2]["lists"].setdefault(h3, [])
            continue
        if h2 is None:
            continue
        sections[h2]["lines"].append(line)
        match = ITEM_RE.match(line.strip()) if not raw.startswith((" ", "\t")) else None
        if match:
            items.append((number, h2, h3, match.group(1).strip()))
            if h3 is not None:
                sections[h2]["lists"][h3].append(number)
    return sections, items


def version_of(text):
    match = VERSION_RE.search(text or "")
    return int(match.group(1)) if match else None


def validate(text, kinds, template_text=None):
    """Return (errors, warnings) for the rules file text and the set of safety kinds in use."""
    errors, warnings = [], []
    version = version_of(text)
    if version is None:
        errors.append("no 'rules_version: N' line near the top of the file")
    sections, items = parse(text)

    checked = set(EXTRA_SECTIONS)
    for kind in sorted(kinds):
        checked.add(kind)
        if kind not in sections:
            errors.append(f"no '## {kind}' section (an environment in the config has safety.kind: {kind})")
            continue
        for name in LISTS:
            numbers = sections[kind]["lists"].get(name)
            if numbers is None:
                errors.append(f"section '## {kind}' has no '### {name}' list")
            elif not numbers:
                errors.append(f"'### {name}' under '## {kind}' is empty; write '- (none)' if it has no rules")

    if "Modifiers" not in sections:
        errors.append("no '## Modifiers' section")
    else:
        body = "\n".join(sections["Modifiers"]["lines"])
        for field in ("allow_destructive", "allow_account_creation"):
            if field not in body:
                errors.append(f"'## Modifiers' does not mention {field}")

    seen = {}
    for number, h2, _h3, item in items:
        if h2 not in checked:
            continue
        if item.startswith("(none)"):
            continue
        match = ID_RE.match(item)
        if not match:
            errors.append(f"line {number}: \"{item[:40]}\" has no rule ID; start it with '- R-NN' "
                          f"(or write '- (none)' for an empty list)")
            continue
        seen.setdefault(match.group(1), []).append(number)
    for rule_id, numbers in sorted(seen.items()):
        if len(numbers) > 1:
            errors.append(f"rule ID {rule_id} is used more than once (lines {', '.join(map(str, numbers))})")

    template_version = version_of(template_text)
    if version is not None and template_version is not None and template_version > version:
        warnings.append(f"the plugin's template is at rules_version {template_version} and this file at {version}; "
                        f"the template may have newer defaults you want to compare")
    return errors, warnings


def kinds_in_config(config_path, env_name):
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    envs = cfg["environments"]
    if env_name:
        envs = [e for e in envs if e["name"] == env_name]
        if not envs:
            raise ValueError(f"no environment named '{env_name}'")
    return {e["safety"]["kind"] for e in envs}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check rules-of-engagement.md against the config")
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--env")
    ap.add_argument("--rules", type=Path)
    ap.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    args = ap.parse_args(argv)

    try:
        kinds = kinds_in_config(args.config, args.env)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        print(f"Cannot read the config: {error}", file=sys.stderr)
        return 2
    rules = args.rules or args.config.resolve().parent / "rules-of-engagement.md"
    if not rules.exists():
        print("ERROR rules-of-engagement.md is missing; run /exploratory-testing:setup "
              "(it adds the file and leaves your other files alone)")
        return 1
    template_text = args.template.read_text(encoding="utf-8") if args.template.exists() else None
    errors, warnings = validate(rules.read_text(encoding="utf-8-sig"), kinds, template_text)
    for message in errors:
        print(f"ERROR {message}")
    for message in warnings:
        print(f"WARN {message}")
    if not errors:
        print("OK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
