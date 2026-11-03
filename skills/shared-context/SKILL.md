---
name: shared-context
description: Shared project and domain context for the context-collector, planner and runner agents. Not for direct use.
user-invocable: false
---

## Context

Index of shared context. Read a file only when the task needs it:
- references/oracles.md: **FOR PLANNER**: read before creating test charters.
- references/quality-criteria.md: **FOR PLANNER**: read before prioritizing quality criteria for a test engagement.
- references/modes.md: read to understand what involvement and outcome modes mean.
- references/config-properties.md: **FOR CONTEXT-COLLECTOR, PLANNER AND RUNNER**: read before using `<workspace_dir>/config.yaml`. Explains what the config properties mean (environments, targets, accounts, safety, sources) and what rules to follow based on the config.
