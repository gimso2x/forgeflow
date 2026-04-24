from __future__ import annotations

import json
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
