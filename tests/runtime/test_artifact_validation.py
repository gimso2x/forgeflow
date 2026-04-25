import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from forgeflow_runtime.orchestrator import RuntimeViolation, load_runtime_policy, retry_stage, run_route


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
                    "attempt_count": 0,
                }
            ],
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
