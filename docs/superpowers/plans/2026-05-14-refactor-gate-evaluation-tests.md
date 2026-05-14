# Refactor Gate Evaluation Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace manual artifact creation with the `artifact_factory` fixture in `tests/runtime/test_gate_evaluation.py` to improve maintainability and consistency.

**Architecture:** Update test function signatures to include `artifact_factory` (and `write_json` where files are needed) and use the factory to generate test data.

**Tech Stack:** pytest, forgeflow-runtime

---

### Task 1: Refactor `run_state` related tests

**Files:**
- Modify: `tests/runtime/test_gate_evaluation.py`

- [ ] **Step 1: Update `test_record_completed_gate_appends_stage_gate_once`**

```python
def test_record_completed_gate_appends_stage_gate_once(artifact_factory) -> None:
    run_state = artifact_factory("run-state", completed_gates=[])

    record_completed_gate(run_state, "plan", stage_gate_map={"plan": "plan_approved"})
    record_completed_gate(run_state, "plan", stage_gate_map={"plan": "plan_approved"})

    assert run_state["completed_gates"] == ["plan_approved"]
```

- [ ] **Step 2: Update `test_record_completed_gate_skips_stage_without_gate`**

```python
def test_record_completed_gate_skips_stage_without_gate(artifact_factory) -> None:
    run_state = artifact_factory("run-state", completed_gates=[])

    record_completed_gate(run_state, "execute", stage_gate_map={"plan": "plan_approved"})

    assert run_state["completed_gates"] == []
```

- [ ] **Step 3: Run tests to verify**

Run: `pytest tests/runtime/test_gate_evaluation.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/runtime/test_gate_evaluation.py
git commit -m "refactor: use artifact_factory for run-state in gate evaluation tests"
```

---

### Task 2: Refactor `brief` related tests

**Files:**
- Modify: `tests/runtime/test_gate_evaluation.py`

- [ ] **Step 1: Update `test_clarification_gate_rejects_brief_without_explicit_specialist_skip_decisions`**

```python
def test_clarification_gate_rejects_brief_without_explicit_specialist_skip_decisions(tmp_path, artifact_factory, write_json) -> None:
    brief = artifact_factory(
        "brief",
        task_id="task-1",
        objective="small docs change",
        in_scope=["docs"],
        acceptance_criteria=["docs updated"],
        required_specialists=[],
    )
    # Ensure optional fields that should be missing are actually missing if factory provides defaults
    brief.pop("skipped_specialists", None)
    brief.pop("skip_rationale", None)
    
    write_json(tmp_path / "brief.json", brief)

    with pytest.raises(RuntimeViolation, match="must explicitly require or skip every specialist"):
        enforce_stage_gate(tmp_path, _policy_requiring_brief(), "plan", canonical_task_id="task-1")
```

- [ ] **Step 2: Update `test_clarification_gate_accepts_explicit_specialist_skips_with_rationale`**

```python
def test_clarification_gate_accepts_explicit_specialist_skips_with_rationale(tmp_path, artifact_factory, write_json) -> None:
    brief = artifact_factory(
        "brief",
        task_id="task-1",
        objective="small docs change",
        in_scope=["docs"],
        acceptance_criteria=["docs updated"],
        required_specialists=[],
        skipped_specialists=["security-review", "ux-review", "perf-review", "frontend-execute", "backend-execute", "infra-execute"],
        skip_rationale="Docs-only task; no specialist domain execution needed.",
    )
    write_json(tmp_path / "brief.json", brief)

    enforce_stage_gate(tmp_path, _policy_requiring_brief(), "plan", canonical_task_id="task-1")
```

- [ ] **Step 3: Update `test_clarification_gate_rejects_conflicting_specialist_decisions`**

```python
def test_clarification_gate_rejects_conflicting_specialist_decisions(tmp_path, artifact_factory, write_json) -> None:
    brief = artifact_factory(
        "brief",
        task_id="task-1",
        objective="small docs change",
        in_scope=["docs"],
        acceptance_criteria=["docs updated"],
        required_specialists=["security-review"],
        skipped_specialists=["security-review", "ux-review", "perf-review", "frontend-execute", "backend-execute", "infra-execute"],
        skip_rationale="Docs-only task; no specialist domain execution needed.",
    )
    write_json(tmp_path / "brief.json", brief)

    with pytest.raises(RuntimeViolation, match="cannot both require and skip specialists: security-review"):
        enforce_stage_gate(tmp_path, _policy_requiring_brief(), "plan", canonical_task_id="task-1")
```

- [ ] **Step 4: Update `test_clarification_gate_rejects_unknown_specialists`**

```python
def test_clarification_gate_rejects_unknown_specialists(tmp_path, artifact_factory, write_json) -> None:
    brief = artifact_factory(
        "brief",
        task_id="task-1",
        objective="small docs change",
        in_scope=["docs"],
        acceptance_criteria=["docs updated"],
        required_specialists=["unknown-review"],
        skipped_specialists=["security-review", "ux-review", "perf-review", "frontend-execute", "backend-execute", "infra-execute"],
        skip_rationale="Docs-only task; no specialist domain execution needed.",
    )
    write_json(tmp_path / "brief.json", brief)

    with pytest.raises(RuntimeViolation, match="failed schema validation: required_specialists/0"):
        enforce_stage_gate(tmp_path, _policy_requiring_brief(), "plan", canonical_task_id="task-1")
```

- [ ] **Step 5: Run tests to verify**

Run: `pytest tests/runtime/test_gate_evaluation.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/runtime/test_gate_evaluation.py
git commit -m "refactor: use artifact_factory in gate evaluation tests"
```
