import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from forgeflow_runtime.orchestrator import (
    RuntimeViolation,
    advance_to_next_stage,
    load_runtime_policy,
    resume_task,
    run_route,
    status_summary,
)


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
                    "verification": "pytest tests/runtime/test_checkpoint_resume.py -q",
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


def test_run_route_resumes_from_existing_checkpoint(tmp_path: Path) -> None:
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
        task_dir / "decision-log.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "entries": [
                {
                    "timestamp": "2026-04-22T00:00:00Z",
                    "actor": "orchestrator",
                    "category": "stage-transition",
                    "decision": "stage entered: execute",
                    "rationale": "checkpoint created during an earlier run",
                    "affected_artifacts": ["run-state", "decision-log"],
                }
            ],
        },
    )
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
            "next_action": "quality-review를 검증하고 finalize로 진행",
            "open_blockers": [],
            "updated_at": "2026-04-22T00:05:00Z"
        },
    )

    result = run_route(task_dir=task_dir, policy=policy, route_name="small")

    assert result["current_stage"] == "finalize"
    assert result["status"] == "completed"
    assert result["completed_gates"] == [
        "clarification_complete",
        "execution_evidenced",
        "quality_review_passed",
        "ready_to_finalize",
    ]

    decision_log = json.loads((task_dir / "decision-log.json").read_text(encoding="utf-8"))
    decisions = [entry["decision"] for entry in decision_log["entries"]]
    assert decisions == [
        "stage entered: execute",
        "route resumed: small from execute",
        "stage entered: quality-review",
        "stage entered: finalize",
    ]
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    _assert_schema_valid("checkpoint", checkpoint)
    assert checkpoint["current_stage"] == "finalize"
    assert checkpoint["run_state_ref"] == "run-state.json"
    assert checkpoint["latest_review_ref"] == "review-report.json"
    assert checkpoint["next_action"] == "Route complete. Review final artifacts and hand off results."
    assert checkpoint["open_blockers"] == []


def test_run_route_rejects_mismatched_checkpoint_route(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "checkpoint.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_stage": "clarify",
            "plan_ref": "brief.json",
            "plan_ledger_ref": "run-state.json",
            "run_state_ref": "run-state.json",
            "next_action": "route를 재개",
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
            "findings": ["looks fine"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )

    with pytest.raises(RuntimeViolation, match="checkpoint.json route medium does not match requested route small"):
        run_route(task_dir=task_dir, policy=policy, route_name="small")


def test_run_route_rejects_checkpoint_gate_drift(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "execute",
            "status": "in_progress",
            "completed_gates": ["execution_evidenced"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "",
            "spec_review_approved": False,
            "quality_review_approved": False,
        },
    )
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

    with pytest.raises(RuntimeViolation, match="run-state checkpoint is missing completed gates before execute: clarification_complete"):
        run_route(task_dir=task_dir, policy=policy, route_name="small")


def test_run_route_rejects_future_gate_checkpoint_drift(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "execute",
            "status": "in_progress",
            "completed_gates": ["clarification_complete", "quality_review_passed"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "",
            "spec_review_approved": False,
            "quality_review_approved": False,
        },
    )
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

    with pytest.raises(RuntimeViolation, match="run-state checkpoint has out-of-sequence completed gates at execute: quality_review_passed"):
        run_route(task_dir=task_dir, policy=policy, route_name="small")


def test_run_route_rejects_incomplete_completed_checkpoint(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "execute",
            "status": "completed",
            "completed_gates": ["clarification_complete", "execution_evidenced"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "",
            "spec_review_approved": False,
            "quality_review_approved": False,
            "final_status": "success",
        },
    )
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

    with pytest.raises(RuntimeViolation, match="completed run-state checkpoint must already be at terminal stage finalize"):
        run_route(task_dir=task_dir, policy=policy, route_name="small")


def test_advance_rejects_mismatched_run_state_stage(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)

    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    run_state["current_stage"] = "execute"
    _write_json(task_dir / "run-state.json", run_state)

    with pytest.raises(RuntimeViolation, match="requested current_stage clarify does not match persisted run-state stage execute"):
        advance_to_next_stage(task_dir=task_dir, policy=policy, route_name="small", current_stage="clarify")


def test_resume_rejects_medium_session_state_with_wrong_plan_ledger_ref(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir, route_name="medium")
    _write_json(
        task_dir / "checkpoint.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_stage": "clarify",
            "plan_ref": "plan.json",
            "plan_ledger_ref": "plan-ledger.json",
            "run_state_ref": "run-state.json",
            "next_action": "execute로 진행",
            "open_blockers": [],
            "updated_at": "2026-04-22T00:05:00Z",
        },
    )
    _write_json(
        task_dir / "session-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_stage": "clarify",
            "plan_ref": "plan.json",
            "plan_ledger_ref": "run-state.json",
            "run_state_ref": "run-state.json",
            "latest_checkpoint_ref": "checkpoint.json",
            "next_action": "execute로 진행",
            "updated_at": "2026-04-22T00:05:00Z",
        },
    )

    with pytest.raises(RuntimeViolation, match="session-state.json plan_ledger_ref run-state.json must point to plan-ledger.json for route medium"):
        resume_task(task_dir=task_dir, policy=policy, route_name="medium")


