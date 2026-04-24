from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


EVOLUTION_EXAMPLES = [
    "generated-adapter-drift-rule.json",
    "no-env-commit-rule.json",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _load_rule_by_id(root: Path, rule_id: str) -> dict[str, Any]:
    for example_name in EVOLUTION_EXAMPLES:
        rule = _load_json(root / "examples" / "evolution" / example_name)
        if rule.get("id") == rule_id:
            return rule
    known = ", ".join(_load_json(root / "examples" / "evolution" / name).get("id", name) for name in EVOLUTION_EXAMPLES)
    raise ValueError(f"unknown evolution rule {rule_id!r}; known rules: {known}")


def _safety_checks(rule: dict[str, Any]) -> dict[str, bool]:
    enforcement = rule.get("enforcement", {})
    serialized = json.dumps(rule)
    evidence = rule.get("hard_gate_evidence", {})
    return {
        "scope_project": rule.get("scope") == "project",
        "adopted_hard": rule.get("lifecycle") == "adopted_hard",
        "hard_exit_2": enforcement.get("mode") == "hard_exit_2",
        "deterministic": enforcement.get("deterministic") is True,
        "global_export_disabled": rule.get("global_export", {}).get("allowed") is False,
        "hard_gate_evidence_present": bool(evidence) and all(evidence.values()),
        "raw_evidence_absent": "raw_prompt" not in serialized and "raw_frustration" not in serialized,
    }


def dry_run_rule(root: Path, rule_id: str) -> dict[str, Any]:
    """Describe a project-local rule without executing its command."""

    root = root.resolve()
    rule = _load_rule_by_id(root, rule_id)
    check = rule.get("check", {})
    enforcement = rule.get("enforcement", {})
    safety_checks = _safety_checks(rule)
    return {
        "rule_id": rule.get("id"),
        "title": rule.get("title"),
        "scope": rule.get("scope"),
        "lifecycle": rule.get("lifecycle"),
        "check_kind": check.get("kind"),
        "command": check.get("command"),
        "expected_exit_code": check.get("expected_exit_code"),
        "mode": enforcement.get("mode"),
        "message": enforcement.get("message"),
        "would_execute": False,
        "safe_to_execute_later": all(safety_checks.values()),
        "safety_checks": safety_checks,
    }


def execute_rule(root: Path, rule_id: str) -> dict[str, Any]:
    """Execute a safety-validated project-local rule command.

    Commands come from versioned project-local evolution examples, not user input.
    The CLI still requires an explicit acknowledgement flag before calling this.
    """

    root = root.resolve()
    dry_run = dry_run_rule(root, rule_id)
    if not dry_run["safe_to_execute_later"]:
        return {
            **dry_run,
            "executed": False,
            "passed": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "rule failed safety checks; command not executed",
        }

    completed = subprocess.run(
        dry_run["command"],
        cwd=root,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )
    expected_exit_code = dry_run["expected_exit_code"]
    return {
        **dry_run,
        "would_execute": True,
        "executed": True,
        "exit_code": completed.returncode,
        "expected_exit_code": expected_exit_code,
        "passed": completed.returncode == expected_exit_code,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def inspect_evolution_policy(root: Path) -> dict[str, Any]:
    """Return a read-only summary of the canonical evolution policy.

    This deliberately does not execute rule commands. The first runtime surface is
    inspection, not enforcement. Self-evolution that starts by running arbitrary
    project commands is how tools become tiny haunted houses.
    """

    root = root.resolve()
    policy = _load_yaml(root / "policy" / "canonical" / "evolution.yaml")
    global_scope = policy["scopes"]["global"]
    project_scope = policy["scopes"]["project"]

    examples = []
    examples_valid = True
    for example_name in EVOLUTION_EXAMPLES:
        rule = _load_json(root / "examples" / "evolution" / example_name)
        summary = _example_summary(rule)
        examples.append(summary)
        if not (
            summary["scope"] == "project"
            and summary["lifecycle"] == "adopted_hard"
            and summary["mode"] == "hard_exit_2"
            and summary["deterministic"] is True
            and summary["global_export_allowed"] is False
        ):
            examples_valid = False

    return {
        "policy_version": policy.get("version"),
        "global": {
            "artifact_root": global_scope.get("artifact_root"),
            "activation": global_scope.get("activation"),
            "permissions": global_scope.get("permissions", []),
            "forbidden": global_scope.get("forbidden", []),
            "advises": [
                permission.removeprefix("advise_")
                for permission in global_scope.get("permissions", [])
                if permission.startswith("advise_")
            ],
            "can_block": False,
        },
        "project": {
            "artifact_root": project_scope.get("artifact_root"),
            "permissions": project_scope.get("permissions", []),
            "hard_gate_requires": project_scope.get("hard_gate_requires", []),
            "can_enforce_hard": "enforce_adopted_hard_rules" in project_scope.get("permissions", []),
        },
        "retrieval_contract": policy.get("retrieval_contract", {}),
        "rule_lifecycle": policy.get("rule_lifecycle", []),
        "signal_sources": policy.get("signal_sources", []),
        "project_hard_examples": examples,
        "examples_valid": examples_valid,
        "runtime_enforcement": "not_enabled",
    }
