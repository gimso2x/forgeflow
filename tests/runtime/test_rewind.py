import json
from collections.abc import Callable
from pathlib import Path

from forgeflow_runtime.orchestrator import load_runtime_policy, run_route, step_back


ROOT = Path(__file__).resolve().parents[2]


def test_step_back_rewinds_to_previous_stage(
    tmp_path: Path,
    make_task_dir: Callable[[Path], Path],
    assert_schema_valid: Callable[[str, dict], None],
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = make_task_dir(tmp_path)
    state = step_back(task_dir=task_dir, policy=policy, route_name="small", current_stage="quality-review")

    assert state["current_stage"] == "execute"
    assert state["status"] == "in_progress"
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    assert_schema_valid("checkpoint", checkpoint)
    assert checkpoint["route"] == "small"
    assert checkpoint["current_stage"] == "execute"
    assert checkpoint["next_action"] == "Resume at quality-review after reloading canonical artifacts."


def test_step_back_rewinds_plan_ledger_progress_for_medium_route(
    tmp_path: Path,
    make_task_dir: Callable[[Path], Path],
    medium_plan_artifacts: Callable[..., None],
    write_json: Callable[[Path, dict], None],
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = make_task_dir(tmp_path)
    medium_plan_artifacts(task_dir)
    write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "quality-review",
            "status": "in_progress",
            "completed_gates": ["clarification_complete"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "task-1",
            "spec_review_approved": False,
            "quality_review_approved": False,
        },
    )
    write_json(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "completed_stages": ["clarify", "plan", "execute"],
            "completed_gates": ["clarification_complete", "plan_executable", "execution_evidenced"],
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
                    "evidence_refs": [
                        "run-state.json#gate:plan_executable",
                        "run-state.json#gate:execution_evidenced",
                    ],
                    "attempt_count": 0,
                }
            ],
        },
    )
    write_json(
        task_dir / "checkpoint.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_stage": "quality-review",
            "current_task_id": "task-1",
            "plan_ref": "plan.json",
            "plan_ledger_ref": "plan-ledger.json",
            "run_state_ref": "run-state.json",
            "latest_review_ref": "review-report.json",
            "next_action": "Resume at finalize after review approval.",
            "open_blockers": [],
            "updated_at": "2026-04-22T00:00:00Z",
        },
    )
    write_json(
        task_dir / "session-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_stage": "quality-review",
            "current_task_id": "task-1",
            "plan_ref": "plan.json",
            "plan_ledger_ref": "plan-ledger.json",
            "run_state_ref": "run-state.json",
            "latest_checkpoint_ref": "checkpoint.json",
            "latest_review_ref": "review-report.json",
            "next_action": "Resume at finalize after review approval.",
            "updated_at": "2026-04-22T00:00:00Z",
        },
    )
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

    state = step_back(task_dir=task_dir, policy=policy, route_name="medium", current_stage="quality-review")

    assert state["current_stage"] == "execute"
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    assert persisted_plan_ledger["completed_stages"] == ["clarify", "plan"]
    assert persisted_plan_ledger["completed_gates"] == ["clarification_complete", "plan_executable"]
    assert persisted_plan_ledger["tasks"][0]["evidence_refs"] == ["run-state.json#gate:plan_executable"]

    result = run_route(task_dir=task_dir, policy=policy, route_name="medium")

    assert result["current_stage"] == "finalize"
    decision_log = json.loads((task_dir / "decision-log.json").read_text(encoding="utf-8"))
    decisions = [entry["decision"] for entry in decision_log["entries"]]
    assert "step back: quality-review -> execute" in decisions
    # After rewind, execute stage injects execute-intelligence entries
    resume_idx = decisions.index("route resumed: medium from execute")
    assert "stage entered: execute" in decisions[resume_idx:]
    assert "stage entered: quality-review" in decisions
    assert "stage entered: finalize" in decisions
    assert decisions[-1] == "stage entered: finalize"


def test_step_back_large_route_preserves_spec_evidence_and_clears_quality_flag(
    tmp_path: Path,
    make_task_dir: Callable[[Path], Path],
    medium_plan_artifacts: Callable[..., None],
    write_json: Callable[[Path, dict], None],
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = make_task_dir(tmp_path)
    medium_plan_artifacts(task_dir, route_name="large_high_risk")
    write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "long-run",
            "status": "in_progress",
            "completed_gates": ["clarification_complete"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "task-1",
            "spec_review_approved": True,
            "quality_review_approved": True,
        },
    )
    write_json(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "large_high_risk",
            "completed_stages": ["clarify", "plan", "execute", "spec-review", "quality-review", "finalize"],
            "completed_gates": [
                "clarification_complete",
                "plan_executable",
                "execution_evidenced",
                "spec_review_passed",
                "quality_review_passed",
                "ready_to_finalize",
            ],
            "retries": {},
            "current_task_id": "task-1",
            "last_review_verdict": "approved",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "update workflow docs",
                    "depends_on": [],
                    "files": ["docs/workflow.md"],
                    "parallel_safe": False,
                    "status": "in_progress",
                    "required_gates": ["machine", "validator"],
                    "evidence_refs": [
                        "run-state.json#gate:plan_executable",
                        "run-state.json#gate:execution_evidenced",
                        "review-report-spec.json#verdict:approved",
                        "review-report-quality.json#verdict:approved",
                        "run-state.json#gate:quality_review_passed",
                        "run-state.json#gate:ready_to_finalize",
                        "eval-record.json#verdict:approved",
                    ],
                    "attempt_count": 1,
                }
            ],
        },
    )

    state = step_back(task_dir=task_dir, policy=policy, route_name="large_high_risk", current_stage="long-run")

    assert state["current_stage"] == "finalize"
    assert state["spec_review_approved"] is True
    assert state["quality_review_approved"] is False
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    assert "review-report-spec.json#verdict:approved" in persisted_plan_ledger["tasks"][0]["evidence_refs"]
    assert "review-report-quality.json#verdict:approved" in persisted_plan_ledger["tasks"][0]["evidence_refs"]
    assert "eval-record.json#verdict:approved" not in persisted_plan_ledger["tasks"][0]["evidence_refs"]
