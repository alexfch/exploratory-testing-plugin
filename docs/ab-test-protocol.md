# A/B protocol: did the token rework keep the work the same?

Goal: the reworked plugin uses at most one third of the tokens of the baseline run **for the same work**:
the same context, the same charters, the same sessions, the same amount of interaction with the app, the same
observations, the same bugs.

## What is compared

- **A (baseline):** the existing 12-charter run on `larder-ios-app` (the session folder
  `~/.claude/projects/-Users-mult2-Projects-larder-ios-app/53bd555b-05a2-4a5e-9ddd-743aba964aef/` and its
  engagement folder). Nothing is re-run for it.
- **B (candidate):** the reworked plugin (working tree of this repo) run on the **same charters**.

Different charters would be different work, so B does not plan its own charters in the execution comparison.
The planner is compared separately (step 4).

## Steps

1. **Pick 4 charters from A** that differ in kind (for example one that found several bugs, one that found
   none, one long, one short). Note for each: tool calls, Test Notes lines, bugs.
2. **Replay them in B.** In `larder-ios-app`, start a new run (the orchestrator creates the run folder), then
   before the first Runner leg: copy `engagement.md` (context, scope, rules) from A's run folder, create
   `sessions/TC-1.md` ... `TC-4.md` from A's charters (Test Charter section only; empty notes, bugs and
   problems) with a first line `Target: mobile` added to each Setup row, and set `state.json` to
   `phase: execute`, `status: not-started`, `round: 1`, `leg: 1`, `session_spent: 0`. Same app build, same
   simulator, same rules of engagement. Stop the run after TC-4.
3. **Measure both:**
   ```bash
   python3 scripts/token_report.py <session-folder-of-A>
   python3 scripts/token_report.py <session-folder-of-B> --engagement-dir <B run folder>
   ```
   Compare the Runners row per charter (A's total divided by its 12 charters, or A's four chosen charters if you
   split A's Runner transcripts by their descriptions).
4. **Planner check (separate, cheap).** Run the new Planner for round 2 and round 5 of a fresh engagement and
   check that `plan.md` is consistent (strategy kept, history rows, coverage map, backlog) and the charters
   continue one path. Compare its cost with A's Planner (90 turns for all 12 rounds).

## Pass criteria

| Measure | Pass |
|---|---|
| Cost-equivalent of the Runners per charter | B <= 1/3 of A |
| Total cost-equivalent (all participants) | B <= 1/3 of A |
| Tool calls per charter | within +-20% of A (the work is the same) |
| Test Notes lines per charter | within +-20% of A |
| Bugs | every bug of A's four charters is found again in B, or explained (a real difference) |
| New bugs in B | allowed; list them |

Runs vary, so a miss on one charter is not a failure; a pattern across the four is. If the bug count drops,
check first whether the leg handoffs lost something (look for "Open threads" that were never continued) and
whether the compact page source hid an element the Runner needed (look for a Runner Grep-ing the full XML a lot).

## Caveats

- A paused for rate limits, which forced cold cache rewrites that B may not suffer. Look at cache writes and
  not only the total.
- Output tokens in the transcripts are a streaming snapshot; both runs are undercounted the same way.
- To run B the plugin must be loaded from this repo (for example `claude --plugin-dir <this repo>` started in
  `larder-ios-app`), not the previously installed copy.
