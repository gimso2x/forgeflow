import json
from collections.abc import Callable
from pathlib import Path

import pytest

from forgeflow_runtime.orchestrator import RuntimeViolation, _canonical_task_id, load_runtime_policy, start_task
from forgeflow_runtime.task_identity import canonical_task_id


ROOT = Path(__file__).resolve().parents[2]


def _brief(task_id: str) -> dict:
    return {
        "schema_version": "0.1",
        "task_id": task_id,
        "objective": "Resolve identity",
        "in_scope": ["runtime"],
        "out_of_scope": [],
        "constraints": ["local only"],
        "acceptance_criteria": ["task id is stable"],
        "risk_level": "low",
    }


def _run_state(task_id: str) -> dict:
    return {
        "schema_version": "0.1",
        "task_id": task_id,
        "current_stage": "clarify",
        "status": "in_progress",
        "completed_gates": [],
        "failed_gates": [],
        "retries": {},
        "current_task_id": "",
        "spec_review_approved": False,
        "quality_review_approved": False,
    }


def test_canonical_task_id_prefers_matching_brief_and_keeps_orchestrator_alias(
    tmp_path: Path,
    write_json: Callable[[Path, dict], None],
) -> None:
    write_json(tmp_path / "brief.json", _brief("task-001"))
    write_json(tmp_path / "run-state.json", _run_state("task-001"))

    assert canonical_task_id(tmp_path) == "task-001"
    assert _canonical_task_id(tmp_path) == "task-001"


def test_canonical_task_id_rejects_brief_run_state_mismatch(
    tmp_path: Path,
    write_json: Callable[[Path, dict], None],
) -> None:
    write_json(tmp_path / "brief.json", _brief("task-001"))
    write_json(tmp_path / "run-state.json", _run_state("other-task"))

    with pytest.raises(RuntimeViolation, match="run-state.json task_id other-task does not match canonical task_id task-001"):
        canonical_task_id(tmp_path)


def test_start_task_rejects_existing_artifacts(
    tmp_path: Path,
    make_task_dir: Callable[[Path], Path],
    write_json: Callable[[Path, dict], None],
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = make_task_dir(tmp_path)
    write_json(task_dir / "brief.json", {"schema_version": "0.1", "task_id": "task-001"})

    with pytest.raises(RuntimeViolation, match="start requires an empty task directory"):
        start_task(task_dir=task_dir, policy=policy, route_name="small")


def test_start_task_bootstraps_medium_route_and_session_state(
    tmp_path: Path,
    assert_schema_valid: Callable[[str, dict], None],
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = tmp_path / "bootstrapped-medium"

    result = start_task(task_dir=task_dir, policy=policy, route_name="medium")

    assert result["route"] == "medium"
    assert result["current_stage"] == "clarify"
    assert "session-state.json" in result["created_artifacts"]
    assert "plan-ledger.json" in result["created_artifacts"]

    session_state = json.loads((task_dir / "session-state.json").read_text(encoding="utf-8"))
    assert_schema_valid("session-state", session_state)
    assert session_state["route"] == "medium"
    assert session_state["run_state_ref"] == "run-state.json"
    assert session_state["plan_ref"] == "plan.json"
    assert session_state["plan_ledger_ref"] == "plan-ledger.json"
    assert session_state["latest_checkpoint_ref"] == "checkpoint.json"
