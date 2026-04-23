from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_SAMPLES_PATH = ROOT / "scripts" / "validate_sample_artifacts.py"


def _load_validate_samples_module():
    spec = importlib.util.spec_from_file_location("validate_sample_artifacts", VALIDATE_SAMPLES_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_state_schema_constrains_current_stage_enum() -> None:
    schema = json.loads((ROOT / "schemas" / "run-state.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    errors = sorted(
        validator.iter_errors(
            {
                "schema_version": "0.1",
                "task_id": "task-001",
                "current_stage": "totally-made-up-stage",
                "status": "in_progress",
                "completed_gates": [],
                "failed_gates": [],
                "retries": {},
                "spec_review_approved": False,
                "quality_review_approved": False,
            }
        ),
        key=lambda err: list(err.path),
    )

    assert errors
    assert any(list(err.path) == ["current_stage"] for err in errors)


def test_decision_log_schema_rejects_invalid_timestamp_and_actor() -> None:
    schema = json.loads((ROOT / "schemas" / "decision-log.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    errors = sorted(
        validator.iter_errors(
            {
                "schema_version": "0.1",
                "task_id": "task-001",
                "entries": [
                    {
                        "timestamp": "not-a-timestamp",
                        "actor": "mystery-agent",
                        "category": "scope",
                        "decision": "keep going",
                        "rationale": "because",
                    }
                ],
            }
        ),
        key=lambda err: list(err.path),
    )

    assert errors
    assert any(list(err.path) == ["entries", 0, "timestamp"] for err in errors)
    assert any(list(err.path) == ["entries", 0, "actor"] for err in errors)


def test_review_report_schema_requires_approved_by_for_approved_verdict() -> None:
    schema = json.loads((ROOT / "schemas" / "review-report.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    errors = sorted(
        validator.iter_errors(
            {
                "schema_version": "0.1",
                "task_id": "task-001",
                "review_type": "quality",
                "verdict": "approved",
                "findings": ["looks fine"],
                "next_action": "finalize 가능",
            }
        ),
        key=lambda err: list(err.path),
    )

    assert errors
    assert any(err.validator == "required" and "approved_by" in err.message for err in errors)


def test_review_report_schema_requires_next_action_for_non_approved_verdict() -> None:
    schema = json.loads((ROOT / "schemas" / "review-report.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    errors = sorted(
        validator.iter_errors(
            {
                "schema_version": "0.1",
                "task_id": "task-001",
                "review_type": "spec",
                "verdict": "blocked",
                "findings": ["missing plan evidence"],
                "approved_by": "spec-reviewer",
            }
        ),
        key=lambda err: list(err.path),
    )

    assert errors
    assert any(err.validator == "required" and "next_action" in err.message for err in errors)


def test_review_report_schema_accepts_safe_flag_and_open_blockers() -> None:
    schema = json.loads((ROOT / "schemas" / "review-report.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    errors = sorted(
        validator.iter_errors(
            {
                "schema_version": "0.1",
                "task_id": "task-001",
                "review_type": "quality",
                "verdict": "changes_requested",
                "findings": ["verification gap remains"],
                "open_blockers": ["integration test evidence missing"],
                "safe_for_next_stage": False,
                "next_action": "execute stage evidence를 보강",
            }
        ),
        key=lambda err: list(err.path),
    )

    assert not errors


def test_plan_ledger_schema_requires_evidence_for_done_tasks() -> None:
    schema = json.loads((ROOT / "schemas" / "plan-ledger.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    errors = sorted(
        validator.iter_errors(
            {
                "schema_version": "0.1",
                "task_id": "task-001",
                "route": "medium",
                "tasks": [
                    {
                        "id": "task-1",
                        "title": "done without proof",
                        "depends_on": [],
                        "files": ["docs/example.md"],
                        "parallel_safe": True,
                        "status": "done",
                        "required_gates": [],
                        "evidence_refs": [],
                        "attempt_count": 0,
                    }
                ],
            }
        ),
        key=lambda err: list(err.path),
    )

    assert errors
    assert any(list(err.path) == ["tasks", 0, "required_gates"] for err in errors)
    assert any(list(err.path) == ["tasks", 0, "evidence_refs"] for err in errors)


def test_checkpoint_schema_requires_valid_timestamp() -> None:
    schema = json.loads((ROOT / "schemas" / "checkpoint.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    errors = sorted(
        validator.iter_errors(
            {
                "schema_version": "0.1",
                "task_id": "task-001",
                "route": "medium",
                "current_stage": "execute",
                "plan_ref": "examples/artifacts/plan.sample.json",
                "plan_ledger_ref": "examples/artifacts/plan-ledger.sample.json",
                "run_state_ref": "examples/artifacts/run-state.sample.json",
                "next_action": "Resume",
                "open_blockers": [],
                "updated_at": "not-a-timestamp",
            }
        ),
        key=lambda err: list(err.path),
    )

    assert errors
    assert any(list(err.path) == ["updated_at"] for err in errors)


def test_session_state_schema_requires_core_refs() -> None:
    schema = json.loads((ROOT / "schemas" / "session-state.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    errors = sorted(
        validator.iter_errors(
            {
                "schema_version": "0.1",
                "task_id": "task-001",
                "route": "medium",
                "current_stage": "execute",
                "current_task_id": "task-1",
                "run_state_ref": "run-state.json",
                "latest_checkpoint_ref": "checkpoint.json",
                "next_action": "resume",
                "updated_at": "2026-04-23T00:00:00Z",
            }
        ),
        key=lambda err: list(err.path),
    )

    assert errors
    assert any(err.validator == "required" and "plan_ref" in err.message for err in errors)
    assert any(err.validator == "required" and "plan_ledger_ref" in err.message for err in errors)


def test_validate_sample_artifacts_tracks_positive_and_negative_fixtures() -> None:
    validate_samples = _load_validate_samples_module()

    assert validate_samples.POSITIVE_SAMPLES
    assert validate_samples.NEGATIVE_SAMPLES

    result = subprocess.run(
        [sys.executable, "scripts/validate_sample_artifacts.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "SAMPLE ARTIFACT VALIDATION: PASS" in result.stdout
    assert "negative fixtures rejected" in result.stdout


@pytest.mark.parametrize(
    ("fixture_name", "expected_fragment"),
    [
        ("run-state-invalid-stage.sample.json", "current_stage"),
        ("decision-log-invalid-entry.sample.json", "timestamp"),
        ("review-report-approved-missing-approved-by.sample.json", "approved_by"),
        ("review-report-blocked-missing-next-action.sample.json", "next_action"),
        ("review-report-open-blockers-wrong-type.sample.json", "open_blockers"),
        ("plan-ledger-done-without-evidence.sample.json", "evidence_refs"),
        ("checkpoint-invalid-updated-at.sample.json", "updated_at"),
        ("session-state-missing-ref.sample.json", "plan_ref"),
    ],
)
def test_negative_fixtures_fail_for_expected_reason(fixture_name: str, expected_fragment: str) -> None:
    validate_samples = _load_validate_samples_module()
    fixture_path = ROOT / "examples" / "artifacts" / "invalid" / fixture_name

    errors = validate_samples.validate_json_file(
        fixture_path=fixture_path,
        schema_path=validate_samples.NEGATIVE_SAMPLES[fixture_name],
    )

    assert errors
    assert any(expected_fragment in error for error in errors)
