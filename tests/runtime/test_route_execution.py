import json
from collections.abc import Callable
from pathlib import Path

import pytest

from forgeflow_runtime.orchestrator import RuntimeViolation, load_runtime_policy, run_route
from forgeflow_runtime.route_execution import build_route_result, route_entry_decision, route_iteration_stages


ROOT = Path(__file__).resolve().parents[2]


def test_route_iteration_stages_starts_at_resume_index() -> None:
    route = ["clarify", "plan", "execute", "quality-review", "finalize"]

    assert route_iteration_stages(route, 2) == ["execute", "quality-review", "finalize"]


def test_build_route_result_uses_plan_ledger_progress_when_present() -> None:
    run_state = {
        "current_stage": "finalize",
        "status": "completed",
        "completed_gates": ["stale-run-state-gate"],
        "retries": {"execute": 1},
    }
    plan_ledger = {
        "completed_gates": ["clarification_complete", "ready_to_finalize"],
        "retries": {"execute": 2, "quality-review": 1},
    }

    result = build_route_result(run_state, plan_ledger)

    assert result == {
        "current_stage": "finalize",
        "status": "completed",
        "completed_gates": ["clarification_complete", "ready_to_finalize"],
        "retries": {"execute": 2, "quality-review": 1},
    }
    assert run_state["completed_gates"] == ["stale-run-state-gate"]


def test_route_entry_decision_selects_new_route() -> None:
    decision = route_entry_decision(route_name="small", start_index=0, resume_from_stage=None, route_length=4)

    assert decision.decision == "route selected: small"
    assert decision.rationale == "canonical complexity route applied"


def test_route_entry_decision_resumes_from_validated_stage() -> None:
    decision = route_entry_decision(
        route_name="medium",
        start_index=2,
        resume_from_stage="execute",
        route_length=5,
    )

    assert decision.decision == "route resumed: medium from execute"
    assert decision.rationale == "validated checkpoint state reused instead of replaying prior stages"


def test_route_entry_decision_marks_complete_route() -> None:
    decision = route_entry_decision(
        route_name="small",
        start_index=4,
        resume_from_stage="finalize",
        route_length=4,
    )

    assert decision.decision == "route already complete: small"
    assert decision.rationale == "validated checkpoint already reached route terminal stage"
    assert decision.already_complete is True


def test_small_route_runs_end_to_end_and_updates_state(
    tmp_path: Path,
    write_json: Callable[[Path, dict], None],
    assert_schema_valid: Callable[[str, dict], None],
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    write_json(
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

    result = run_route(task_dir=task_dir, policy=policy, route_name="small")

    assert result["current_stage"] == "finalize"
    assert result["status"] == "completed"
    assert result["final_status"] == "success"
    assert result["completed_gates"] == [
        "clarification_complete",
        "execution_evidenced",
        "quality_review_passed",
        "ready_to_finalize",
    ]
    assert_schema_valid("run-state", result)

    decision_log = json.loads((task_dir / "decision-log.json").read_text(encoding="utf-8"))
    assert_schema_valid("decision-log", decision_log)
    decisions = [entry["decision"] for entry in decision_log["entries"]]
    assert decisions == [
        "route selected: small",
        "stage entered: clarify",
        "stage entered: execute",
        "stage entered: quality-review",
        "stage entered: finalize",
    ]


def test_large_route_runs_end_to_end_and_collects_both_review_flags(
    tmp_path: Path,
    write_json: Callable[[Path, dict], None],
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = tmp_path / "large-task"
    task_dir.mkdir()
    write_json(
        task_dir / "brief.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-001",
            "objective": "Run a large route",
            "in_scope": ["runtime"],
            "out_of_scope": [],
            "constraints": ["local only"],
            "acceptance_criteria": ["large route works"],
            "risk_level": "high",
        },
    )
    write_json(
        task_dir / "plan.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-001",
            "steps": [
                {
                    "id": "step-1",
                    "objective": "Run route",
                    "expected_output": "done",
                    "verification": "pytest",
                }
            ],
        },
    )
    write_json(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-001",
            "route": "large_high_risk",
            "current_task_id": "task-1",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "Run route",
                    "depends_on": [],
                    "files": ["plan.json", "review-report-spec.json", "review-report-quality.json", "eval-record.json"],
                    "parallel_safe": False,
                    "status": "in_progress",
                    "required_gates": ["machine", "validator", "scenario"],
                    "evidence_refs": [],
                    "attempt_count": 0
                }
            ]
        },
    )
    write_json(
        task_dir / "review-report-spec.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-001",
            "review_type": "spec",
            "verdict": "approved",
            "findings": ["spec ok"],
            "approved_by": "spec-reviewer",
            "next_action": "quality-review로 진행",
        },
    )
    write_json(
        task_dir / "review-report-quality.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["quality ok"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )
    write_json(
        task_dir / "eval-record.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-001",
            "outcome": "success",
            "what_worked": ["route worked"],
            "what_failed": [],
        },
    )

    result = run_route(task_dir=task_dir, policy=policy, route_name="large_high_risk")

    assert result["current_stage"] == "long-run"
    assert result["status"] == "completed"
    assert result["final_status"] == "success"
    assert result["spec_review_approved"] is True
    assert result["quality_review_approved"] is True
    assert result["completed_gates"] == [
        "clarification_complete",
        "plan_executable",
        "execution_evidenced",
        "spec_review_passed",
        "quality_review_passed",
        "ready_to_finalize",
        "worth_long_run_capture",
    ]


def test_large_route_rejects_missing_eval_record_before_long_run(
    tmp_path: Path,
    write_json: Callable[[Path, dict], None],
) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = tmp_path / "large-task-missing-eval"
    task_dir.mkdir()
    write_json(
        task_dir / "brief.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-002",
            "objective": "Run a large route",
            "in_scope": ["runtime"],
            "out_of_scope": [],
            "constraints": ["local only"],
            "acceptance_criteria": ["large route works"],
            "risk_level": "high",
        },
    )
    write_json(
        task_dir / "plan.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-002",
            "steps": [
                {
                    "id": "step-1",
                    "objective": "Run route",
                    "expected_output": "done",
                    "verification": "pytest",
                }
            ],
        },
    )
    write_json(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-002",
            "route": "large_high_risk",
            "current_task_id": "task-1",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "Run route",
                    "depends_on": [],
                    "files": ["plan.json", "review-report-spec.json", "review-report-quality.json", "eval-record.json"],
                    "parallel_safe": False,
                    "status": "in_progress",
                    "required_gates": ["machine", "validator", "scenario"],
                    "evidence_refs": [],
                    "attempt_count": 0
                }
            ]
        },
    )
    write_json(
        task_dir / "review-report-spec.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-002",
            "review_type": "spec",
            "verdict": "approved",
            "findings": ["spec ok"],
            "approved_by": "spec-reviewer",
            "next_action": "quality-review로 진행",
        },
    )
    write_json(
        task_dir / "review-report-quality.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-002",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["quality ok"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )

    with pytest.raises(RuntimeViolation, match="long-run requires artifacts satisfying gate worth_long_run_capture: eval-record"):
        run_route(task_dir=task_dir, policy=policy, route_name="large_high_risk")
