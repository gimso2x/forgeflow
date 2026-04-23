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
1. runtime validation still leans heavily on per-artifact schema checks and a subset of semantic cross-checks
2. medium/large fixtures are not yet diverse enough to prove the runtime rejects realistic drift and weak review states
3. issue #1 is still open because the remaining checklist items were never split into focused follow-up slices

---

## Workstream A: Orchestrator semantic validation hardening

### Objective
Catch semantic drift inside the runtime itself instead of relying on docs/tests to imply correctness.

### Files
- Modify: `forgeflow_runtime/orchestrator.py`
- Modify: `scripts/run_orchestrator.py`
- Modify: `tests/test_runtime_orchestrator.py`
- Modify: `tests/test_validate_sample_artifacts.py`
- Optionally modify: `schemas/review-report.schema.json` only if a real runtime invariant cannot be expressed without schema support

### Required checks to add
1. **Session-state semantic cross-checks**
   - `session-state.route` must match requested route
   - `session-state.current_stage` must match canonical `run-state.current_stage`
   - `session-state.run_state_ref` must point to `run-state.json`
   - `session-state.plan_ledger_ref` must match route shape: small may point to `run-state.json`; medium/large must point to `plan-ledger.json`
   - `session-state.latest_review_ref` must not point outside task dir and must agree with latest review artifact if present

2. **Review-report semantic cross-checks at runtime**
   - `review_type=spec` cannot satisfy quality-review gate
   - `review_type=quality` cannot satisfy spec-review gate
   - `verdict=approved` with unresolved blockers should fail runtime validation
   - `safe_for_next_stage=false` must block finalize/next-stage progress even if `verdict=approved`

3. **Plan-ledger consistency checks**
   - completed stages must respect route order
   - completed gates must correspond to completed stages
   - current task status must not be `done` while required review gates are missing
   - evidence refs written by runtime must remain task-local and point to existing artifacts when the file exists on disk

4. **Checkpoint/session-state drift checks during resume/status**
   - resume should reject stale `next_action` pointers that reference missing artifacts
   - status should surface open blockers when semantic invariants fail instead of pretending the task is healthy

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
   - positive-ish fixture for status/review visibility
   - should expose that plan exists but verification is still weak enough to require quality-review scrutiny

2. **large-approved-but-unsafe**
   - review verdict may say approved, but `safe_for_next_stage=false`
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
- either close it after the follow-up issues are created and note that provider integrations remain out of scope
- or edit/comment that the remaining checklist items have been split into dedicated issues

My opinion: **split and close** is cleaner if the umbrella issue already delivered the core orchestrator.

---

## Recommended execution order

### Task 1: Write failing tests for semantic review/runtime drift
- Target: `tests/test_runtime_orchestrator.py`
- Add failing tests for blocker/unsafe approved review and session-state/ledger drift
- Run only the new tests to confirm failure

### Task 2: Harden orchestrator checks
- Target: `forgeflow_runtime/orchestrator.py`
- Implement the minimal logic to make those tests pass
- Re-run targeted tests, then full runtime suite

### Task 3: Add medium/large negative fixtures
- Target: `examples/runtime-fixtures/negative/*`
- Wire them into `scripts/run_adherence_evals.py`
- Verify the eval harness fails before the implementation and passes after

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
