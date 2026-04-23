import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from forgeflow_runtime.orchestrator import (
    RuntimeViolation,
    advance_to_next_stage,
    escalate_route,
    load_runtime_policy,
    resume_task,
    retry_stage,
    run_route,
    start_task,
    status_summary,
    step_back,
)


ROOT = Path(__file__).resolve().parents[1]


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


def test_load_runtime_policy_and_resolve_small_route() -> None:
    policy = load_runtime_policy(ROOT)

    assert policy.workflow_stages == [
        "clarify",
        "plan",
        "execute",
        "spec-review",
        "quality-review",
        "finalize",
        "long-run",
    ]
    assert policy.routes["small"] == [
        "clarify",
        "execute",
        "quality-review",
        "finalize",
    ]


def test_advance_blocks_missing_entry_artifacts(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    (task_dir / "run-state.json").unlink()

    with pytest.raises(RuntimeViolation, match="missing required artifacts for spec-review: run-state"):
        advance_to_next_stage(task_dir=task_dir, policy=policy, route_name="large_high_risk", current_stage="execute")


def test_run_route_requires_plan_ledger_for_medium_route(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
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
                    "verification": "pytest tests/test_runtime_orchestrator.py -q",
                    "rollback_note": "remove incomplete workflow edits if validation fails",
                }
            ],
        },
    )

    with pytest.raises(RuntimeViolation, match="medium route requires plan-ledger.json"):
        run_route(task_dir=task_dir, policy=policy, route_name="medium")


