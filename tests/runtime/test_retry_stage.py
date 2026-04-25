import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from forgeflow_runtime.orchestrator import RuntimeViolation, retry_stage


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


def _write_medium_plan_ledger(task_dir: Path) -> None:
    _write_json(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_task_id": "task-1",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "execute bounded refactor",
                    "depends_on": [],
                    "files": ["run-state.json"],
                    "parallel_safe": False,
                    "status": "in_progress",
                    "required_gates": ["machine", "validator"],
                    "evidence_refs": [],
                    "attempt_count": 0,
                }
            ],
        },
    )


def _write_retry_checkpoint(task_dir: Path, *, route: str = "medium", stage: str = "execute") -> None:
    _write_json(
        task_dir / "checkpoint.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": route,
            "current_stage": stage,
            "current_task_id": "task-1",
            "plan_ref": "brief.json",
            "plan_ledger_ref": "plan-ledger.json",
            "run_state_ref": "run-state.json",
            "next_action": f"retry {stage}",
            "open_blockers": [],
            "updated_at": "2026-04-22T00:05:00Z",
        },
    )


def test_retry_is_bounded(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    first = retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)
    second = retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)

    assert first["retries"]["execute"] == 1
    assert second["retries"]["execute"] == 2
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    _assert_schema_valid("checkpoint", checkpoint)
    assert checkpoint["current_stage"] == "execute"
    assert checkpoint["run_state_ref"] == "run-state.json"
    assert checkpoint["next_action"] == "Resume at quality-review after reloading canonical artifacts."

    with pytest.raises(RuntimeViolation, match="retry budget exceeded for execute: 2/2"):
        retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)


def test_retry_stage_preserves_medium_route_checkpoint(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_ledger(task_dir)
    _write_retry_checkpoint(task_dir)

    state = retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)

    assert state["current_task_id"] == "task-1"
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    _assert_schema_valid("checkpoint", checkpoint)
    assert checkpoint["route"] == "medium"
    assert checkpoint["plan_ledger_ref"] == "plan-ledger.json"
    assert checkpoint["current_task_id"] == "task-1"
    assert checkpoint["next_action"] == "Resume at quality-review after reloading canonical artifacts."


def test_retry_stage_rejects_checkpoint_route_drift_against_plan_ledger(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_ledger(task_dir)
    _write_retry_checkpoint(task_dir, route="small")

    with pytest.raises(RuntimeViolation, match="checkpoint.json route small does not match canonical route medium"):
        retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)


def test_retry_stage_rejects_stage_outside_inferred_route(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "spec-review",
            "status": "in_progress",
            "completed_gates": ["clarification_complete", "plan_executable", "execution_evidenced"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "",
            "spec_review_approved": False,
            "quality_review_approved": False,
        },
    )
    _write_json(
        task_dir / "checkpoint.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "small",
            "current_stage": "spec-review",
            "plan_ref": "brief.json",
            "plan_ledger_ref": "run-state.json",
            "run_state_ref": "run-state.json",
            "next_action": "retry spec-review",
            "open_blockers": [],
            "updated_at": "2026-04-22T00:05:00Z",
        },
    )

    with pytest.raises(RuntimeViolation, match="recovery route small does not include current stage spec-review"):
        retry_stage(task_dir=task_dir, stage_name="spec-review", max_retries=2)
