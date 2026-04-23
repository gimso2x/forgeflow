#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _schema_required(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    req = data.get("required", [])
    if not isinstance(req, list):
        raise ValueError(f"required must be a list in {path}")
    return req


def _format_jsonschema_errors(errors: list[Any]) -> str:
    return "; ".join(f"{'/'.join(map(str, err.path)) or '<root>'}: {err.message}" for err in errors[:3])


def _validate_yaml_schema(schema_path: Path, document: Any, source_name: str) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda err: list(err.path))
    if not errors:
        return []
    return [f"{source_name} failed schema validation: {_format_jsonschema_errors(errors)}"]


def validate_policy_root(root: Path) -> list[str]:
    errors: list[str] = []
    canonical_dir = root / "policy" / "canonical"
    policy_docs = {
        "workflow": _load_yaml(canonical_dir / "workflow.yaml"),
        "stages": _load_yaml(canonical_dir / "stages.yaml"),
        "gates": _load_yaml(canonical_dir / "gates.yaml"),
        "complexity-routing": _load_yaml(canonical_dir / "complexity-routing.yaml"),
    }

    policy_schema_dir = root / "schemas" / "policy"
    for name, document in policy_docs.items():
        errors.extend(
            _validate_yaml_schema(
                policy_schema_dir / f"{name}.schema.json",
                document,
                source_name=f"{name}.yaml",
            )
        )

    if errors:
        return errors

    workflow_stages = policy_docs["workflow"]["stages"]
    stage_keys = list(policy_docs["stages"]["stages"].keys())
    if workflow_stages != stage_keys:
        errors.append(f"stage mismatch: workflow={workflow_stages} stages={stage_keys}")

    order = policy_docs["workflow"]["review_order"]
    if order != ["spec-review", "quality-review"]:
        errors.append(f"invalid review order: {order}")

    routes = {name: payload["stages"] for name, payload in policy_docs["complexity-routing"]["routes"].items()}
    if "small" not in routes or routes["small"] != ["clarify", "execute", "quality-review", "finalize"]:
        errors.append("small route mismatch")
    if "medium" not in routes or routes["medium"] != ["clarify", "plan", "execute", "quality-review", "finalize"]:
        errors.append("medium route mismatch")
    if "large_high_risk" not in routes or routes["large_high_risk"] != [
        "clarify",
        "plan",
        "execute",
        "spec-review",
        "quality-review",
        "finalize",
        "long-run",
    ]:
        errors.append("large_high_risk route mismatch")

    for schema_name in ["brief", "plan", "decision-log", "run-state", "review-report", "eval-record"]:
        schema_path = root / "schemas" / f"{schema_name}.schema.json"
        required = _schema_required(schema_path)
        if "schema_version" not in required:
            errors.append(f"{schema_name}.schema.json missing schema_version")
        if "task_id" not in required:
            errors.append(f"{schema_name}.schema.json missing task_id")

    run_state_required = _schema_required(root / "schemas" / "run-state.schema.json")
    for field in ["spec_review_approved", "quality_review_approved"]:
        if field not in run_state_required:
            errors.append(f"run-state.schema.json missing {field}")

    review_text = (root / "docs" / "review-model.md").read_text(encoding="utf-8")
    if "spec-review 승인 전 finalize 금지" not in review_text:
        errors.append("review-model missing spec-review finalize guard")
    if "quality-review 승인 전 high-risk finalize 금지" not in review_text:
        errors.append("review-model missing quality-review high-risk guard")
    if "run-state.spec_review_approved" not in review_text:
        errors.append("review-model missing run-state approval flag guidance")

    gates = policy_docs["gates"]["gates"]
    if gates.get("spec_review_passed", {}).get("review_type") != "spec":
        errors.append("gates missing spec review_type binding")
    if gates.get("quality_review_passed", {}).get("review_type") != "quality":
        errors.append("gates missing quality review_type binding")
    if gates.get("ready_to_finalize", {}).get("run_state_flags") != ["spec_review_approved", "quality_review_approved"]:
        errors.append("gates missing finalize run_state_flags binding")

    return errors


def main() -> int:
    errors = validate_policy_root(ROOT)
    if errors:
        print("POLICY VALIDATION: FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    routes = list(_load_yaml(ROOT / "policy" / "canonical" / "complexity-routing.yaml")["routes"].keys())
    print("POLICY VALIDATION: PASS")
    print(f"- stages: {_load_yaml(ROOT / 'policy' / 'canonical' / 'workflow.yaml')['stages']}")
    print(f"- review order: {_load_yaml(ROOT / 'policy' / 'canonical' / 'workflow.yaml')['review_order']}")
    print(f"- routes checked: {routes}")
    print("- review gate semantics: bound to review_type and run-state flags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
