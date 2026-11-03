---
name: exploratory-testing
description: Runs a full multi-agent exploratory testing engagement on a mobile or web application, from context collection through charter planning and test sessions to a report. Use only when the user explicitly asks to run exploratory testing, an exploratory test session or engagement, or to test an app or feature hands-on and find bugs in it (e.g. "run exploratory testing on the checkout flow", "explore this iOS build and find bugs", "start a test engagement for release 4.2"). Needs a runnable app (simulator, device or URL) or a repo to build it from. Do NOT use for general questions about testing, test advice, or "what should I check" brainstorming (answer directly); for writing unit, automated or scripted test cases; for code review; or for reviewing a single bug report.
---

# Exploratory Testing (Orchestrator)

Runs a full exploratory testing engagement — from collecting context through session execution to reporting. This skill is an **orchestrator** – it dispatches context collection, planning, execution and reporting between subagents. The deep-perspective work happens in the subagents (agents/<id>.md), not in this skill's main thread. This is a **pipeline skill**: the three phases below (Preparation → Testing → Report) run in order, and decisions made early (mode, scope) must be honored throughout.

---

## State values (state.json)
- phase: context | plan | execute | report
- status: not-started | in-progress | need-decision | session-out-of-budget | session-done | run-done
- round: integer, starts at 1, +1 after each runner turn finishes
- budget_total, budget_spent: integers (tool calls)

**Write-ahead rule:** Update `state.json` BEFORE every spawn, resume or phase change, never after.
- Before spawning/resuming: set "status": "in-progress" and "active_agent": "<agent name>".
- When an agent returns need-decision: set "status": "need-decision" and copy its QUESTION into "pending_question" before asking the user.
- When the user answers: clear "pending_question".

## Phase 0: Resume or start

Run this first on every invocation, AND any time you notice you no longer know <engagement_dir> or the modes (for example, after context compaction).

**0.1 Find unfinished runs.**
Run:
    for f in "${CLAUDE_PROJECT_DIR}"/exploratory-testing/execution/test-run-*/state.json; do
      [ -f "$f" ] && python3 -c "import json,sys;s=json.load(open(sys.argv[1]));print(sys.argv[1], s['phase'], s['status'], s['round']) if s['phase']!='done' else None" "$f"
    done | sort
(Folder names contain sortable timestamps, so the last line per project is the latest run.)

**0.2 Decide.**
- No unfinished runs → go to Phase 1 (new run).
- The user explicitly asked for a new run → go to Phase 1. Leave old runs untouched.
- Unfinished runs exist:
  - IF `human-in-the-loop`: show the user the project, start time, phase and round of each, and ask: resume one, or start a new run?
  - IF `agent-only`: resume the latest unfinished run for the project the user named. If no project was named and there is exactly one unfinished run, resume it. Otherwise ask.

**0.3 Restore.**
Read the chosen state.json. Restore <engagement_dir> the involvement and outcome modes, and round from it. Do not re-run Phase 1. Do not create a new test-run folder.

**0.4 Recover the interrupted turn.**
Agents from before the restart cannot be resumed. If status is in-progress or need-decision:
- Charge the full agent Budget (60) to budget_spent; its TOOL_CALLS_USED is lost.
- Then repair the state by phase:

| phase | Check on disk | Set state to | Then |
|---|---|---|---|
| context | — | context / not-started | Re-run Phase 2 (the context-collector updates existing docs) |
| plan | `sessions/TC-<NN>.md` exists AND its Test Charter section is filled | execute / not-started | Continue Phase 3 |
| plan | file missing or charter empty | plan / not-started | Continue Phase 3 (spawns a fresh Planner) |
| execute | — | execute / not-started | Continue Phase 3 (spawns a fresh Runner on the same TC-<Round>) |
| report | — | report / not-started | Go to Phase 4 |

- If pending_question is not empty: ask the user that question again, and include their answer in the fresh agent's delegation prompt as:
      Earlier question: <pending_question>
      User answer: <answer>

**0.5** Tell the user in one line: "Resuming <project> run <timestamp> at <phase>, round <Round>. Budget <spent>/<total>." Then continue with the normal loop.


## Phase 1: Preparation

**1.0 Preflight (before anything else in a new run)**
Do not collect context, plan, or start any session until this passes.

1.0.1. Run exactly one command:
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/check_setup.py" --config "${CLAUDE_PROJECT_DIR}/exploratory-testing/config.yaml" [--env NAME] [--targets web,api,ios,android]`
   - Add `--env NAME` if the user named an environment.
   - Add `--targets` with only the target types this run will test, if the request says. Otherwise omit it.
