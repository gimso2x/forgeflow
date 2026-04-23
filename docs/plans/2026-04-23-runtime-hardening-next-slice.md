# Runtime Hardening Next Slice Plan

> **For Hermes:** Use subagent-driven-development only after this plan is accepted. Stay inside runtime robustness and fixture coverage. Do not widen into provider integrations or hosted-runtime cosplay.

**Goal:** Tighten ForgeFlow's runtime truth checks and expand medium/large fixture coverage so the repo stops being merely runnable and becomes harder to fool.

**Architecture:** Keep the existing stage machine and operator surface intact. Strengthen validation at the orchestrator boundary, then prove those checks with additional medium/large positive and negative fixtures. Do not add new stages. Do not redesign the workflow just because more abstraction always sounds sexy at 2 a.m.

**Tech Stack:** Python runtime/orchestrator code, JSON Schema, fixture directories, pytest, adherence eval scripts.

---

## Current state judgment

ForgeFlow is already past the "static design repo" phase:
- `start`, `run`, `resume`, `status`, `advance`, `retry`, `step-back`, `escalate`, and `execute` exist
- `session-state`, `checkpoint`, `plan-ledger`, and review artifacts are already in play
- `make validate` and adherence evals are green on main

What still looks soft:
1. runtime already has meaningful semantic cross-checks, but they are still concentrated in a subset of resume/review paths rather than covering the full medium/large drift surface
2. medium/large fixtures are not yet diverse enough to prove the runtime rejects realistic drift and weak review states
3. the remaining runtime hardening work is now split across focused follow-up slices, but the repo still needs a crisp execution order for them

---

## Workstream A: Orchestrator semantic validation hardening

### Objective
Catch semantic drift inside the runtime itself instead of relying on docs/tests to imply correctness.

### Files
- Modify: `forgeflow_runtime/orchestrator.py`
- Modify: `scripts/run_orchestrator.py` only if CLI error/reporting behavior must change after runtime hardening
- Modify: `tests/test_runtime_orchestrator.py`
- Modify: `tests/test_validate_sample_artifacts.py` only for new artifact-contract coverage tied to runtime semantics
- Modify: `schemas/review-report.schema.json` before runtime checks if the new review semantics need explicit contract support

### Required checks to add
1. **Session-state semantic cross-checks**
   - `session-state.route` must match requested route
   - `session-state.current_stage` must match canonical `run-state.current_stage`
   - `session-state.run_state_ref` must point to `run-state.json`
   - `session-state.plan_ledger_ref` must match route shape: small may point to `run-state.json`; medium/large must point to `plan-ledger.json`
   - `session-state.latest_review_ref` must not point outside task dir and must agree with latest review artifact if present

2. **Review-report semantic cross-checks at runtime**
   - first extend the review-report contract if this slice introduces `safe_for_next_stage`, explicit blocker buckets, or similar fields that do not exist today
   - `review_type=spec` cannot satisfy quality-review gate
   - `review_type=quality` cannot satisfy spec-review gate
   - `verdict=approved` with unresolved blockers should fail runtime validation once blockers are modeled explicitly in the artifact contract
   - `safe_for_next_stage=false` must block finalize/next-stage progress once that field exists in the review-report contract

3. **Plan-ledger consistency checks**
   - completed stages must respect route order
   - completed gates must correspond to completed stages
   - current task status must not be `done` while required review gates are missing
   - evidence refs written by runtime must remain task-local and point to existing artifacts when the file exists on disk

4. **Checkpoint/session-state drift checks during resume/status**
   - resume should reject stale `next_action` pointers that reference missing artifacts
   - status should follow the same strict model as `resume`: reject invalid semantic state explicitly rather than pretending the task is healthy

### Verification
- `pytest -q tests/test_runtime_orchestrator.py`
- add targeted tests that fail before implementation for:
  - approved review with blockers
  - approved review with `safe_for_next_stage=false`
  - medium/large session-state pointing at wrong ledger ref
  - completed gates out of order in medium/large ledger

---

## Workstream B: Medium/large fixture expansion

### Objective
Increase confidence that ForgeFlow rejects realistic medium/large route failures instead of only the current toy cases.

