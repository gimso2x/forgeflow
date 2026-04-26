import json
from collections.abc import Callable
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


def test_run_route_requires_plan_ledger_for_medium_route(
    make_task_dir: Callable[[Path], Path], write_json: Callable[[Path, dict], None], tmp_path: Path
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = make_task_dir(tmp_path)
    write_json(
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


def test_advance_requires_plan_ledger_for_medium_route(
    make_task_dir: Callable[[Path], Path], write_json: Callable[[Path, dict], None], tmp_path: Path
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = make_task_dir(tmp_path)
    write_json(
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
    write_json(task_dir / "run-state.json", run_state)

    with pytest.raises(RuntimeViolation, match="medium route requires plan-ledger.json"):
        advance_to_next_stage(task_dir=task_dir, policy=policy, route_name="medium", current_stage="plan")


def _write_medium_plan_artifacts(
    task_dir: Path, write_json: Callable[[Path, dict], None], *, route_name: str = "medium"
) -> None:
    write_json(
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
    write_json(
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


def test_run_route_syncs_current_task_from_plan_ledger(
    make_task_dir: Callable[[Path], Path], write_json: Callable[[Path, dict], None], tmp_path: Path
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir, write_json)
    write_json(
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


def test_retry_stage_updates_plan_ledger_attempts(
    make_task_dir: Callable[[Path], Path], write_json: Callable[[Path, dict], None], tmp_path: Path
) -> None:
    task_dir = make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir, write_json)

    result = retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)

    assert result["retries"]["execute"] == 1
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    persisted_run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert persisted_plan_ledger["tasks"][0]["attempt_count"] == 1
    assert persisted_plan_ledger["tasks"][0]["status"] == "in_progress"
    assert persisted_plan_ledger["retries"] == {"execute": 1}
    assert persisted_run_state["retries"] == {}


def test_advance_updates_plan_ledger_gate_evidence(
    make_task_dir: Callable[[Path], Path], write_json: Callable[[Path, dict], None], tmp_path: Path
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir, write_json)
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    run_state["current_stage"] = "plan"
    write_json(task_dir / "run-state.json", run_state)

    result = advance_to_next_stage(task_dir=task_dir, policy=policy, route_name="medium", current_stage="plan")

    assert result.next_stage == "execute"
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    persisted_run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert persisted_plan_ledger["tasks"][0]["status"] == "in_progress"
    assert persisted_plan_ledger["completed_stages"] == ["plan"]
    assert persisted_plan_ledger["completed_gates"] == ["plan_executable"]
    assert "run-state.json#gate:plan_executable" in persisted_plan_ledger["tasks"][0]["evidence_refs"]
    assert persisted_run_state["completed_gates"] == ["clarification_complete"]
