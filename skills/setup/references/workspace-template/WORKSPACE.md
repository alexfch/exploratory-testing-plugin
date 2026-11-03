# WORKSPACE.md

## Layout
- config.yaml: the project configuration (product, environments, targets, accounts, safety, sources). Written only by the Setup skill. Everyone else reads it and never edits it.
- rules-of-engagement.md: the project's default rules for each kind of environment. Owned by the user; agents never edit it. Only the Orchestrator reads it, and copies the rules that apply into each run's engagement.md.
- context/: only the Context-collector writes and edits it. Others may read if an instruction requires.
- execution/test-run-<timestamp>/: one folder per engagement. Name contains the date and time of the engagement start.
- execution/test-run-<timestamp>/state.json: loop state. Only the Orchestrator writes it.
- execution/test-run-<timestamp>/sessions/TC-<Round>.md: one file per test charter. Created by the Planner, updated by the Planner (test charter) and Runner (test notes and bugs).
- execution/test-run-<timestamp>/engagement.md: Orchestrator and Planner can read/write, except the "Rules of engagement" field: only the Orchestrator writes it, everyone else only reads it.

## Rules
- Never delete files. Never write outside your listed files.
- Never open, read, print or search the secrets file (`~/exploratory-testing/secrets.env`). Never ask the user for a secret value in chat.
