## Modes

### Involvement mode during execution

**`human-in-the-loop` (default):** pause and ask the user for missing context or an explicit decision whenever: scope is ambiguous, a finding's severity is genuinely unclear, or the next charter could go in materially different directions. Convey subagents’ questions to the user and send the answers back to the subagents.
**`agent-only`:** make the most reasonable call yourself and continue without pausing; flag each such decision with the [ASSUMED] tag, in the context document, `engagement.md` or the test notes, wherever you document it.

### Outcome mode during execution

**`test-only` (default):** do not invoke any skill or tool to fix a bug — log it to the report only.
