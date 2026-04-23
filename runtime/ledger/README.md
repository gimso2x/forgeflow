# Ledger surface

ForgeFlow keeps execution state in inspectable local artifacts, not hidden chat state.

This scaffold directory names the runtime ledger responsibilities:
- `run-state` for current stage, status, gates, retries, approvals
- `decision-log` for append-only transition and recovery history
- future checkpoint material for resumable long-running work

Today those artifacts are written directly into task directories by `forgeflow_runtime/orchestrator.py`.
