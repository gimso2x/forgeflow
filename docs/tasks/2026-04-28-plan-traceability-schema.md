# Plan Traceability Schema Hardening

- Date: 2026-04-28
- Owner: ForgeFlow
- Status: completed

## Goal
Lock the plan-stage requirement traceability contract into machine-validated artifacts, not only prose.

## Scope
- Require implementation steps in `plan.schema.json` to declare the requirement or verification target they fulfill.
- Keep `examples/artifacts/plan.sample.json` valid under the stricter contract.
- Add a negative sample proving orphan work without `fulfills` is rejected.
- Run targeted sample validation and full repository validation.

## Non-goals
- Import the so2x schema wholesale.
- Redesign runtime routing or plan-ledger semantics.
- Add shell hooks.

## Acceptance Criteria
- `scripts/validate_sample_artifacts.py` rejects a plan step missing `fulfills`.
- Positive plan samples remain valid.
- `make validate` passes.
- Changes are committed and pushed to `origin/main`.

## Plan
1. Add TDD coverage for missing `fulfills`.
2. Tighten `schemas/plan.schema.json` minimally.
3. Update fixtures if stricter validation exposes stale examples.
4. Validate, review diff for secrets/scope drift, commit, push.
