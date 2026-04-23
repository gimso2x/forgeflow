# Runtime Orchestrator CLI Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a minimal local runtime/orchestrator CLI that executes ForgeFlow’s canonical stage machine against an artifact directory.

**Architecture:** Add a small Python runtime package that loads canonical policy files, resolves a route, validates stage entry/exit from artifact presence plus run-state flags, and records deterministic transitions in `run-state` and `decision-log`. Expose that package through a thin CLI script so v1 stays local, inspectable, and provider-agnostic.

**Tech Stack:** Python 3 stdlib, pytest, JSON artifact files, existing canonical YAML/JSON files.

---

### Task 1: Add failing tests for policy loading and route resolution

**Objective:** Prove the runtime can load canonical policy and select the requested route before any implementation exists.

**Files:**
- Create: `tests/test_runtime_orchestrator.py`
- Create: `forgeflow_runtime/__init__.py`
- Create: `forgeflow_runtime/orchestrator.py`

**Step 1: Write failing test**
- Add tests for `load_runtime_policy()` and `resolve_route("small")`.
- Assert the resolved route stages equal `clarify -> execute -> quality-review -> finalize`.

**Step 2: Run test to verify failure**
- Run: `pytest tests/test_runtime_orchestrator.py::test_load_runtime_policy_and_resolve_small_route -v`
- Expected: FAIL because runtime module/functions do not exist yet.

**Step 3: Write minimal implementation**
- Add lightweight YAML-line parsers that read `policy/canonical/workflow.yaml`, `stages.yaml`, `gates.yaml`, and `complexity-routing.yaml`.
- Return a `RuntimePolicy` object with `workflow_stages`, `stage_requirements`, `gate_requirements`, and `routes`.

**Step 4: Run test to verify pass**
- Run: `pytest tests/test_runtime_orchestrator.py::test_load_runtime_policy_and_resolve_small_route -v`
- Expected: PASS.

---

### Task 2: Add failing tests for legal transition checks

**Objective:** Prove the orchestrator refuses illegal stage transitions and enforces artifact prerequisites.

**Files:**
- Modify: `tests/test_runtime_orchestrator.py`
- Modify: `forgeflow_runtime/orchestrator.py`

**Step 1: Write failing test**
- Add a test that tries to enter `quality-review` before `run-state.json` exists.
- Add a test that tries to enter `finalize` without the required approval flags.

**Step 2: Run test to verify failure**
- Run: `pytest tests/test_runtime_orchestrator.py::test_advance_blocks_missing_entry_artifacts tests/test_runtime_orchestrator.py::test_finalize_blocks_missing_review_flags -v`
- Expected: FAIL because transition validation is not implemented yet.

**Step 3: Write minimal implementation**
- Implement `advance_to_next_stage()` with route-order checks.
- Validate `required_for_entry` artifacts from `stages.yaml`.
- Validate finalize gate flags from `gates.yaml` + `run-state`.
- Raise explicit `RuntimeViolation` messages for illegal transitions.

**Step 4: Run test to verify pass**
- Run the two tests above.
- Expected: PASS.

---

### Task 3: Add failing tests for deterministic state and decision-log updates

**Objective:** Prove each successful transition updates `run-state` and `decision-log` predictably.

**Files:**
- Modify: `tests/test_runtime_orchestrator.py`
- Modify: `forgeflow_runtime/orchestrator.py`

**Step 1: Write failing test**
- Add a test that runs a small route fixture end-to-end.
- Assert:
  - `run-state.current_stage == "finalize"`
  - `run-state.status == "completed"`
  - completed gates include `clarification_complete`, `execution_evidenced`, `quality_review_passed`
  - `decision-log.entries` records route start and each stage transition in order.

**Step 2: Run test to verify failure**
- Run: `pytest tests/test_runtime_orchestrator.py::test_small_route_runs_end_to_end_and_updates_state -v`
- Expected: FAIL because success-path persistence does not exist yet.

**Step 3: Write minimal implementation**
- Implement artifact-directory loading/saving helpers.
- Implement `run_route()` to iterate through the selected route, update gates, flip approval flags from review artifacts, and persist deterministic JSON.

**Step 4: Run test to verify pass**
- Run the single end-to-end test.
- Expected: PASS.

---

### Task 4: Add failing tests for retry / step-back / escalate mechanics

**Objective:** Cover the required local recovery mechanics without adding provider integrations.

**Files:**
- Modify: `tests/test_runtime_orchestrator.py`
- Modify: `forgeflow_runtime/orchestrator.py`

**Step 1: Write failing test**
- Add tests for:
  - `retry_stage()` increments bounded retry counters and blocks when over budget.
  - `step_back()` rewinds to the previous route stage.
  - `escalate_route()` upgrades `small` or `medium` tasks to `large_high_risk`.

**Step 2: Run test to verify failure**
- Run: `pytest tests/test_runtime_orchestrator.py::test_retry_is_bounded tests/test_runtime_orchestrator.py::test_step_back_rewinds_to_previous_stage tests/test_runtime_orchestrator.py::test_escalate_route_switches_to_large_high_risk -v`
- Expected: FAIL because recovery helpers do not exist yet.

**Step 3: Write minimal implementation**
- Add recovery helpers that mutate `run-state` + `decision-log` only.
- Keep budgets simple and explicit: default max 2 retries per stage.

**Step 4: Run test to verify pass**
- Run the three tests above.
- Expected: PASS.

---

### Task 5: Add CLI coverage and fixture docs

**Objective:** Ship a usable CLI entrypoint and one fixture-driven example that proves the route can be exercised locally.

**Files:**
- Create: `scripts/run_orchestrator.py`
- Create: `examples/runtime-fixtures/small-doc-task/brief.json`
- Create: `examples/runtime-fixtures/small-doc-task/review-report.json`
- Create: `examples/runtime-fixtures/small-doc-task/README.md`
- Modify: `README.md`
- Modify: `Makefile`

**Step 1: Write failing test**
- Add a CLI test that shells out to `python3 scripts/run_orchestrator.py run --task-dir ... --route small`.
- Assert exit code 0 and that the task dir now contains updated `run-state.json` and `decision-log.json`.

**Step 2: Run test to verify failure**
- Run: `pytest tests/test_runtime_orchestrator.py::test_cli_run_executes_sample_fixture -v`
- Expected: FAIL because CLI script/fixture/docs do not exist yet.

**Step 3: Write minimal implementation**
- Add argparse-based CLI commands: `run`, `advance`, `retry`, `step-back`, `escalate`.
- Document the sample fixture and usage in `README.md`.
- Add `make runtime-sample` helper.

**Step 4: Run test to verify pass**
- Run the CLI test.
- Expected: PASS.

---

## Verification
- `pytest tests/test_runtime_orchestrator.py -v`
- `make validate`
- `python3 scripts/run_orchestrator.py run --task-dir examples/runtime-fixtures/small-doc-task --route small`

## Done condition
- A local CLI runs at least one fixture end-to-end.
- Illegal transitions fail with explicit errors.
- Finalize is blocked when approval flags are absent.
- `run-state` and `decision-log` are deterministic and inspectable.
- Retry / step-back / escalate work as bounded local mechanics.
