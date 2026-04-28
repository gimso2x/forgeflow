# Issue #57 Artifact-First Hardening

- Date: 2026-04-28
- Owner: ForgeFlow
- Status: completed
- Issue: `#57`
- Commit: `5082cfe`

## Goal
Close the gap where ForgeFlow runtime already had task-dir concepts, but the plugin skill contract still defaulted to response-only behavior and silently broke the artifact-first workflow.

## Problem Statement
The bug was not just "`.forgeflow/tasks/` is missing." The worse problem was contract drift:

- runtime entry points already supported task directories and `init`
- plugin skills still told the agent to prefer chat-only output unless a writable directory was explicitly handed in
- that made `brief.json`, `plan.json`, and `run-state.json` optional in practice, which gutted the workflow

In short: the runtime was trying to be artifact-first while the plugin contract was still chat-first.

## Scope
- Flip canonical ForgeFlow skills from response-only default to artifact-first default.
- Make `.forgeflow/tasks/<task-id>/` the canonical writable path.
- Keep dry-run as the only intentional response-only exception.
- Harden `scripts/run_orchestrator.py` so plugin installation / marketplace cache paths reject mutating commands.
- Preserve `status` as a read-only inspection path.
- Lock the behavior with contract and runtime tests.

## Non-goals
- No full workflow redesign.
- No adapter expansion unrelated to issue #57.
- No mass cleanup of unrelated dirty files already present in the repo.

## Acceptance Criteria
- `clarify`, `plan`, `run`, `review`, `ship`, and top-level `forgeflow` docs all describe artifact-first behavior.
- Plugin / marketplace cache paths reject mutating commands:
  - `start`
  - `init`
  - `run`
  - `resume`
  - `advance`
  - `retry`
  - `step-back`
  - `escalate`
  - `execute`
- `status` remains allowed for read-only inspection.
- Contract tests and targeted runtime tests pass.
- Fix is committed, pushed to `main`, and issue #57 is closed.

## Implementation Summary
1. Rewrote canonical skill contracts so the default path is artifact creation, not chat fallback.
2. Standardized `.forgeflow/tasks/<task-id>/` as the only safe canonical writable path.
3. Explicitly banned writes inside plugin installation directories and marketplace cache paths.
4. Hardened CLI/runtime entry checks so mutating commands fail fast when pointed at those locations.
5. Added and updated tests to freeze the contract.
6. Pushed the fix and closed the issue.

## Verification
- `pytest -q tests/runtime/test_orchestrator_cli.py tests/test_plugin_skill_contracts.py tests/test_forgeflow_ux_contract.py tests/test_finish_skill_contract.py tests/runtime/test_checkpoint_resume.py`
  - `52 passed`
- `python3 scripts/validate_skill_contracts.py`
  - `SKILL CONTRACT VALIDATION: PASS`

## Files Touched in the Fix
- `skills/clarify/SKILL.md`
- `skills/plan/SKILL.md`
- `skills/run/SKILL.md`
- `skills/review/SKILL.md`
- `skills/ship/SKILL.md`
- `skills/forgeflow/SKILL.md`
- `scripts/run_orchestrator.py`
- `tests/runtime/test_orchestrator_cli.py`
- `tests/test_plugin_skill_contracts.py`
- `tests/test_forgeflow_ux_contract.py`

## Outcome
Issue #57 is not just "discussed" or "documented." It is fixed in code, pinned in tests, pushed to `main`, and closed.