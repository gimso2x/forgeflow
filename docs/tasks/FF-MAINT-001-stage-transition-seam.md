# FF-MAINT-001: Extract Stage Transition Seam

Priority: P0
Status: Landed in local review stack
Type: behavior-preserving refactor
Primary file: `forgeflow_runtime/orchestrator.py`
Candidate new file: `forgeflow_runtime/stage_transition.py`

## Problem

`advance_to_next_stage()` is still doing too much inside `orchestrator.py`. It mixes stage movement, gate expectations, artifact checks, execution decisions, review flags, checkpoint/session updates, and transition payload construction.

The current behavior is passing tests, so this is not a bug fix. The risk is future change amplification: a small stage-policy change can accidentally disturb checkpoint, review, or gate behavior.

## Goal

Extract the pure stage-transition decision logic into a focused runtime seam while preserving public behavior and existing CLI/runtime contracts.

## Non-goals

- Do not rewrite the orchestrator.
- Do not introduce a state-machine framework.
- Do not change route policy.
- Do not rename artifacts.
- Do not modify unrelated evolution code.
- Do not combine this with fixture cleanup.

## Proposed seam

Create a focused module such as:

```text
forgeflow_runtime/stage_transition.py
```

Candidate responsibilities:

- Determine the next stage from current route and current stage.
- Represent transition decisions in a pure result object if useful.
- Keep side-effectful writes in `orchestrator.py` until the seam is proven.
- Preserve stable exception behavior by injecting `violation_factory=RuntimeViolation` if needed, rather than importing `orchestrator.py` from the seam.

## Suggested implementation steps

1. Inspect `advance_to_next_stage()` and mark pure decision sub-blocks only.
2. Add focused tests for the pure transition seam first.
3. Move one coherent decision block into `stage_transition.py`.
4. Keep a thin private wrapper in `orchestrator.py` if that reduces churn.
5. Run narrow runtime tests.
6. Run full validation.

## Acceptance criteria

- `advance_to_next_stage()` is shorter and delegates one named responsibility to `stage_transition.py`.
- Existing runtime behavior is unchanged.
- New tests cover the extracted pure seam.
- No generic helper module is introduced.
- No scenario test coverage is deleted or weakened.

## Suggested narrow validation

```bash
python -m pytest tests/runtime/test_stage_transitions.py -q
python -m pytest tests/runtime/test_gate_evaluation.py tests/runtime/test_plan_ledger.py -q
make validate
python -m pytest -q
git diff --check
git status --short
```

## Commit message

```text
refactor: extract stage transition seam
```