def test_run_route_syncs_current_task_from_plan_ledger(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
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
                    "verification": "pytest tests/test_runtime_orchestrator.py -q",
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
            "route": "medium",
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

    result = run_route(task_dir=task_dir, policy=policy, route_name="medium")

    assert result["current_stage"] == "finalize"
    assert result["current_task_id"] == "task-1"
    persisted_run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert persisted_run_state["current_task_id"] == "task-1"


def test_finalize_blocks_missing_review_flags(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
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

    with pytest.raises(RuntimeViolation, match="finalize requires run-state approval flags: quality_review_approved"):
        advance_to_next_stage(task_dir=task_dir, policy=policy, route_name="small", current_stage="quality-review")


def test_run_route_rejects_non_approved_quality_review(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "review_type": "quality",
            "verdict": "changes_requested",
            "findings": ["missing verification"],
            "next_action": "execute stage evidence를 보강",
        },
    )

    with pytest.raises(RuntimeViolation, match="quality-review requires approved quality review-report artifact"):
        run_route(task_dir=task_dir, policy=policy, route_name="small")


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


def test_small_route_runs_end_to_end_and_updates_state(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
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
    _assert_schema_valid("run-state", result)

    decision_log = json.loads((task_dir / "decision-log.json").read_text(encoding="utf-8"))
    _assert_schema_valid("decision-log", decision_log)
    decisions = [entry["decision"] for entry in decision_log["entries"]]
    assert decisions == [
        "route selected: small",
        "stage entered: clarify",
        "stage entered: execute",
        "stage entered: quality-review",
        "stage entered: finalize",
    ]


def test_run_route_rejects_schema_invalid_existing_run_state(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "invented-stage",
            "status": "in_progress",
            "completed_gates": [],
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

    with pytest.raises(RuntimeViolation, match="run-state.json failed schema validation"):
        run_route(task_dir=task_dir, policy=policy, route_name="small")


def test_run_route_rejects_schema_invalid_review_report(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": "looks fine",
        },
    )

    with pytest.raises(RuntimeViolation, match="review-report.json failed schema validation"):
        run_route(task_dir=task_dir, policy=policy, route_name="small")


def test_run_route_rejects_mismatched_review_report_task_id(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "other-task",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["looks fine"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )

    with pytest.raises(RuntimeViolation, match="review-report.json task_id other-task does not match canonical task_id task-001"):
        run_route(task_dir=task_dir, policy=policy, route_name="small")


def test_run_route_rejects_mismatched_eval_record_task_id(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = tmp_path / "large-task"
    task_dir.mkdir()
    _write_json(
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
    _write_json(
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
    _write_json(
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
    _write_json(
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
    _write_json(
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
    _write_json(
        task_dir / "eval-record.json",
        {
            "schema_version": "0.1",
            "task_id": "other-task",
            "outcome": "success",
            "what_worked": ["route worked"],
            "what_failed": [],
        },
    )

    with pytest.raises(RuntimeViolation, match="eval-record.json task_id other-task does not match canonical task_id task-large-001"):
        run_route(task_dir=task_dir, policy=policy, route_name="large_high_risk")


def test_retry_stage_rejects_mismatched_decision_log_task_id(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "decision-log.json",
        {
            "schema_version": "0.1",
            "task_id": "other-task",
            "entries": [],
        },
    )

    with pytest.raises(RuntimeViolation, match="decision-log.json task_id other-task does not match canonical task_id task-001"):
        retry_stage(task_dir=task_dir, stage_name="execute")


def test_run_route_migrates_legacy_decision_log_timestamps(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "decision-log.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "entries": [
                {
                    "timestamp": "seq-001",
                    "actor": "orchestrator",
                    "category": "routing",
                    "decision": "route selected: small",
                    "rationale": "legacy runtime output",
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

    result = run_route(task_dir=task_dir, policy=policy, route_name="small")

    assert result["status"] == "completed"
    decision_log = json.loads((task_dir / "decision-log.json").read_text(encoding="utf-8"))
    _assert_schema_valid("decision-log", decision_log)
    assert decision_log["entries"][0]["timestamp"] == "1970-01-01T00:00:01Z"


def test_large_route_runs_end_to_end_and_collects_both_review_flags(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = tmp_path / "large-task"
    task_dir.mkdir()
    _write_json(
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
    _write_json(
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
    _write_json(
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
    _write_json(
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
    _write_json(
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
    _write_json(
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


def test_large_route_rejects_missing_eval_record_before_long_run(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = tmp_path / "large-task-missing-eval"
    task_dir.mkdir()
    _write_json(
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
    _write_json(
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
    _write_json(
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
    _write_json(
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
    _write_json(
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
                    "attempt_count": 0
                }
            ]
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
            "plan_ref": "brief.json",
            "plan_ledger_ref": "plan-ledger.json",
            "run_state_ref": "run-state.json",
            "next_action": "retry execute",
            "open_blockers": [],
            "updated_at": "2026-04-22T00:05:00Z"
        },
    )

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
                    "attempt_count": 0
                }
            ]
        },
    )
    _write_json(
        task_dir / "checkpoint.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "small",
            "current_stage": "execute",
            "current_task_id": "task-1",
            "plan_ref": "brief.json",
            "plan_ledger_ref": "plan-ledger.json",
            "run_state_ref": "run-state.json",
            "next_action": "retry execute",
            "open_blockers": [],
            "updated_at": "2026-04-22T00:05:00Z"
        },
    )

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
            "updated_at": "2026-04-22T00:05:00Z"
        },
    )

    with pytest.raises(RuntimeViolation, match="recovery route small does not include current stage spec-review"):
        retry_stage(task_dir=task_dir, stage_name="spec-review", max_retries=2)


def test_step_back_rewinds_to_previous_stage(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    state = step_back(task_dir=task_dir, policy=policy, route_name="small", current_stage="quality-review")

    assert state["current_stage"] == "execute"
    assert state["status"] == "in_progress"
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    _assert_schema_valid("checkpoint", checkpoint)
    assert checkpoint["route"] == "small"
    assert checkpoint["current_stage"] == "execute"
    assert checkpoint["next_action"] == "Resume at quality-review after reloading canonical artifacts."


def test_escalate_route_switches_to_large_high_risk(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    state = escalate_route(task_dir=task_dir, from_route="small")

    assert state["status"] == "blocked"
    assert state["current_stage"] == "clarify"
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    _assert_schema_valid("checkpoint", checkpoint)
    assert checkpoint["route"] == "large_high_risk"
    assert checkpoint["current_stage"] == "clarify"
    assert checkpoint["next_action"] == "Resume at plan after reloading canonical artifacts."

    decision_log = json.loads((task_dir / "decision-log.json").read_text(encoding="utf-8"))
    assert decision_log["entries"][-1]["decision"] == "route escalated: small -> large_high_risk"


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


def _run_orchestrator_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/run_orchestrator.py", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_run_executes_sample_fixture(tmp_path: Path) -> None:
    task_dir = tmp_path / "cli-task"
    task_dir.mkdir()
    _write_json(
        task_dir / "brief.json",
        {
            "schema_version": "0.1",
            "task_id": "task-cli-001",
            "objective": "Run CLI route",
            "in_scope": ["runtime"],
            "out_of_scope": [],
            "constraints": ["local only"],
            "acceptance_criteria": ["cli works"],
            "risk_level": "low",
        },
    )
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "task-cli-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["cli looks fine"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )

    result = _run_orchestrator_cli("run", "--task-dir", str(task_dir), "--route", "small")

    assert result.returncode == 0
    assert (task_dir / "run-state.json").exists()
    assert (task_dir / "decision-log.json").exists()


def test_cli_supports_start_resume_and_status(tmp_path: Path) -> None:
    task_dir = tmp_path / "cli-start-task"

    start_result = _run_orchestrator_cli("start", "--task-dir", str(task_dir), "--route", "medium")
    assert start_result.returncode == 0
    assert json.loads(start_result.stdout)["route"] == "medium"

    status_result = _run_orchestrator_cli("status", "--task-dir", str(task_dir), "--route", "medium")
    assert status_result.returncode == 0
    assert json.loads(status_result.stdout)["current_stage"] == "clarify"

    resume_result = _run_orchestrator_cli("resume", "--task-dir", str(task_dir), "--route", "medium")
    assert resume_result.returncode == 0
    assert json.loads(resume_result.stdout)["route"] == "medium"


def test_cli_supports_recovery_commands(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    advance_result = _run_orchestrator_cli(
        "advance",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--current-stage",
        "clarify",
    )
    assert advance_result.returncode == 0
    assert json.loads(advance_result.stdout)["next_stage"] == "execute"

    retry_result = _run_orchestrator_cli("retry", "--task-dir", str(task_dir), "--stage", "execute", "--max-retries", "2")
    assert retry_result.returncode == 0
    assert json.loads(retry_result.stdout)["retries"]["execute"] == 1

    step_back_result = _run_orchestrator_cli(
        "step-back",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--current-stage",
        "quality-review",
    )
    assert step_back_result.returncode == 0
    assert json.loads(step_back_result.stdout)["current_stage"] == "execute"

    escalate_result = _run_orchestrator_cli("escalate", "--task-dir", str(task_dir), "--from-route", "small")
    assert escalate_result.returncode == 0
    assert json.loads(escalate_result.stdout)["status"] == "blocked"


def test_cli_reports_runtime_violations_without_tracebacks(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    for command_args, expected_error in [
        (("run", "--task-dir", str(task_dir), "--route", "unknown"), "ERROR: unknown route: unknown"),
        (
            ("advance", "--task-dir", str(task_dir), "--route", "unknown", "--current-stage", "clarify"),
            "ERROR: unknown route: unknown",
        ),
        (
            ("step-back", "--task-dir", str(task_dir), "--route", "unknown", "--current-stage", "quality-review"),
            "ERROR: unknown route: unknown",
        ),
        (("escalate", "--task-dir", str(task_dir), "--from-route", "unknown"), "ERROR: unknown route for escalation: unknown"),
    ]:
        result = _run_orchestrator_cli(*command_args)

        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr.startswith(expected_error)


def test_medium_and_large_runtime_fixtures_run_end_to_end(tmp_path: Path) -> None:
    fixtures_root = ROOT / "examples" / "runtime-fixtures"

    for fixture_name, route_name, expected_stage in [
        ("medium-refactor-task", "medium", "finalize"),
        ("large-migration-task", "large_high_risk", "long-run"),
    ]:
        source_dir = fixtures_root / fixture_name
        task_dir = tmp_path / fixture_name
        subprocess.run(["cp", "-R", str(source_dir), str(task_dir)], check=True)

        result = run_route(task_dir=task_dir, policy=load_runtime_policy(ROOT), route_name=route_name)

        assert result["status"] == "completed"
        assert result["current_stage"] == expected_stage


def test_adherence_eval_cli_runs_valid_and_negative_fixtures() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_adherence_evals.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ADHERENCE EVALS: PASS" in result.stdout
    assert "small-doc-task" in result.stdout
    assert "resume-small-task" in result.stdout
    assert "medium-refactor-task" in result.stdout
    assert "large-migration-task" in result.stdout
    assert "missing-quality-approval" in result.stdout
    assert "invalid-review-report" in result.stdout
    assert "missing-run-state-before-spec-review" in result.stdout
    assert "missing-eval-record-before-long-run" in result.stdout
    assert "mixed-task-review-report" in result.stdout
    assert "mixed-task-decision-log" in result.stdout
    assert "checkpoint-gate-drift" in result.stdout
    assert "future-gate-checkpoint-drift" in result.stdout
    assert "completed-checkpoint-drift" in result.stdout
