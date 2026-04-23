# Recovery surface

ForgeFlow recovery is intentionally bounded.

This scaffold directory marks the runtime recovery responsibilities:
- retry within explicit budgets only
- step back to the previous safe stage when necessary
- escalate route complexity instead of pretending risk stayed low

Current executable mapping lives in `forgeflow_runtime/orchestrator.py` via `retry_stage`, `step_back`, and `escalate_route`.
