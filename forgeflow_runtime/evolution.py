from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


EVOLUTION_EXAMPLES = [
    "generated-adapter-drift-rule.json",
    "no-env-commit-rule.json",
]
PROJECT_RULE_DIR = Path(".forgeflow") / "evolution" / "rules"
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
APPROVED_COMMAND_IDS = {"generated-adapter-drift", "no-env-commit"}
COMMAND_TIMEOUT_SECONDS = 30


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


def _rule_summary(rule: dict[str, Any], *, source: str, path: Path) -> dict[str, Any]:
    summary = _example_summary(rule)
    summary["source"] = source
    summary["path"] = str(path)
    return summary


def _load_example_rules(root: Path) -> list[tuple[dict[str, Any], Path]]:
    rules: list[tuple[dict[str, Any], Path]] = []
    for example_name in EVOLUTION_EXAMPLES:
        path = root / "examples" / "evolution" / example_name
        rules.append((_load_json(path), path))
    return rules


def _load_project_rules(root: Path) -> list[tuple[dict[str, Any], Path]]:
    rules_dir = root / PROJECT_RULE_DIR
    if not rules_dir.is_dir():
        return []
    return [(_load_json(path), path) for path in sorted(rules_dir.glob("*.json"))]


def list_rules(root: Path, *, include_examples: bool = False, fallback_root: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    examples_root = (fallback_root or root).resolve()
    project_rules = [_rule_summary(rule, source="project", path=path) for rule, path in _load_project_rules(root)]
    example_rules = (
        [_rule_summary(rule, source="example", path=path) for rule, path in _load_example_rules(examples_root)]
        if include_examples
        else []
    )
    return {
        "project_rule_dir": str(root / PROJECT_RULE_DIR),
        "project_rules": project_rules,
        "example_rules": example_rules,
    }


def _load_example_rule_by_id(root: Path, rule_id: str) -> tuple[dict[str, Any], Path]:
    for rule, path in _load_example_rules(root):
        if rule.get("id") == rule_id:
            return rule, path
    known = ", ".join(rule.get("id", path.name) for rule, path in _load_example_rules(root))
    raise ValueError(f"unknown evolution example {rule_id!r}; known examples: {known}")


def _load_rule_by_id(root: Path, rule_id: str, *, allow_examples: bool, fallback_root: Path | None = None) -> tuple[dict[str, Any], str, Path]:
    for rule, path in _load_project_rules(root):
        if rule.get("id") == rule_id:
            return rule, "project", path
    if allow_examples:
        examples_root = (fallback_root or root).resolve()
        for rule, path in _load_example_rules(examples_root):
            if rule.get("id") == rule_id:
                return rule, "example", path
    known_project = [rule.get("id", path.name) for rule, path in _load_project_rules(root)]
    if allow_examples:
        examples_root = (fallback_root or root).resolve()
        known_examples = [rule.get("id", path.name) for rule, path in _load_example_rules(examples_root)]
        known = ", ".join(known_project + known_examples)
        raise ValueError(f"unknown evolution rule {rule_id!r}; known rules: {known}")
    known = ", ".join(known_project) or "<none>"
    raise ValueError(f"evolution rule {rule_id!r} not found in project-local registry {root / PROJECT_RULE_DIR}; known project rules: {known}")


def _safety_checks(rule: dict[str, Any]) -> dict[str, bool]:
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
    }


def dry_run_rule(root: Path, rule_id: str, *, allow_examples: bool = True, fallback_root: Path | None = None) -> dict[str, Any]:
    """Describe a rule without executing its command."""

    root = root.resolve()
    rule, source, path = _load_rule_by_id(root, rule_id, allow_examples=allow_examples, fallback_root=fallback_root)
    check = rule.get("check", {})
    enforcement = rule.get("enforcement", {})
    safety_checks = _safety_checks(rule)
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
        "safe_to_execute_later": all(safety_checks.values()),
        "safety_checks": safety_checks,
    }



def _rule_filename(rule: dict[str, Any], source_path: Path) -> str:
    rule_id = rule.get("id")
    if isinstance(rule_id, str) and rule_id:
        return f"{rule_id}-rule.json"
    return source_path.name


def adopt_example_rule(root: Path, rule_id: str, *, fallback_root: Path | None = None) -> dict[str, Any]:
    """Copy a safe example rule into the project-local registry without overwriting."""

    root = root.resolve()
    examples_root = (fallback_root or root).resolve()
    rule, source_path = _load_example_rule_by_id(examples_root, rule_id)
    source = "example"
    if source != "example":
        raise ValueError(f"rule {rule_id!r} is already project-local; adopt expects an example rule")
    safety_checks = _safety_checks(rule)
    if not all(safety_checks.values()):
        failed = ", ".join(name for name, passed in safety_checks.items() if not passed)
        raise ValueError(f"example rule {rule_id!r} failed safety checks: {failed}")

    destination_dir = root / PROJECT_RULE_DIR
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / _rule_filename(rule, source_path)
    if destination.exists():
        raise FileExistsError(f"project-local evolution rule already exists: {destination}")
    destination.write_text(json.dumps(rule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "adopted": True,
        "rule_id": rule.get("id"),
        "source": str(source_path),
        "destination": str(destination),
        "safety_checks": safety_checks,
    }


def _run_approved_command(command_id: str, root: Path) -> subprocess.CompletedProcess[str]:
    if command_id == "no-env-commit":
        git_check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        if git_check.returncode != 0:
            return git_check
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        if staged.returncode != 0:
            return staged
        bad = [
            path
            for path in staged.stdout.splitlines()
            if path in {".env", ".env.local"} or path.endswith("/.env") or path.endswith("/.env.local")
        ]
        return subprocess.CompletedProcess(
            args=["forgeflow-approved-command", command_id],
            returncode=1 if bad else 0,
            stdout="\n".join(bad) + ("\n" if bad else ""),
            stderr="",
        )
    if command_id == "generated-adapter-drift":
        generate = subprocess.run(
            [sys.executable, "scripts/generate_adapters.py"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        if generate.returncode != 0:
            return generate
        diff = subprocess.run(
            ["git", "diff", "--exit-code", "adapters/generated"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        return subprocess.CompletedProcess(
            args=["forgeflow-approved-command", command_id],
            returncode=diff.returncode,
            stdout=generate.stdout + diff.stdout,
            stderr=generate.stderr + diff.stderr,
        )
    raise ValueError(f"unapproved evolution command id: {command_id}")


def execute_rule(root: Path, rule_id: str) -> dict[str, Any]:
    """Execute a safety-validated project-local rule command.

    Commands come from versioned project-local evolution examples, not user input.
    The CLI still requires an explicit acknowledgement flag before calling this.
    """

    root = root.resolve()
    dry_run = dry_run_rule(root, rule_id, allow_examples=False)
    if not dry_run["safe_to_execute_later"]:
        return {
            **dry_run,
            "executed": False,
            "passed": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "rule failed safety checks; command not executed",
        }

    try:
        completed = _run_approved_command(str(dry_run["command_id"]), root)
    except subprocess.TimeoutExpired as exc:
        return {
            **dry_run,
            "would_execute": True,
            "executed": True,
            "passed": False,
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": f"evolution rule timed out after {COMMAND_TIMEOUT_SECONDS}s",
        }
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
        if not all(_safety_checks(rule).values()):
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
