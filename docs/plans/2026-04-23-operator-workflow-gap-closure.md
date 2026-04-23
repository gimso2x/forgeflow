# Operator Workflow Gap Closure Plan

> **For Hermes:** Use subagent-driven-development only after this plan is accepted. Keep the external shape aligned with `engineering-discipline`; do not widen scope into provider integrations or prompt-zoo nonsense.

**Goal:** Close the gap between ForgeFlow's strong internal artifact/runtime foundation and the still-weak operator-facing workflow, so a user can start, resume, inspect, and review real work without manually stitching artifacts together.

**Architecture:** Keep `engineering-discipline` as the visible operator UX, but make the runtime truth explicit through task bootstrap, session-state pointers, and calibrated review artifacts. Do not add new stages. Do not rename the workflow just because another repo had shinier nouns.

**Tech Stack:** Markdown docs, JSON Schema, YAML policy, Python runtime/orchestrator scripts, example fixtures, pytest.

---

## One-line judgment

ForgeFlow already has the right kernel.
What it lacks is the **entry flow and operator ergonomics** that make the kernel usable without repo archaeology.

---

## Evidence-backed current state

### Already strong
- workflow shape is stable and readable
  - `README.md`
  - `docs/workflow.md`
  - `policy/canonical/workflow.yaml`
- artifact-first contracts already exist
  - `schemas/plan-ledger.schema.json`
  - `schemas/checkpoint.schema.json`
  - `schemas/run-state.schema.json`
  - `schemas/review-report.schema.json`
- generated adapter pipeline already exists
  - `adapters/targets/*/manifest.yaml`
  - `adapters/generated/*`
- minimal runtime orchestration exists
  - `scripts/run_orchestrator.py`
  - `forgeflow_runtime/orchestrator.py`
  - `tests/test_runtime_orchestrator.py`

### Still weak
- no first-class **task bootstrap** flow
  - current CLI assumes an existing `--task-dir`
- no explicit **session-state pointer artifact** for resume/handoff
- review schema/rubric is still too thin for calibrated operator review
- memory/eval substrate is mostly scaffold, not a practical operator-facing system

### Design constraint
Do **not** solve this by adding more stages, more personas, or another branding religion.
The fix is to expose the existing semantics through better operator surfaces.

---

## Target operator workflow

### Small task
`start -> clarify -> execute -> quality-review -> finalize`

### Medium task
`start -> clarify -> plan -> execute -> quality-review -> finalize`

### Large/high-risk task
`start -> clarify -> plan -> execute -> spec-review -> quality-review -> finalize -> long-run`

### Operator-visible commands we actually need
1. `start` — initialize task directory and base artifacts
2. `status` — show current route, stage, blockers, next action, evidence summary
3. `advance` — move one stage forward when gates pass
4. `retry` — bounded retry within policy
5. `step-back` — rewind one stage with explicit reason
6. `resume` — reload from session-state + checkpoint refs, not transcript vibes
7. `review-summary` — show latest verdict, evidence refs, residual risks

**Decision:** `run` alone is not enough. Users need a visible lifecycle, not a hidden state machine cosplay.

---

## Scope of this gap-closure plan

### In scope
- task bootstrap surface
- session-state artifact + resume flow
- status/review-summary operator surfaces
- stronger review schema/rubric calibration
- examples and tests that prove the operator workflow

### Out of scope
- provider-specific integrations
- hosted runtime
- plugin ecosystem
- magical hidden memory
- renaming the ForgeFlow stages
- mandatory heavy contracts for tiny tasks

---

## Workstream 1: Task bootstrap

### Objective
Create a first-class entrypoint so a new task can be started without hand-crafting artifact directories.

### Files
- Modify: `scripts/run_orchestrator.py`
- Modify: `forgeflow_runtime/orchestrator.py`
- Create: `examples/runtime-fixtures/bootstrapped-small-task/`
- Create: `examples/runtime-fixtures/bootstrapped-medium-task/`
- Create: `examples/runtime-fixtures/bootstrapped-large-task/`
- Modify: `README.md`

### Required behavior
`start` should:
- create task directory if missing
- write initial `run-state.json`
- write initial `session-state.json`
- write route-appropriate starter artifacts:
  - `brief.md` or `brief.json`
  - `plan.md` for medium/large templates
  - `plan-ledger.json` for medium/large
  - optional `contracts/` directory only when required later
