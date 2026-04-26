# ForgeFlow Maintainability Task Backlog

Date: 2026-04-26
Status: Proposed
Scope: behavior-preserving maintainability hardening after runtime/evolution decomposition

## Verdict

ForgeFlow is operationally healthy: validation and tests pass, recent decomposition improved the architecture, and `docs/contract-map.md` now records major contract surfaces. The remaining risk is change amplification around the runtime orchestration core, especially `forgeflow_runtime/orchestrator.py`.

This backlog intentionally avoids feature expansion. Each task should be a small, reviewable slice with narrow tests first, then `make validate`, full pytest, `git diff --check`, and `git status --short`.

## Current evidence

- `make validate`: passing at review time.
- `python -m pytest -q`: `382 passed` at review time.
- Main hotspot: `forgeflow_runtime/orchestrator.py` at roughly 1243 lines.
- Largest runtime orchestration functions:
  - `run_route()` around 143 lines.
  - `advance_to_next_stage()` around 131 lines.
  - `start_task()` around 82 lines.
- Existing useful seams:
  - `forgeflow_runtime/artifact_validation.py`
  - `forgeflow_runtime/gate_evaluation.py`
  - `forgeflow_runtime/resume_validation.py`
  - `forgeflow_runtime/plan_ledger.py`
  - `forgeflow_runtime/task_identity.py`
- Existing contract index: `docs/contract-map.md`.

## Task list

| ID | Priority | Task | Primary risk reduced |
| --- | --- | --- | --- |
| FF-MAINT-001 | P0 | Extract stage transition seam | `advance_to_next_stage()` change amplification |
| FF-MAINT-002 | P0 | Extract route execution seam | `run_route()` change amplification |
| FF-MAINT-003 | P1 | Consolidate runtime test fixtures carefully | Large test setup duplication |
| FF-MAINT-004 | P1 | Add script-thinness guard | CLI scripts accumulating policy logic |
| FF-MAINT-005 | P1 | Harden contract-map validation | Docs/source-of-truth drift |

## Non-goals

- No broad rewrite of `orchestrator.py`.
- No state-machine framework.
- No new adapter or workflow feature.
- No vague `utils.py` extraction.
- No deletion of large scenario tests just because they are large.
- No runtime refactor and large test refactor in the same commit.

## Validation baseline for every task

Run at least:

```bash
make validate
python -m pytest -q
git diff --check
git status --short
```

Add narrower pytest targets per task before the full suite.

## Review rule

A task is done only when:

1. Behavior is preserved.
2. The touched responsibility has a clearer named seam or tighter guard.
3. Narrow tests pass.
4. Full validation passes.
5. The diff is small enough to review without archaeology.