### Files
- Create: `examples/runtime-fixtures/medium-plan-with-weak-verification/`
- Create: `examples/runtime-fixtures/large-approved-but-unsafe/`
- Create: `examples/runtime-fixtures/negative/medium-ledger-gate-drift/`
- Create: `examples/runtime-fixtures/negative/large-spec-quality-mismatch/`
- Create: `examples/runtime-fixtures/negative/large-session-state-stale-review-ref/`
- Modify: `scripts/run_adherence_evals.py`
- Modify: `evals/adherence/README.md`
- Modify: `tests/test_runtime_orchestrator.py`

### Fixture intent
1. **medium-plan-with-weak-verification**
   - richer status/review fixture for a medium route that is structurally valid
   - should pass `status`/`resume`, but still be the kind of task that quality-review must scrutinize before finalize

2. **large-approved-but-unsafe**
   - review verdict may say approved, but the review artifact contract marks it unsafe for the next stage
   - finalize must be blocked

3. **negative/medium-ledger-gate-drift**
   - medium route with completed gate that implies a later stage than the ledger actually reached
   - runtime must reject resume/run/status as drift

4. **negative/large-spec-quality-mismatch**
   - spec-review artifact missing or failed, quality-review artifact approved
   - runtime must reject any attempt to treat quality-review as a substitute

5. **negative/large-session-state-stale-review-ref**
   - session-state points to a missing or stale latest review artifact
   - resume/status must reject it explicitly

### Verification
- unit tests should fail first for the new semantic invariants before runtime logic is changed
- runtime hardening should land before the new negative adherence cases are expected to pass
- `python3 scripts/run_adherence_evals.py`
- `make validate`
- ensure README/adherence docs mention the new negative cases briefly, without turning into a novel

---

## Workstream C: Backlog cleanup and issue slicing

### Objective
Stop leaving the remaining work hidden inside one stale umbrella issue.

### Files
- Modify: issue tracker on GitHub
- Optionally add a short plan index note in `README.md` only if needed

### Required issue split
1. `Harden runtime semantic validation inside the orchestrator`
2. `Add richer medium/large runtime fixtures and adherence eval coverage`

### Decision on issue #1
- keep closed/open history honest
- keep the old orchestrator umbrella issue as historical context only; do not route new implementation work through it again
- note in follow-up issues that provider integrations remain out of scope for this slice

My opinion: **split and close** is cleaner if the umbrella issue already delivered the core orchestrator.

---

## Recommended execution order

### Task 1: Write failing tests for semantic review/runtime drift
- Target: `tests/test_runtime_orchestrator.py`
- Add failing tests for blocker/unsafe approved review and session-state/ledger drift
- Run only the new tests to confirm failure

### Task 2: Harden orchestrator checks
- Target: `forgeflow_runtime/orchestrator.py`
- implement the minimal logic to make those tests pass; if new review semantics require contract fields, update the schema/sample artifacts first in this task
- Re-run targeted tests, then full runtime suite

### Task 3: Add medium/large negative fixtures
- Target: `examples/runtime-fixtures/negative/*`
- Wire them into `scripts/run_adherence_evals.py`
- verify the broader adherence harness is red before the remaining runtime logic for those new cases, then green after the implementation is complete

### Task 4: Add medium/large richer positive-ish fixtures
- Target: `examples/runtime-fixtures/*`
- Use them for status/resume/finalize edge checks instead of only happy-path demos

### Task 5: Update issue tracker
- Create the two follow-up issues
- decompose remaining work cleanly
- stop pretending the old umbrella issue is still the right unit of execution

---

## What not to do next
- do not start provider-specific integrations because the repo finally feels alive
- do not add new adapter targets to feel productive
- do not invent another command surface before tightening semantic checks on the current one
- do not turn every validation nuance into schema if a runtime cross-check is the right layer

---

## Final recommendation

**The right next slice is not "more features." It is runtime honesty.**

ForgeFlow is already usable.
Now it needs to become harder to bullshit:
1. tighten orchestrator semantic validation
2. prove it with harsher medium/large fixtures
3. clean up the backlog so the next implementation step is obvious