- return machine-readable output:
  - `task_dir`
  - `route`
  - `current_stage`
  - `created_artifacts[]`
  - `next_action`

### Verification
- `python3 scripts/run_orchestrator.py start --task-dir <tmp> --route small`
- `python3 scripts/run_orchestrator.py start --task-dir <tmp> --route medium`
- `python3 scripts/run_orchestrator.py start --task-dir <tmp> --route large_high_risk`
- `pytest tests/test_runtime_orchestrator.py -q`

### Why this matters
This is the missing front door.
Without it, ForgeFlow keeps asking the operator to already know too much.

---

## Workstream 2: Session-state pointer artifact

### Objective
Make resume and handoff artifact-based for real, not just philosophically.

### Files
- Create: `schemas/session-state.schema.json`
- Create: `examples/artifacts/session-state.sample.json`
- Create: `examples/artifacts/invalid/session-state-missing-ref.sample.json`
- Modify: `scripts/validate_sample_artifacts.py`
- Modify: `docs/recovery-policy.md`
- Modify: `docs/checkpoint-model.md`
- Modify: `forgeflow_runtime/orchestrator.py`
- Modify: `tests/test_validate_sample_artifacts.py`
- Modify: `tests/test_runtime_orchestrator.py`

### Required fields
- `schema_version`
- `task_id`
- `route`
- `current_stage`
- `current_task_id`
- `plan_ref`
- `plan_ledger_ref`
- `run_state_ref`
- `latest_checkpoint_ref`
- `latest_review_ref`
- `next_action`
- `updated_at`

### Required behavior
- `start` writes initial `session-state.json`
- `advance`, `retry`, `step-back`, `escalate` update `session-state.json`
- `resume` reads `session-state.json`, reloads referenced artifacts, and returns current truth
- runtime rejects broken refs or route/stage drift

### Verification
- `python3 scripts/validate_sample_artifacts.py`
- `python3 scripts/run_orchestrator.py resume --task-dir <fixture>`
- negative fixture rejects missing refs and stale pointers
- `pytest tests/test_runtime_orchestrator.py -q`

### Why this matters
If resume still depends on transcript summaries, then the whole artifact-first sermon is bullshit.
This closes that loophole.

---

## Workstream 3: Status and review-summary surfaces

### Objective
Expose state and review outcomes in operator language instead of forcing users to inspect raw artifact files.

### Files
- Modify: `scripts/run_orchestrator.py`
- Modify: `forgeflow_runtime/orchestrator.py`
- Modify: `README.md`
- Create: `docs/operator-workflow.md`
- Modify: `tests/test_runtime_orchestrator.py`

### Required commands
#### `status`
Returns:
- `task_id`
- `route`
- `current_stage`
- `current_task_id`
- `open_blockers[]`
- `required_gates[]`
- `latest_review_verdict`
- `next_action`

#### `review-summary`
Returns:
- `review_type`
- `verdict`
- `blockers[]`
- `important_follow_ups[]`
- `advisories[]`
- `missing_evidence[]`
- `residual_risks[]`
- `evidence_refs[]`
- `next_action`

### Verification
- run `status` against small/medium/large fixtures
- run `review-summary` against approved and changes-requested fixtures
- ensure outputs are compact, machine-readable, and human-usable

### Why this matters
Users should not have to open four JSON files to answer “where am I?” or “why did review fail?”
That’s not discipline. That’s punishment.

---

## Workstream 4: Calibrated review schema and policy

### Objective
Upgrade review from thin pass/fail reporting into calibrated, evidence-backed judgment.

### Files
- Modify: `schemas/review-report.schema.json`
- Modify: `policy/canonical/review-rubrics.yaml`
- Modify: `docs/workflow.md`
- Create: `examples/artifacts/review-report-approved.sample.json`
- Create: `examples/artifacts/review-report-blocked.sample.json`
- Create: `examples/artifacts/invalid/review-report-invalid-severity.sample.json`
- Modify: `scripts/validate_sample_artifacts.py`
- Modify: `tests/test_validate_sample_artifacts.py`

