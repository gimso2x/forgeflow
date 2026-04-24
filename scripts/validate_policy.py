#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

APPROVED_EVOLUTION_COMMAND_IDS = {"generated-adapter-drift", "no-env-commit"}

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


def _evolution_example_paths(root: Path) -> list[Path]:
    example_dir = root / "examples" / "evolution"
    if not example_dir.is_dir():
        return []
    return sorted(example_dir.glob("*.json"))


def _validate_evolution_examples(root: Path, evolution: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    example_dir = root / "examples" / "evolution"
    example_paths = _evolution_example_paths(root)
    if not example_paths:
        return [f"evolution examples missing: {example_dir.relative_to(root)}"]
    rule_schema_path = root / "schemas" / "evolution-rule.schema.json"
    rule_schema = json.loads(rule_schema_path.read_text(encoding="utf-8"))
    rule_validator = Draft202012Validator(rule_schema)
    hard_gate_requires = set(evolution["scopes"]["project"].get("hard_gate_requires", []))
    for example_path in example_paths:
        rel_path = example_path.relative_to(root)
        try:
            rule = json.loads(example_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{rel_path} invalid JSON: {exc}")
            continue

        schema_errors = sorted(rule_validator.iter_errors(rule), key=lambda err: list(err.path))
        if schema_errors:
            errors.append(f"{rel_path} failed schema validation: {_format_jsonschema_errors(schema_errors)}")
            continue
        command_id = rule["check"]["command_id"]
        if command_id not in APPROVED_EVOLUTION_COMMAND_IDS:
            errors.append(f"{rel_path} uses unapproved command_id: {command_id}")
        evidence = rule.get("hard_gate_evidence", {})
        if set(evidence.keys()) != hard_gate_requires:
            errors.append(f"{rel_path} hard_gate_evidence must match project hard_gate_requires")
        serialized = json.dumps(rule)
        for forbidden in ["raw_prompt", "raw_frustration"]:
            if forbidden in serialized:
                errors.append(f"{rel_path} must not include {forbidden}")
    return errors


def validate_policy_root(root: Path) -> list[str]:
    errors: list[str] = []
    canonical_dir = root / "policy" / "canonical"
    policy_docs = {
        "workflow": _load_yaml(canonical_dir / "workflow.yaml"),
        "stages": _load_yaml(canonical_dir / "stages.yaml"),
        "gates": _load_yaml(canonical_dir / "gates.yaml"),
        "complexity-routing": _load_yaml(canonical_dir / "complexity-routing.yaml"),
        "evolution": _load_yaml(canonical_dir / "evolution.yaml"),
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

    stage_policy = policy_docs["stages"]["stages"]
    required_stage_non_negotiables = {
        "clarify": ["brief", "route"],
        "plan": ["expected output", "verification"],
        "execute": ["decision-log", "run-state"],
        "spec-review": ["acceptance criteria", "worker self-report"],
        "quality-review": ["maintainability", "run-state.quality_review_approved"],
        "finalize": ["review approvals", "artifacts"],
        "long-run": ["eval-record", "reusable learning"],
    }
    for stage_name, required_terms in required_stage_non_negotiables.items():
        non_negotiables = stage_policy.get(stage_name, {}).get("non_negotiables", [])
        if len(non_negotiables) < 3:
            errors.append(f"{stage_name} missing at least three non_negotiables")
            continue
        joined = "\n".join(non_negotiables)
        for term in required_terms:
            if term not in joined:
                errors.append(f"{stage_name} non_negotiables missing required term: {term}")

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

    evolution = policy_docs["evolution"]
    global_scope = evolution["scopes"]["global"]
    project_scope = evolution["scopes"]["project"]
    if global_scope.get("activation") != "explicit_opt_in":
        errors.append("evolution global scope must be explicit opt-in")
    if "advise_review" in global_scope.get("permissions", []):
        errors.append("evolution global scope must not advise review gates")
    for forbidden in ["raw_prompt_storage_by_default", "raw_frustration_text_by_default", "hard_enforcement_by_default", "cross_project_exit_2"]:
        if forbidden not in global_scope.get("forbidden", []):
            errors.append(f"evolution global scope missing forbidden guard: {forbidden}")
    if project_scope.get("artifact_root") != ".forgeflow/evolution":
        errors.append("evolution project artifact_root must be .forgeflow/evolution")
    for required in ["project_local_enablement", "soft_soak_period", "independent_recurrence_or_audited_maintainer_enablement", "deterministic_check", "low_false_positive_rate", "rollback_available", "eval_record", "audit_trail"]:
        if required not in project_scope.get("hard_gate_requires", []):
            errors.append(f"evolution hard gate missing requirement: {required}")
    if evolution.get("rule_lifecycle") != ["candidate", "soft", "hard_candidate", "adopted_hard", "retired"]:
        errors.append("evolution rule_lifecycle must stay v1-minimal")
    retrieval = evolution.get("retrieval_contract", {})
    if retrieval.get("max_patterns") != 3:
        errors.append("evolution retrieval must cap global patterns at 3")
    for required in ["confidence", "why_matched", "scope", "source_count"]:
        if required not in retrieval.get("requires", []):
            errors.append(f"evolution retrieval missing required field: {required}")
    errors.extend(_validate_evolution_examples(root, evolution))

    long_run_text = (root / "docs" / "long-run-model.md").read_text(encoding="utf-8")
    for required in ["eval-record.json", "worth_long_run_capture", "No evidence, no memory", "do not retain"]:
        if required not in long_run_text:
            errors.append(f"long-run-model missing required guidance: {required}")

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
    print("- self-evolution: global advisory, project-local enforcement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
