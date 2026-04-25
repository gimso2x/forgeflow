import json
from pathlib import Path

from forgeflow_runtime.orchestrator import load_runtime_policy, resume_task, status_summary


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
                    "verification": "pytest tests/runtime/test_status_resume.py -q",
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


def test_resume_task_reloads_session_state_and_returns_current_truth(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "execute",
            "status": "in_progress",
            "completed_gates": ["clarification_complete", "execution_evidenced"],
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
            "current_stage": "execute",
            "plan_ref": "brief.json",
            "plan_ledger_ref": "run-state.json",
            "run_state_ref": "run-state.json",
            "latest_review_ref": "review-report.json",
            "next_action": "checkpoint truth",
            "open_blockers": [],
            "updated_at": "2026-04-22T00:05:00Z"
        },
    )
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["resume evidence exists"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )
    _write_json(
        task_dir / "session-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "small",
            "current_stage": "execute",
            "current_task_id": "",
            "plan_ref": "brief.json",
            "plan_ledger_ref": "run-state.json",
            "run_state_ref": "run-state.json",
            "latest_checkpoint_ref": "checkpoint.json",
            "latest_review_ref": "review-report.json",
            "next_action": "quality-review로 진행",
            "updated_at": "2026-04-22T00:05:00Z"
        },
    )

    result = resume_task(task_dir=task_dir, policy=policy)

    assert result["task_id"] == "task-001"
    assert result["route"] == "small"
    assert result["current_stage"] == "execute"
    assert result["next_action"] == "checkpoint truth"


def test_status_summary_reports_current_truth(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "checkpoint.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "small",
            "current_stage": "clarify",
            "plan_ref": "brief.json",
            "plan_ledger_ref": "run-state.json",
            "run_state_ref": "run-state.json",
            "next_action": "execute로 진행",
            "open_blockers": ["need evidence"],
            "updated_at": "2026-04-22T00:05:00Z"
        },
    )
    _write_json(
        task_dir / "session-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "small",
            "current_stage": "clarify",
            "current_task_id": "",
            "plan_ref": "brief.json",
            "plan_ledger_ref": "run-state.json",
            "run_state_ref": "run-state.json",
            "latest_checkpoint_ref": "checkpoint.json",
            "next_action": "execute로 진행",
            "updated_at": "2026-04-22T00:05:00Z"
        },
    )

    result = status_summary(task_dir=task_dir, policy=policy)

    assert result["task_id"] == "task-001"
    assert result["route"] == "small"
    assert result["current_stage"] == "clarify"
    assert result["open_blockers"] == ["need evidence"]
    assert result["required_gates"] == ["execution_evidenced", "quality_review_passed", "ready_to_finalize"]
    assert result["latest_review_verdict"] is None
    assert result["next_action"] == "execute로 진행"


def test_resume_task_prefers_plan_ledger_current_task_for_medium_route(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir)
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "execute",
            "status": "in_progress",
            "completed_gates": ["clarification_complete"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "stale-task-id",
            "spec_review_approved": False,
            "quality_review_approved": False,
        },
    )
    _write_json(
        task_dir / "checkpoint.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_stage": "execute",
            "current_task_id": "task-1",
            "plan_ref": "plan.json",
            "plan_ledger_ref": "plan-ledger.json",
            "run_state_ref": "run-state.json",
            "next_action": "quality-review로 진행",
            "open_blockers": [],
            "updated_at": "2026-04-22T00:05:00Z"
        },
    )
    _write_json(
        task_dir / "session-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_stage": "execute",
            "current_task_id": "task-1",
            "plan_ref": "plan.json",
            "plan_ledger_ref": "plan-ledger.json",
            "run_state_ref": "run-state.json",
            "latest_checkpoint_ref": "checkpoint.json",
            "next_action": "quality-review로 진행",
            "updated_at": "2026-04-22T00:05:00Z"
        },
    )

    result = resume_task(task_dir=task_dir, policy=policy, route_name="medium")

    assert result["current_task_id"] == "task-1"


def test_status_summary_prefers_plan_ledger_current_task_for_medium_route(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir)
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "execute",
            "status": "in_progress",
            "completed_gates": ["clarification_complete"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "stale-task-id",
            "spec_review_approved": False,
            "quality_review_approved": False,
        },
    )
    _write_json(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "completed_stages": ["clarify", "plan"],
            "completed_gates": ["clarification_complete", "plan_executable"],
            "retries": {"execute": 1},
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
                    "evidence_refs": ["run-state.json#gate:plan_executable"],
                    "attempt_count": 1,
                }
            ],
        },
    )
    _write_json(
        task_dir / "checkpoint.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_stage": "execute",
            "current_task_id": "task-1",
            "plan_ref": "plan.json",
            "plan_ledger_ref": "plan-ledger.json",
            "run_state_ref": "run-state.json",
            "next_action": "quality-review로 진행",
            "open_blockers": ["need execution evidence"],
            "updated_at": "2026-04-22T00:05:00Z"
        },
    )
    _write_json(
        task_dir / "session-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_stage": "execute",
            "current_task_id": "task-1",
            "plan_ref": "plan.json",
            "plan_ledger_ref": "plan-ledger.json",
            "run_state_ref": "run-state.json",
            "latest_checkpoint_ref": "checkpoint.json",
            "next_action": "quality-review로 진행",
            "updated_at": "2026-04-22T00:05:00Z"
        },
    )

    result = status_summary(task_dir=task_dir, policy=policy, route_name="medium")

    assert result["current_task_id"] == "task-1"
    assert result["required_gates"] == ["execution_evidenced", "quality_review_passed", "ready_to_finalize"]
