# Runtime scaffold

This tree is the repository-facing runtime scaffold promised by the design docs.

It documents the control surfaces that a practical ForgeFlow runtime must expose:
- `orchestrator/` — stage-machine entrypoints and execution coordination
- `ledger/` — append-only run history and checkpoint surfaces
- `gates/` — stage transition and review-order enforcement
- `recovery/` — bounded retry, step-back, and escalation rules

The executable Python implementation currently lives in `forgeflow_runtime/` and is invoked by `scripts/run_orchestrator.py`.
This `runtime/` tree is the stable scaffold/documentation surface, not a duplicated code path.