1.0.2. Act on the exit code:
   - **0**: continue. Mention any `WARN` lines in one short list. Do not stop for them.
   - **1**: stop. Show only the `FAIL` lines. If the config is missing or invalid, or `safety` or `accounts` is missing, send the user to `/exploratory-testing:setup`. Unset secrets: they edit the secrets file themselves. An unreachable URL or missing tool: they fix the environment. Do not start testing and do not offer to skip a `FAIL`.
   - **2**: the script could not run (usually missing Python packages). Tell the user and stop.
   - **3**: several environments and none chosen. Ask which one (AskUserQuestion, using the names the script printed), then run again with `--env`. If you cannot ask, stop and say a choice is needed.
1.0.3. Do not repeat these checks yourself, and never open the secrets file.

**1.1 Create the test run.**
- Run:
    ts=$(date +%Y-%m-%dT%H-%M-%S)
    cp -R "${CLAUDE_SKILL_DIR}/references/test-run-template" "exploratory-testing/execution/test-run-$ts"
    cp "${CLAUDE_SKILL_DIR}/references/session-template.md" "exploratory-testing/execution/test-run-$ts/session-template.md"
- <engagement_dir> = ${CLAUDE_PROJECT_DIR}/exploratory-testing/execution/test-run-$ts (absolute).
- Take the timestamp only from the date command. Never type one yourself.
- Never rename or modify anything under ${CLAUDE_SKILL_DIR}.

**1.2 Learn about the modes.**
- Invoke the `exploratory-testing:shared-context` skill. It explains the Involvement and Outcome modes.
- Take the active modes for the current engagement from the user message. If not provided, use defaults: **Involvement mode - "human-in-the-loop"**, and **Outcome mode - "test-only"**.
- Hold both modes for the rest of the engagement — they govern context collection, execution, and reporting.

**1.3 Identify testing purpose.**
- Use "Find important problems in the change and its impact radius" as the default testing purpose.

Follow the branch matching the involvement mode.
**IF `agent-only`:**
- If the user provided a specific testing purpose (other than the default one), take it as the testing goal. Otherwise stick to the default one.

**IF `human-in-the-loop`:**
- If the user did not provide the testing purpose, ask for it. Give a few relevant ideas based on what you know about testing purposes in exploratory testing, to help the user to figure out their version.
- If the user struggles to decide, or refuses to provide the purpose use the default one.

**1.4 Pre-fill engagement details.**
In the `<engagement_dir>/engagement.md` file:
- fill in the “Involvement mode” field with the current active involvement mode.
- fill in the “Outcome mode” fields with the current active outcome mode.
- fill in the “engagement_dir” field with the `<engagement_dir>` value.
- fill in the “context_dir” field with the `${CLAUDE_PROJECT_DIR}/exploratory-testing/context` value (absolute).
- fill in the “Purpose” field with the testing purpose.
- fill in the “Test item” section with whatever has been already provded in the user message (if anything). E.g environment name, OS, browsers, devices.

**1.5 Update state file**
- Read "Budget" from the `<engagement_dir>/engagement.md` file. Write the Budget value to `state.json` as budget_total. Set budget_spent to 0.
- Write project_name, workspace_dir, engagement_dir, context_dir, involvement and outcome into `<engagement_dir>/state.json`.

## Phase 2. Gathering context 

### 2.1 Run the subagent
- Spawn the `exploratory-testing:context-collector` agent and give it the name `context-collector`. Use this delegation prompt, filling in the values:

```
  Workspace: exploratory-testing
  Context dir: exploratory-testing/context 
  Modes: involvement=<involvement>
  Budget: 60 tool calls
  Read exploratory-testing/WORKSPACE.md first, then follow your instructions to collect the project context.
```

- Run the **write-ahead rule** now.
- Do not move to the next phase until the Context-collector finishes it's work and gets back to you with status `session-done`.
- If the Context-collector finishes with `session-out-of-budget` status, stop execution and let the user know that there was not enough budget to collect full context.

### 2.2 Collect info from the user (only if Involvement Mode is **human-in-the-loop**)
- If the Context-collector comes back with status `need-decision`:
    edit the `state.json` and set `"phase": "context"` and `"status": "need-decision"`;
    take the question from the agent response and pass it to the user.
- As the user gives the answer:
    run the **write-ahead rule** now.
    resume the existing `context-collector` agent by sending a message to `context-collector` instead of spawning a new one. **If resuming fails** (for example, the session was restarted and `context-collector` is not available), spawn a new `exploratory-testing:context-collector` as descrived on p.2.1.
- Run p.2.2 in loop until the `Context-collector` agent comes back with the status `session-done`.
- Do not move to the next phase until the Context-collector finishes it's work and gets back to you with status `session-done`.

### 2.3 Hand off to the next phase
- When `Context-collector` finishes work with status `session-done`, edit the `state.json` and set `phase: plan` and `"status": "not-started"`. Only after that move forward to the next Phase.
- Run **Budget gate** now.

