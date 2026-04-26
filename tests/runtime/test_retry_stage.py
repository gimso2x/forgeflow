import json
from collections.abc import Callable
from pathlib import Path

import pytest

from forgeflow_runtime.orchestrator import RuntimeViolation, retry_stage


def _write_retry_checkpoint(
    task_dir: Path,
    write_json: Callable[[Path, dict], None],
    *,
    route: str = "medium",
    stage: str = "execute",
) -> None:
    write_json(
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


def test_retry_is_bounded(
    tmp_path: Path,
    make_task_dir: Callable[[Path], Path],
    assert_schema_valid: Callable[[str, dict], None],
) -> None:
    task_dir = make_task_dir(tmp_path)

    first = retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)
    second = retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)

    assert first["retries"]["execute"] == 1
    assert second["retries"]["execute"] == 2
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    assert_schema_valid("checkpoint", checkpoint)
    assert checkpoint["current_stage"] == "execute"
    assert checkpoint["run_state_ref"] == "run-state.json"
    assert checkpoint["next_action"] == "Resume at quality-review after reloading canonical artifacts."

    with pytest.raises(RuntimeViolation, match="retry budget exceeded for execute: 2/2"):
        retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)


def test_retry_stage_preserves_medium_route_checkpoint(
    tmp_path: Path,
    make_task_dir: Callable[[Path], Path],
    medium_plan_artifacts: Callable[..., None],
    write_json: Callable[[Path, dict], None],
    assert_schema_valid: Callable[[str, dict], None],
) -> None:
    task_dir = make_task_dir(tmp_path)
    medium_plan_artifacts(task_dir)
    _write_retry_checkpoint(task_dir, write_json)

    state = retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)

    assert state["current_task_id"] == "task-1"
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    assert_schema_valid("checkpoint", checkpoint)
    assert checkpoint["route"] == "medium"
    assert checkpoint["plan_ledger_ref"] == "plan-ledger.json"
    assert checkpoint["current_task_id"] == "task-1"
    assert checkpoint["next_action"] == "Resume at quality-review after reloading canonical artifacts."


def test_retry_stage_rejects_checkpoint_route_drift_against_plan_ledger(
    tmp_path: Path,
    make_task_dir: Callable[[Path], Path],
    medium_plan_artifacts: Callable[..., None],
    write_json: Callable[[Path, dict], None],
) -> None:
    task_dir = make_task_dir(tmp_path)
    medium_plan_artifacts(task_dir)
    _write_retry_checkpoint(task_dir, write_json, route="small")

    with pytest.raises(RuntimeViolation, match="checkpoint.json route small does not match canonical route medium"):
        retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)


def test_retry_stage_rejects_stage_outside_inferred_route(
    tmp_path: Path,
    make_task_dir: Callable[[Path], Path],
    write_json: Callable[[Path, dict], None],
) -> None:
    task_dir = make_task_dir(tmp_path)
    write_json(
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
    write_json(
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
