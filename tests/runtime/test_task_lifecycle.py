import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from forgeflow_runtime.orchestrator import RuntimeViolation, load_runtime_policy, start_task


ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))


def _assert_schema_valid(name: str, payload: dict) -> None:
    errors = sorted(Draft202012Validator(_load_schema(name)).iter_errors(payload), key=lambda err: list(err.path))
    assert not errors, [f"{list(err.path)}: {err.message}" for err in errors]


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


def test_start_task_rejects_existing_artifacts(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(task_dir / "brief.json", {"schema_version": "0.1", "task_id": "task-001"})

    with pytest.raises(RuntimeViolation, match="start requires an empty task directory"):
        start_task(task_dir=task_dir, policy=policy, route_name="small")


def test_start_task_bootstraps_medium_route_and_session_state(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = tmp_path / "bootstrapped-medium"

    result = start_task(task_dir=task_dir, policy=policy, route_name="medium")

    assert result["route"] == "medium"
    assert result["current_stage"] == "clarify"
    assert "session-state.json" in result["created_artifacts"]
    assert "plan-ledger.json" in result["created_artifacts"]

    session_state = json.loads((task_dir / "session-state.json").read_text(encoding="utf-8"))
    _assert_schema_valid("session-state", session_state)
    assert session_state["route"] == "medium"
    assert session_state["run_state_ref"] == "run-state.json"
    assert session_state["plan_ref"] == "plan.json"
    assert session_state["plan_ledger_ref"] == "plan-ledger.json"
    assert session_state["latest_checkpoint_ref"] == "checkpoint.json"
