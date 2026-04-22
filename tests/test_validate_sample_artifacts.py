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
