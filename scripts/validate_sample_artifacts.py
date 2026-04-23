#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
POSITIVE_SAMPLES = {
    "examples/artifacts/brief.sample.json": ROOT / "schemas/brief.schema.json",
    "examples/artifacts/plan.sample.json": ROOT / "schemas/plan.schema.json",
    "examples/artifacts/plan-ledger.sample.json": ROOT / "schemas/plan-ledger.schema.json",
    "examples/artifacts/decision-log.sample.json": ROOT / "schemas/decision-log.schema.json",
    "examples/artifacts/run-state.sample.json": ROOT / "schemas/run-state.schema.json",
    "examples/artifacts/review-report-spec.sample.json": ROOT / "schemas/review-report.schema.json",
    "examples/artifacts/review-report-quality.sample.json": ROOT / "schemas/review-report.schema.json",
    "examples/artifacts/eval-record.sample.json": ROOT / "schemas/eval-record.schema.json",
    "examples/artifacts/checkpoint.sample.json": ROOT / "schemas/checkpoint.schema.json",
    "examples/artifacts/session-state.sample.json": ROOT / "schemas/session-state.schema.json",
}
NEGATIVE_SAMPLES = {
    "run-state-invalid-stage.sample.json": ROOT / "schemas/run-state.schema.json",
    "decision-log-invalid-entry.sample.json": ROOT / "schemas/decision-log.schema.json",
    "review-report-approved-missing-approved-by.sample.json": ROOT / "schemas/review-report.schema.json",
    "review-report-blocked-missing-next-action.sample.json": ROOT / "schemas/review-report.schema.json",
    "review-report-open-blockers-wrong-type.sample.json": ROOT / "schemas/review-report.schema.json",
    "review-report-approved-with-open-blockers.sample.json": ROOT / "schemas/review-report.schema.json",
    "review-report-approved-unsafe.sample.json": ROOT / "schemas/review-report.schema.json",
    "plan-ledger-done-without-evidence.sample.json": ROOT / "schemas/plan-ledger.schema.json",
    "checkpoint-invalid-updated-at.sample.json": ROOT / "schemas/checkpoint.schema.json",
    "session-state-missing-ref.sample.json": ROOT / "schemas/session-state.schema.json",
}
FORMAT_CHECKER = FormatChecker()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_error(error) -> str:
    location = ".".join(str(part) for part in error.path)
    return f"{location or '<root>'}: {error.message}"


def validate_json_file(*, fixture_path: Path, schema_path: Path) -> list[str]:
    validator = Draft202012Validator(_load_json(schema_path), format_checker=FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(_load_json(fixture_path)), key=lambda err: list(err.path))
    return [_format_error(error) for error in errors]


def main() -> int:
    errors: list[str] = []
    checked_positive: list[str] = []
    checked_negative: list[str] = []

    for sample_rel, schema_path in POSITIVE_SAMPLES.items():
        sample_path = ROOT / sample_rel
        sample_errors = validate_json_file(fixture_path=sample_path, schema_path=schema_path)
        if sample_errors:
            errors.extend(f"{sample_rel}: {err}" for err in sample_errors)
        checked_positive.append(sample_rel)

    invalid_root = ROOT / "examples" / "artifacts" / "invalid"
    for fixture_name, schema_path in NEGATIVE_SAMPLES.items():
        fixture_path = invalid_root / fixture_name
        sample_errors = validate_json_file(fixture_path=fixture_path, schema_path=schema_path)
        if not sample_errors:
            errors.append(f"examples/artifacts/invalid/{fixture_name}: expected validation failure")
        checked_negative.append(fixture_name)

    if errors:
        print("SAMPLE ARTIFACT VALIDATION: FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("SAMPLE ARTIFACT VALIDATION: PASS")
    print(f"- positive fixtures checked: {len(checked_positive)}")
    print(f"- negative fixtures rejected: {len(checked_negative)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
