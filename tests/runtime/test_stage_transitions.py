import json
from collections.abc import Callable
from pathlib import Path

import pytest

from forgeflow_runtime.generator import GenerationError
from forgeflow_runtime.orchestrator import RuntimeViolation, advance_to_next_stage, load_runtime_policy


ROOT = Path(__file__).resolve().parents[2]


def _write_medium_plan_artifacts(
    task_dir: Path,
    write_json: Callable[[Path, dict], None],
    *,
    route_name: str = "medium",
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
                    "verification": "pytest tests/runtime/test_stage_transitions.py -q",
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


def test_advance_blocks_missing_entry_artifacts(
    tmp_path: Path,
    make_task_dir: Callable[[Path], Path],
    write_json: Callable[[Path, dict], None],
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir, write_json, route_name="large_high_risk")
    (task_dir / "run-state.json").unlink()

    with pytest.raises(RuntimeViolation, match="missing required artifacts for spec-review: run-state"):
        advance_to_next_stage(task_dir=task_dir, policy=policy, route_name="large_high_risk", current_stage="execute")


def test_advance_can_execute_next_stage_immediately(
    tmp_path: Path,
    make_task_dir: Callable[[Path], Path],
    write_json: Callable[[Path, dict], None],
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir, write_json)
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    run_state["current_stage"] = "plan"
    write_json(task_dir / "run-state.json", run_state)

    result = advance_to_next_stage(
        task_dir=task_dir,
        policy=policy,
        route_name="medium",
        current_stage="plan",
        execute_immediately=True,
        adapter_target="codex",
    )

    assert result.next_stage == "execute"
    assert result.execution is not None
    assert result.execution["stage"] == "execute"
    assert result.execution["adapter"] == "codex"
    assert result.execution["status"] == "success"
    assert (task_dir / "execute-output.md").exists()
    assert "stub-codex-output" in (task_dir / "execute-output.md").read_text(encoding="utf-8")


def test_advance_execute_failure_keeps_previous_stage_state(
    tmp_path: Path,
    make_task_dir: Callable[[Path], Path],
    write_json: Callable[[Path, dict], None],
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir, write_json)
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    run_state["current_stage"] = "plan"
    write_json(task_dir / "run-state.json", run_state)

    with pytest.raises(GenerationError, match="unknown role: nonexistent-role"):
        advance_to_next_stage(
            task_dir=task_dir,
            policy=policy,
            route_name="medium",
            current_stage="plan",
            execute_immediately=True,
            role="nonexistent-role",
        )

    persisted_run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert persisted_run_state["current_stage"] == "plan"
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    assert persisted_plan_ledger["completed_stages"] == []
    assert not (task_dir / "execute-output.md").exists()
