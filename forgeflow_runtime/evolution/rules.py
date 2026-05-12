from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_RULE_DIR = Path(".forgeflow") / "evolution" / "rules"
RETIRED_RULE_DIR = Path(".forgeflow") / "evolution" / "retired-rules"
HARD_GATE_REQUIRES = {
    "project_local_enablement",
    "soft_soak_period",
    "independent_recurrence_or_audited_maintainer_enablement",
    "deterministic_check",
    "low_false_positive_rate",
    "rollback_available",
    "eval_record",
    "audit_trail",
}
APPROVED_COMMANDS = {
    "generated-adapter-drift": "python scripts/generate_adapters.py --check",
    "no-env-commit": "python scripts/forgeflow_evolution.py execute --rule no-env-commit --i-understand-project-local-hard-rule",
}
APPROVED_COMMAND_IDS = set(APPROVED_COMMANDS)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def failed_safety_checks(safety_checks: dict[str, bool]) -> list[str]:
    return [name for name, passed in safety_checks.items() if not passed]


def _example_summary(rule: dict[str, Any]) -> dict[str, Any]:
    enforcement = rule.get("enforcement", {})
    return {
        "id": rule.get("id"),
        "title": rule.get("title"),
        "scope": rule.get("scope"),
        "lifecycle": rule.get("lifecycle"),
        "mode": enforcement.get("mode"),
        "deterministic": enforcement.get("deterministic") is True,
        "global_export_allowed": rule.get("global_export", {}).get("allowed") is True,
    }


def rule_summary(rule: dict[str, Any], *, source: str, path: Path) -> dict[str, Any]:
    summary = _example_summary(rule)
    summary["source"] = source
    summary["path"] = str(path)
    return summary


def evolution_example_paths(root: Path) -> list[Path]:
    example_dir = root / "examples" / "evolution"
    if not example_dir.is_dir():
        return []
    return sorted(example_dir.glob("*.json"))


def load_example_rules(root: Path) -> list[tuple[dict[str, Any], Path]]:
    return [(_load_json(path), path) for path in evolution_example_paths(root)]


def load_project_rules(root: Path) -> list[tuple[dict[str, Any], Path]]:
    rules_dir = root / PROJECT_RULE_DIR
    if not rules_dir.is_dir():
        return []
    return [(_load_json(path), path) for path in sorted(rules_dir.glob("*.json"))]


def list_rules(root: Path, *, include_examples: bool = False, fallback_root: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    examples_root = (fallback_root or root).resolve()
    project_rules = [rule_summary(rule, source="project", path=path) for rule, path in load_project_rules(root)]
    example_rules = (
        [rule_summary(rule, source="example", path=path) for rule, path in load_example_rules(examples_root)]
        if include_examples
        else []
    )
    return {
        "project_rule_dir": str(root / PROJECT_RULE_DIR),
        "project_rules": project_rules,
        "example_rules": example_rules,
    }


def load_example_rule_by_id(root: Path, rule_id: str) -> tuple[dict[str, Any], Path]:
    for rule, path in load_example_rules(root):
        if rule.get("id") == rule_id:
            return rule, path
    known = ", ".join(rule.get("id", path.name) for rule, path in load_example_rules(root))
    raise ValueError(f"unknown evolution example {rule_id!r}; known examples: {known}")


def load_rule_by_id(root: Path, rule_id: str, *, allow_examples: bool, fallback_root: Path | None = None) -> tuple[dict[str, Any], str, Path]:
    for rule, path in load_project_rules(root):
        if rule.get("id") == rule_id:
            return rule, "project", path
    if allow_examples:
        examples_root = (fallback_root or root).resolve()
        for rule, path in load_example_rules(examples_root):
            if rule.get("id") == rule_id:
                return rule, "example", path
    known_project = [rule.get("id", path.name) for rule, path in load_project_rules(root)]
    if allow_examples:
        examples_root = (fallback_root or root).resolve()
        known_examples = [rule.get("id", path.name) for rule, path in load_example_rules(examples_root)]
        known = ", ".join(known_project + known_examples)
        raise ValueError(f"unknown evolution rule {rule_id!r}; known rules: {known}")
    known = ", ".join(known_project) or "<none>"
    raise ValueError(f"evolution rule {rule_id!r} not found in project-local registry {root / PROJECT_RULE_DIR}; known project rules: {known}")


def safety_checks(rule: dict[str, Any]) -> dict[str, bool]:
    enforcement = rule.get("enforcement", {})
    serialized = json.dumps(rule)
    evidence = rule.get("hard_gate_evidence", {})
    check = rule.get("check", {})
    return {
        "scope_project": rule.get("scope") == "project",
        "adopted_hard": rule.get("lifecycle") == "adopted_hard",
        "hard_exit_2": enforcement.get("mode") == "hard_exit_2",
        "deterministic": enforcement.get("deterministic") is True,
        "global_export_disabled": rule.get("global_export", {}).get("allowed") is False,
        "hard_gate_evidence_complete": set(evidence) == HARD_GATE_REQUIRES and all(isinstance(value, str) and value.strip() for value in evidence.values()),
        "raw_evidence_absent": "raw_prompt" not in serialized and "raw_frustration" not in serialized,
        "check_shape": check.get("kind") == "command"
        and isinstance(check.get("command_id"), str)
        and isinstance(check.get("command"), str)
        and isinstance(check.get("expected_exit_code"), int),
        "approved_command": check.get("command_id") in APPROVED_COMMAND_IDS,
        "approved_command_contract": check.get("command") == APPROVED_COMMANDS.get(check.get("command_id")),
    }


def dry_run_rule(root: Path, rule_id: str, *, allow_examples: bool = True, fallback_root: Path | None = None) -> dict[str, Any]:
    """Describe a rule without executing its command."""

    root = root.resolve()
    rule, source, path = load_rule_by_id(root, rule_id, allow_examples=allow_examples, fallback_root=fallback_root)
    check = rule.get("check", {})
    enforcement = rule.get("enforcement", {})
    checks = safety_checks(rule)
    return {
        "rule_id": rule.get("id"),
        "source": source,
        "path": str(path),
        "title": rule.get("title"),
        "scope": rule.get("scope"),
        "lifecycle": rule.get("lifecycle"),
        "check_kind": check.get("kind"),
        "command_id": check.get("command_id"),
        "command": check.get("command"),
        "expected_exit_code": check.get("expected_exit_code"),
        "mode": enforcement.get("mode"),
        "message": enforcement.get("message"),
        "would_execute": False,
        "safe_to_execute_later": all(checks.values()),
        "safety_checks": checks,
    }