def test_resume_rejects_stale_session_state_latest_review_ref(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "review-report-spec.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "review_type": "spec",
            "verdict": "approved",
            "findings": ["spec ok"],
            "approved_by": "spec-reviewer",
            "next_action": "quality-review로 진행",
        },
    )
    _write_json(
        task_dir / "review-report-quality.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["quality ok"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )
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
            "latest_review_ref": "review-report-quality.json",
            "next_action": "execute로 진행",
            "open_blockers": [],
            "updated_at": "2026-04-22T00:05:00Z",
        },
    )
    _write_json(
        task_dir / "session-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "small",
            "current_stage": "clarify",
            "plan_ref": "brief.json",
            "plan_ledger_ref": "run-state.json",
            "run_state_ref": "run-state.json",
            "latest_checkpoint_ref": "checkpoint.json",
            "latest_review_ref": "review-report-spec.json",
            "next_action": "execute로 진행",
            "updated_at": "2026-04-22T00:05:00Z",
        },
    )

    with pytest.raises(RuntimeViolation, match="session-state.json latest_review_ref review-report-spec.json does not match canonical latest review review-report-quality.json"):
        resume_task(task_dir=task_dir, policy=policy, route_name="small")


def test_status_rejects_session_state_route_drift(tmp_path: Path) -> None:
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
            "open_blockers": [],
            "updated_at": "2026-04-22T00:05:00Z",
        },
    )
    _write_json(
        task_dir / "session-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_stage": "clarify",
            "plan_ref": "brief.json",
            "plan_ledger_ref": "run-state.json",
            "run_state_ref": "run-state.json",
            "latest_checkpoint_ref": "checkpoint.json",
            "next_action": "execute로 진행",
            "updated_at": "2026-04-22T00:05:00Z",
        },
    )

    with pytest.raises(RuntimeViolation, match="session-state.json route medium does not match canonical route small"):
        status_summary(task_dir=task_dir, policy=policy, route_name="small")


def test_status_rejects_session_state_stage_drift(tmp_path: Path) -> None:
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
            "open_blockers": [],
            "updated_at": "2026-04-22T00:05:00Z",
        },
    )
    _write_json(
        task_dir / "session-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "small",
            "current_stage": "execute",
            "plan_ref": "brief.json",
            "plan_ledger_ref": "run-state.json",
            "run_state_ref": "run-state.json",
            "latest_checkpoint_ref": "checkpoint.json",
            "next_action": "execute로 진행",
            "updated_at": "2026-04-22T00:05:00Z",
        },
    )

    with pytest.raises(RuntimeViolation, match="session-state.json current_stage execute does not match run-state current_stage clarify"):
        status_summary(task_dir=task_dir, policy=policy, route_name="small")


def test_status_rejects_session_state_latest_review_ref_that_escapes_task_dir(tmp_path: Path) -> None:
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
            "open_blockers": [],
            "updated_at": "2026-04-22T00:05:00Z",
        },
    )
    _write_json(
        task_dir / "session-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "small",
            "current_stage": "clarify",
            "plan_ref": "brief.json",
            "plan_ledger_ref": "run-state.json",
            "run_state_ref": "run-state.json",
            "latest_checkpoint_ref": "checkpoint.json",
            "latest_review_ref": "../review-report.json",
            "next_action": "execute로 진행",
            "updated_at": "2026-04-22T00:05:00Z",
        },
    )

    with pytest.raises(RuntimeViolation, match="session-state.json latest_review_ref ../review-report.json escapes task directory"):
        status_summary(task_dir=task_dir, policy=policy, route_name="small")