### Required schema additions
- `blockers[]`
- `important_follow_ups[]`
- `advisories[]`
- `residual_risks[]`
- `approval_basis[]`
- `reviewed_by`
- `safe_for_next_stage` (boolean)

### Required policy additions
Spec review must distinguish:
- scope miss
- acceptance miss
- evidence miss
- drift

Quality review must distinguish:
- avoidable complexity
- weak verification
- maintainability risk
- documented but acceptable residual risk

### Verification
- `python3 scripts/validate_sample_artifacts.py`
- negative samples fail for malformed severity structure
- runtime/finalize treats `safe_for_next_stage` as a generic approved-review progression guard, not a quality-only flag

### Why this matters
Superpowers got one thing very right: review should be skeptical.
But if it can’t distinguish blocker vs follow-up vs nit, it turns into theater.
We are not building theater.

---

## Workstream 5: Operator examples and methodology evals

### Objective
Prove the workflow through examples and process checks, not README vibes.

### Files
- Create: `docs/operator-workflow.md`
- Modify: `evals/adherence/README.md`
- Create: `examples/operator-flows/small-task.md`
- Create: `examples/operator-flows/medium-task.md`
- Create: `examples/operator-flows/large-task.md`
- Modify: `tests/test_runtime_orchestrator.py`
- Create/modify process-adherence tests under `tests/`

### Required eval coverage
- `start` creates correct route-specific artifacts
- `resume` refuses broken refs and stale state
- `status` reflects actual runtime state
- `review-summary` matches the latest review artifact
- `quality-review` cannot substitute for failed `spec-review`
- `finalize` refuses unresolved blockers

### Verification
- `make validate`
- `python3 scripts/run_adherence_evals.py`
- tests assert process adherence, not just file existence

### Why this matters
The harness has to prove it behaves correctly.
Otherwise it’s just another repo with strong opinions and weak receipts.

---

## Recommended execution order

### Task 1: Add session-state contract first
**Objective:** make resume and status semantics explicit before widening CLI surface.

**Files:**
- Create: `schemas/session-state.schema.json`
- Create: `examples/artifacts/session-state.sample.json`
- Modify: `scripts/validate_sample_artifacts.py`
- Modify: `docs/recovery-policy.md`

**Verification:**
- `python3 scripts/validate_sample_artifacts.py`

### Task 2: Add `start` and `resume`
**Objective:** create a real operator entry and reload path.

**Files:**
- Modify: `scripts/run_orchestrator.py`
- Modify: `forgeflow_runtime/orchestrator.py`
- Modify: `tests/test_runtime_orchestrator.py`

**Verification:**
- `pytest tests/test_runtime_orchestrator.py -q`

### Task 3: Add `status` and `review-summary`
**Objective:** expose workflow state without file spelunking.

**Files:**
- Modify: `scripts/run_orchestrator.py`
- Modify: `forgeflow_runtime/orchestrator.py`
- Create: `docs/operator-workflow.md`

**Verification:**
- fixture-based status/review-summary checks

### Task 4: Strengthen review schema/policy
**Objective:** make review output operationally useful.

**Files:**
- Modify: `schemas/review-report.schema.json`
- Modify: `policy/canonical/review-rubrics.yaml`
- Modify: sample artifacts/tests

**Verification:**
- schema + negative fixture validation

### Task 5: Update README and examples
**Objective:** make the operator workflow obvious in the repo surface.

**Files:**
- Modify: `README.md`
- Create: `examples/operator-flows/*`

**Verification:**
- a new user can identify start/resume/status/review flow from docs alone

---

## What not to do
- do not introduce new stage names
- do not add personas or slash-command spam
- do not make memory a magical black box
- do not bury review semantics in prompt prose only
- do not require contracts for every tiny task
- do not keep polishing the kernel while the front door is still missing

---

## Final recommendation

**Build the missing operator shell around the kernel that already exists.**

The right move now is:
1. add `session-state`
2. add `start/resume/status/review-summary`
3. calibrate review artifacts
4. prove the flow with examples and adherence tests

If we do that, ForgeFlow stops being “interesting internal architecture” and starts becoming a harness people can actually drive.
If we don’t, it stays one more smart repo that makes users read too much before doing anything.
