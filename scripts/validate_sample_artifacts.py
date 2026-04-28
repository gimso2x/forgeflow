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
    "examples/artifacts/issue-drafts.sample.json": ROOT / "schemas" / "issue-drafts.schema.json",
    "examples/artifacts/interface-spec.sample.json": ROOT / "schemas" / "interface-spec.schema.json",
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
    "plan-step-missing-fulfills.sample.json": ROOT / "schemas/plan.schema.json",
    "checkpoint-invalid-updated-at.sample.json": ROOT / "schemas/checkpoint.schema.json",
    "session-state-missing-ref.sample.json": ROOT / "schemas/session-state.schema.json",
    "interface-spec-single-option.sample.json": ROOT / "schemas/interface-spec.schema.json",
}
NEGATIVE_SEMANTIC_PLAN_SAMPLES = {
    "plan-missing-verify-target.sample.json": "fulfills 'missing-target' has no verify_plan target",
    "plan-missing-contract-artifact.sample.json": "contracts artifact missing-contracts.md does not exist",
    "plan-stale-journey-verify.sample.json": "verify_plan targets journey 'stale-journey' but no journey exists",
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


def validate_plan_traceability(*, plan_path: Path) -> list[str]:
    plan = _load_json(plan_path)
    errors: list[str] = []
    steps = plan.get("steps", [])
    step_ids = {step.get("id") for step in steps}
    verify_plan = plan.get("verify_plan", [])
    verify_targets = {entry.get("target") for entry in verify_plan if entry.get("type") in {"sub_req", "step"}}
    journey_verify_targets = {entry.get("target") for entry in verify_plan if entry.get("type") == "journey"}
    journeys = plan.get("journeys", [])
    journey_ids = {journey.get("id") for journey in journeys}

    for step in steps:
        step_id = step.get("id")
        for dependency in step.get("dependencies", []) or []:
            if dependency not in step_ids:
                errors.append(f"step {step_id} depends on unknown step '{dependency}'")
        for fulfilled in step.get("fulfills", []) or []:
            if fulfilled not in verify_targets:
                errors.append(f"step {step_id} fulfills '{fulfilled}' has no verify_plan target")

    for journey in journeys:
        journey_id = journey.get("id")
        if journey_id not in journey_verify_targets:
            errors.append(f"journey {journey_id} has no verify_plan journey target")
        for composed in journey.get("composes", []) or []:
            if composed not in verify_targets:
                errors.append(f"journey {journey_id} composes '{composed}' has no verify_plan target")

    for journey_target in journey_verify_targets:
        if journey_target not in journey_ids:
            errors.append(f"verify_plan targets journey '{journey_target}' but no journey exists")

    contracts = plan.get("contracts") or {}
    artifact = contracts.get("artifact")
    if artifact is not None and not (plan_path.parent / artifact).is_file():
        errors.append(f"contracts artifact {artifact} does not exist")

    return errors


def main() -> int:
    errors: list[str] = []
    checked_positive: list[str] = []
    checked_negative: list[str] = []

    for sample_rel, schema_path in POSITIVE_SAMPLES.items():
        sample_path = ROOT / sample_rel
        sample_errors = validate_json_file(fixture_path=sample_path, schema_path=schema_path)
        if sample_errors:
            errors.extend(f"{sample_rel}: {err}" for err in sample_errors)
        if schema_path.name == "plan.schema.json":
            semantic_errors = validate_plan_traceability(plan_path=sample_path)
            if semantic_errors:
                errors.extend(f"{sample_rel}: {err}" for err in semantic_errors)
        checked_positive.append(sample_rel)

    invalid_root = ROOT / "examples" / "artifacts" / "invalid"
    for fixture_name, schema_path in NEGATIVE_SAMPLES.items():
        fixture_path = invalid_root / fixture_name
        sample_errors = validate_json_file(fixture_path=fixture_path, schema_path=schema_path)
        if not sample_errors:
            errors.append(f"examples/artifacts/invalid/{fixture_name}: expected validation failure")
        checked_negative.append(fixture_name)

    for fixture_name, expected_error in NEGATIVE_SEMANTIC_PLAN_SAMPLES.items():
        fixture_path = invalid_root / fixture_name
        schema_errors = validate_json_file(fixture_path=fixture_path, schema_path=ROOT / "schemas/plan.schema.json")
        if schema_errors:
            errors.extend(f"examples/artifacts/invalid/{fixture_name}: schema should pass before semantic check: {err}" for err in schema_errors)
            checked_negative.append(fixture_name)
            continue
        semantic_errors = validate_plan_traceability(plan_path=fixture_path)
        if not any(expected_error in err for err in semantic_errors):
            errors.append(
                f"examples/artifacts/invalid/{fixture_name}: expected semantic validation failure containing {expected_error!r}; got {semantic_errors!r}"
            )
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