## Phase 3. Testing (Running the loop)

Repeat until `state.json` has `"phase": "report"`  `"status": "not-started"`:

### 3.1. Read the loop state
Read `<engagement_dir>/state.json`. Note `round`, `phase`, `status`. Do not read any other workspace files.

### 3.2. Dispatch based on phase and status (from the `state.json`)

**If phase is `plan` and status is `not-started`:**
- Run the Budget gate now. Do not spawn or resume until it passes.
- First round: spawn the `exploratory-testing:planner` agent and give it the name `planner`.
- Later rounds: resume the existing Planner by sending a message to `planner` instead of spawning a new one. **If resuming fails** (for example, the session was restarted and `planner` is not available), spawn a new `exploratory-testing:planner` as in the first round.
- Run the **write-ahead rule** now.
- Use this delegation prompt, filling in the values:

```
  Workspace: exploratory-testing
  Engagement dir: <engagement_dir>
  Context dir: exploratory-testing/context
  Round: <Round>
  Session file: <engagement_dir>/sessions/TC-<Round>.md.
  Modes: involvement=<involvement>, outcome=<outcome>
  Budget: 500 tool calls
  Read exploratory-testing/WORKSPACE.md first, then follow your instructions to create a new test charter.
```

- As the Planner is started, edit the `state.json` and set `"status": "in-progress"`.

**If phase is `execute` and status is `not-started`:**
- Run the Budget gate now. Do not spawn or resume until it passes.
- Spawn the `exploratory-testing:session-runner` agent and give it the name `session-runner-<Round>` (so each round's Runner has a unique name). Spawn a new Runner for each round.
- Run the **write-ahead rule** now.
- Use this delegation prompt:

```
  Workspace: exploratory-testing
  Engagement dir: <engagement_dir>
  Context dir: exploratory-testing/context
  Round: <Round>
  Session file: <engagement_dir>/sessions/TC-<Round>.md.
  Modes: involvement=<involvement>, outcome=<outcome>
  Budget: 500 tool calls
  Read exploratory-testing/WORKSPACE.md first, then follow your instructions to execute the charter in the Session file.
```

- As the Runner is started, edit the `state.json` and set `"status": "in-progress"`.

### 3.3 Help agents to get answers from the user
When an agent's response contains status `need-decision`:
- Edit the `state.json` and set `"status": "need-decision"`.
- Take the question(s) form the agent's response and ask the user those questions.
- If the user's answers are partial or ambiguous ask for clarifications. If the user's first answer is complete and sufficient, take it as the asnwer for the agent. If you had to ask for clarifications, compile the final version of the answer based on the conversation.
- **IF Planner asked to approve a test charter**: 
    Based on the user's answers update the original version of the charter.
    If the user just approved the Planner's version, use the original version with no update as the user's answer.
- Run the **write-ahead rule** now.
- As you have the answer from the user, resume the same agent that came with the question. Send the agent the following message:

```
User answer: <put the user's answer here>
```

As the current agent is resumed, edit the `state.json` and set `"status": "in-progress"`.

### 3.4. Wait for the agent to finish
Wait for the agent's completion notification before doing anything else.
Do not check workspace files while an agent is still running.

### 3.5. Verify the handoff
After a Planner turn with `status: session-done`:
- change `state.json` and set `"phase": "execute"`, `"status": "not-started";
After a Planner turn with `status: run-done`:
- change `state.json` and set `"phase": "report"`, `"status": "not-started".
After a Runner turn with `status: session-done` or `status: session-out-of-budget`:
- change `state.json` and set `"phase": "plan"`, `"status": "not-started"`, increment `round`.
If a Runner finishes with no STATUS block, treat it as 'session-out-of-budget' with a warning that it was cut off. Don’t wait on it forever. 
Keep your context small. Use only the agents' summaries and the checks above.

Continue the loop.


## Budget gate
Run this before every spawn or resume of any agent.

1. remaining = budget_total - budget_spent (from state.json and engagement.md).
2. Minimum needed: 60 for context-collector, planner or session-runner.
3. If remaining is below the minimum: do NOT spawn or resume. Set state.json phase=report, status=not-started. Tell the user "Budget exhausted: <spent>/<total> tool calls used." Continue with Phase 4 (Report).

## Budget accounting
Run this after each agent finishes a turn with session-done, run-done or session-out-of-budget status.
- add TOOL_CALLS_USED to budget_spent in state.json.
- If the reply has no TOOL_CALLS_USED (the agent was cut off), charge the full Budget you gave it.
- Do this for the context-collector, planner and runner alike.
- Do NOT do this when an agent finishes with the `need-decision` status.


---

## Phase 4: Report
Change `state.json` and set `"phase": "report"`, `"status": "run-done".
.............. TO ADD MORE INSTRUCTIONS LATER ......................

