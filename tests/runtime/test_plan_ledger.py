import json
from pathlib import Path

import pytest

from forgeflow_runtime.orchestrator import (
    RuntimeViolation,
    advance_to_next_stage,
    load_runtime_policy,
    retry_stage,
    run_route,
)


ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_task_dir(tmp_path: Path) -> Path:
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    _write_json(
        task_dir / "brief.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "objective": "Run a small route",
            "in_scope": ["runtime"],
            "out_of_scope": [],
            "constraints": ["local only"],
            "acceptance_criteria": ["route works"],
            "risk_level": "low",
        },
    )
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "clarify",
            "status": "in_progress",
            "completed_gates": ["clarification_complete"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "",
            "spec_review_approved": False,
            "quality_review_approved": False,
        },
    )
    return task_dir


def test_run_route_requires_plan_ledger_for_medium_route(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "plan.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "steps": [
                {
                    "id": "step-1",
                    "objective": "update workflow docs",
                    "dependencies": [],
                    "expected_output": "workflow docs reflect medium route behavior",
                    "verification": "pytest tests/test_runtime_orchestrator.py -q",
                    "rollback_note": "remove incomplete workflow edits if validation fails",
                }
            ],
        },
    )

    with pytest.raises(RuntimeViolation, match="medium route requires plan-ledger.json"):
        run_route(task_dir=task_dir, policy=policy, route_name="medium")


def test_advance_requires_plan_ledger_for_medium_route(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "plan.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "steps": [
                {
                    "id": "step-1",
                    "objective": "update workflow docs",
                    "dependencies": [],
                    "expected_output": "workflow docs reflect medium route behavior",
                    "verification": "pytest tests/test_runtime_orchestrator.py -q",
                    "rollback_note": "remove incomplete workflow edits if validation fails",
                }
            ],
        },
    )
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    run_state["current_stage"] = "plan"
    _write_json(task_dir / "run-state.json", run_state)

    with pytest.raises(RuntimeViolation, match="medium route requires plan-ledger.json"):
        advance_to_next_stage(task_dir=task_dir, policy=policy, route_name="medium", current_stage="plan")


def _write_medium_plan_artifacts(task_dir: Path, *, route_name: str = "medium") -> None:
    _write_json(
        task_dir / "plan.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "steps": [
                {
                    "id": "step-1",
                    "objective": "update workflow docs",
                    "dependencies": [],
                    "expected_output": "workflow docs reflect medium route behavior",
                    "verification": "pytest tests/test_runtime_orchestrator.py -q",
                    "rollback_note": "remove incomplete workflow edits if validation fails",
                }
            ],
        },
    )
    _write_json(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": route_name,
            "completed_stages": [],
            "completed_gates": [],
            "retries": {},
            "current_task_id": "task-1",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "update workflow docs",
                    "depends_on": [],
                    "files": ["docs/workflow.md"],
                    "parallel_safe": False,
                    "status": "in_progress",
                    "required_gates": ["machine", "validator"],
                    "evidence_refs": [],
                    "attempt_count": 0,
                }
            ],
        },
    )


def test_run_route_syncs_current_task_from_plan_ledger(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir)
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["looks fine"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )

    result = run_route(task_dir=task_dir, policy=policy, route_name="medium")

    assert result["current_stage"] == "finalize"
    assert result["current_task_id"] == "task-1"
    persisted_run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert persisted_run_state["current_task_id"] == "task-1"
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    assert persisted_plan_ledger["tasks"][0]["status"] == "done"
    assert persisted_plan_ledger["tasks"][0]["attempt_count"] == 1
    assert persisted_plan_ledger["completed_stages"] == ["clarify", "plan", "execute", "quality-review", "finalize"]
    assert persisted_plan_ledger["completed_gates"] == [
        "clarification_complete",
        "plan_executable",
        "execution_evidenced",
        "quality_review_passed",
        "ready_to_finalize",
    ]
    assert "run-state.json#gate:plan_executable" in persisted_plan_ledger["tasks"][0]["evidence_refs"]
    assert "review-report.json#verdict:approved" in persisted_plan_ledger["tasks"][0]["evidence_refs"]
    assert persisted_plan_ledger["last_review_verdict"] == "approved"
    assert persisted_run_state["completed_gates"] == ["clarification_complete"]


def test_retry_stage_updates_plan_ledger_attempts(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir)

    result = retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)

    assert result["retries"]["execute"] == 1
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    persisted_run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert persisted_plan_ledger["tasks"][0]["attempt_count"] == 1
    assert persisted_plan_ledger["tasks"][0]["status"] == "in_progress"
    assert persisted_plan_ledger["retries"] == {"execute": 1}
    assert persisted_run_state["retries"] == {}


def test_advance_updates_plan_ledger_gate_evidence(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir)
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    run_state["current_stage"] = "plan"
    _write_json(task_dir / "run-state.json", run_state)

    result = advance_to_next_stage(task_dir=task_dir, policy=policy, route_name="medium", current_stage="plan")

    assert result.next_stage == "execute"
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    persisted_run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert persisted_plan_ledger["tasks"][0]["status"] == "in_progress"
    assert persisted_plan_ledger["completed_stages"] == ["plan"]
    assert persisted_plan_ledger["completed_gates"] == ["plan_executable"]
    assert "run-state.json#gate:plan_executable" in persisted_plan_ledger["tasks"][0]["evidence_refs"]
    assert persisted_run_state["completed_gates"] == ["clarification_complete"]

