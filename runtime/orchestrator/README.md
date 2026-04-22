# Orchestrator surface

This directory reserves the orchestrator scaffold described in `scaffold-draft.md`.

Current executable mapping:
- Python package: `forgeflow_runtime/orchestrator.py`
- CLI wrapper: `scripts/run_orchestrator.py`

Responsibilities:
- resolve canonical complexity routes
- enforce stage-entry artifact requirements
- persist `run-state` and append-only `decision-log`
- require `spec-review -> quality-review` ordering before finalize
