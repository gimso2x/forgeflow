# FF-MAINT-002: Extract Route Execution Seam

Priority: P0
Status: Landed in local review stack
Type: behavior-preserving refactor
Primary file: `forgeflow_runtime/orchestrator.py`
Candidate new file: `forgeflow_runtime/route_execution.py`

## Problem

`run_route()` remains one of the highest-risk orchestration hotspots. It coordinates route loop progression, stage execution, artifact validation, checkpoint/session synchronization, and finalization behavior.

The function currently works, but it is too central. Future route behavior changes should not require editing a 100+ line orchestration function with many side effects.

## Goal

Extract one cohesive route-execution responsibility from `run_route()` into a named runtime seam, without changing public behavior.

## Non-goals

- Do not rewrite all route execution at once.
- Do not introduce a framework/state-machine dependency.
- Do not change route names, policy files, or artifact schema.
- Do not change checkpoint semantics.
- Do not combine with stage-transition extraction unless FF-MAINT-001 has already landed.

## Proposed seam

Create a module such as:

```text
forgeflow_runtime/route_execution.py
```

Candidate responsibilities:

- Calculate the next executable stage sequence for a route.
- Isolate route-loop stop/finalize conditions.
- Keep file writes and runtime artifact mutation in `orchestrator.py` initially.
- Use injected callbacks/factories for stable exception and execution behavior where necessary.

## Suggested implementation steps

1. Start only after FF-MAINT-001 is complete or explicitly skipped.
2. Identify a pure route-loop decision block inside `run_route()`.
3. Add focused unit tests for that route decision behavior.
4. Extract the block into `route_execution.py`.
5. Keep the orchestrator as the side-effect coordinator.
6. Run route, checkpoint, and review-gate tests.

## Acceptance criteria

- `run_route()` is shorter and delegates one named route-execution responsibility.
- Existing route behavior remains unchanged.
- Checkpoint/resume tests still pass.
- Review-gate and finalization behavior still pass.
- No broad rewrite or framework appears in the diff.

## Suggested narrow validation

```bash
python -m pytest tests/runtime/test_checkpoint_resume.py tests/runtime/test_status_resume.py -q
python -m pytest tests/runtime/test_review_gates.py tests/runtime/test_stage_transitions.py -q
make validate
python -m pytest -q
git diff --check
git status --short
```

## Commit message

```text
refactor: extract route execution seam
```
