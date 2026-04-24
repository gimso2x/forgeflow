from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


EVOLUTION_EXAMPLES = [
    "generated-adapter-drift-rule.json",
    "no-env-commit-rule.json",
]
PROJECT_RULE_DIR = Path(".forgeflow") / "evolution" / "rules"
RETIRED_RULE_DIR = Path(".forgeflow") / "evolution" / "retired-rules"
PROPOSAL_DIR = Path(".forgeflow") / "evolution" / "proposals"
AUDIT_LOG_PATH = Path(".forgeflow") / "evolution" / "audit-log.jsonl"
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


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _append_audit_event(root: Path, event: dict[str, Any]) -> None:
    audit_path = root / AUDIT_LOG_PATH
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "timestamp": _utc_timestamp(), **event}
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _read_audit_events(root: Path) -> list[dict[str, Any]]:
    audit_path = root / AUDIT_LOG_PATH
    if not audit_path.is_file():
        return []
    lines = [line for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def audit_events(root: Path, *, limit: int = 20) -> dict[str, Any]:
    root = root.resolve()
    audit_path = root / AUDIT_LOG_PATH
    if limit < 1:
        raise ValueError("audit limit must be >= 1")
    events = _read_audit_events(root)[-limit:]
    return {"audit_log": str(audit_path), "events": events}


def effectiveness_review(root: Path, rule_id: str, *, since_days: int = 30) -> dict[str, Any]:
    """Read-only audit-backed effectiveness review for one rule.

    This intentionally recommends but never promotes, edits, retires, restores, or
    executes anything. Promotion without a separate policy gate is governance fan
    fiction wearing a hard hat.
    """

    root = root.resolve()
    if since_days < 1:
        raise ValueError("since_days must be >= 1")
    cutoff = datetime.now(UTC).timestamp() - since_days * 86400
    matching_events = []
    for event in _read_audit_events(root):
        if event.get("rule_id") != rule_id or event.get("event") != "execute":
            continue
        timestamp = event.get("timestamp")
        if isinstance(timestamp, str):
            try:
                event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
            except ValueError:
                event_time = cutoff
            if event_time < cutoff:
                continue
        matching_events.append(event)
    executions = len(matching_events)
    failures = sum(1 for event in matching_events if event.get("passed") is False)
    blocked = sum(1 for event in matching_events if event.get("executed") is False)
    passes = sum(1 for event in matching_events if event.get("passed") is True)
    if failures >= 2:
        recommendation = "promotion_candidate"
    elif failures == 1:
        recommendation = "watch_candidate"
    elif executions > 0:
        recommendation = "effective_candidate"
    else:
        recommendation = "insufficient_data"
    return {
        "rule_id": rule_id,
        "read_only": True,
        "window_days": since_days,
        "metrics": {
            "executions": executions,
            "passes": passes,
            "failures": failures,
            "blocked_executions": blocked,
        },
        "recommendation": recommendation,
        "would_promote": False,
        "would_mutate": False,
        "audit_backed_only": True,
    }


def promotion_plan(root: Path, rule_id: str, *, since_days: int = 30) -> dict[str, Any]:
    """Build a non-mutating promotion plan from audit-backed effectiveness evidence."""

    effectiveness = effectiveness_review(root, rule_id, since_days=since_days)
    metrics = effectiveness["metrics"]
    recommendation = effectiveness["recommendation"]
    risk_flags: list[str] = []
    required_approvals: list[str] = []
    suggested_next_command: str | None = None
    if recommendation == "promotion_candidate":
        required_approvals = ["maintainer_approval", "project_owner_approval"]
        risk_flags.append("promotion_requires_separate_policy_gate")
        suggested_next_command = f"python3 scripts/forgeflow_evolution.py effectiveness --rule {rule_id} --since-days {since_days} --json"
    elif recommendation == "watch_candidate":
        risk_flags.append("single_failure_needs_observation")
    elif recommendation == "insufficient_data":
        risk_flags.append("insufficient_effectiveness_evidence")
    return {
        "rule_id": rule_id,
        "read_only": True,
        "would_mutate": False,
        "would_promote": False,
        "recommendation": recommendation,
        "required_human_approvals": required_approvals,
        "evidence_summary": {
            "window_days": effectiveness["window_days"],
            "executions": metrics["executions"],
            "passes": metrics["passes"],
            "failures": metrics["failures"],
            "blocked_executions": metrics["blocked_executions"],
        },
        "risk_flags": risk_flags,
        "suggested_next_command": suggested_next_command,
    }


def write_promotion_plan(root: Path, rule_id: str, *, since_days: int = 30) -> dict[str, Any]:
    """Persist a promotion proposal without changing rules or audit logs."""

    root = root.resolve()
    plan = promotion_plan(root, rule_id, since_days=since_days)
    proposals_dir = root / PROPOSAL_DIR
    proposals_dir.mkdir(parents=True, exist_ok=True)
    safe_rule_id = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in rule_id).strip("-") or "rule"
    timestamp = _utc_timestamp().replace(":", "").replace("-", "")
    proposal_path = proposals_dir / f"{timestamp}-{safe_rule_id}-promotion-plan.json"
    payload = {
        **plan,
        "proposal_written": True,
        "proposal_path": str(proposal_path),
    }
    proposal_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _failed_safety_checks(safety_checks: dict[str, bool]) -> list[str]:
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


def _rule_summary(rule: dict[str, Any], *, source: str, path: Path) -> dict[str, Any]:
    summary = _example_summary(rule)
    summary["source"] = source
    summary["path"] = str(path)
    return summary


def _evolution_example_paths(root: Path) -> list[Path]:
    example_dir = root / "examples" / "evolution"
    if not example_dir.is_dir():
        return []
    return sorted(example_dir.glob("*.json"))


def _load_example_rules(root: Path) -> list[tuple[dict[str, Any], Path]]:
    return [(_load_json(path), path) for path in _evolution_example_paths(root)]


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


def _load_retired_rule_by_id(root: Path, rule_id: str) -> tuple[dict[str, Any], Path]:
    retired_dir = root / RETIRED_RULE_DIR
    if retired_dir.is_dir():
        for path in sorted(retired_dir.glob("*.json")):
            rule = _load_json(path)
            if rule.get("id") == rule_id:
                return rule, path
    known = []
    if retired_dir.is_dir():
        known = [(_load_json(path).get("id") or path.name) for path in sorted(retired_dir.glob("*.json"))]
    known_text = ", ".join(known) or "<none>"
    raise ValueError(f"evolution rule {rule_id!r} not found in retired registry {retired_dir}; known retired rules: {known_text}")


def _move_with_audit_rollback(source_path: Path, destination: Path, audit_callback) -> None:
    source_path.replace(destination)
    try:
        audit_callback()
    except Exception:
        if destination.exists() and not source_path.exists():
            destination.replace(source_path)
        raise


def retire_rule(root: Path, rule_id: str, *, reason: str) -> dict[str, Any]:
    root = root.resolve()
    if not reason.strip():
        raise ValueError("retire reason must be non-empty")
    rule, source, source_path = _load_rule_by_id(root, rule_id, allow_examples=False)
    destination_dir = root / RETIRED_RULE_DIR
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source_path.name
    if destination.exists():
        raise FileExistsError(f"retired evolution rule already exists: {destination}")
    result = {
        "retired": True,
        "rule_id": rule.get("id"),
        "source": source,
        "source_path": str(source_path),
        "destination": str(destination),
        "reason": reason,
    }

    def audit() -> None:
        _append_audit_event(
            root,
            {
                "event": "retire",
                "rule_id": result["rule_id"],
                "source": source,
                "source_path": result["source_path"],
                "destination": result["destination"],
                "reason": reason,
                "passed": True,
            },
        )

    _move_with_audit_rollback(source_path, destination, audit)
    return result


def restore_rule(root: Path, rule_id: str, *, reason: str) -> dict[str, Any]:
    root = root.resolve()
    if not reason.strip():
        raise ValueError("restore reason must be non-empty")
    rule, source_path = _load_retired_rule_by_id(root, rule_id)
    destination_dir = root / PROJECT_RULE_DIR
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source_path.name
    if destination.exists():
        raise FileExistsError(f"project-local evolution rule already exists: {destination}")
    safety_checks = _safety_checks(rule)
    if not all(safety_checks.values()):
        failed = ", ".join(name for name, passed in safety_checks.items() if not passed)
        raise ValueError(f"retired rule {rule_id!r} failed safety checks: {failed}")
    result = {
        "restored": True,
        "rule_id": rule.get("id"),
        "source_path": str(source_path),
        "destination": str(destination),
        "reason": reason,
        "safety_checks": safety_checks,
    }

    def audit() -> None:
        _append_audit_event(
            root,
            {
                "event": "restore",
                "rule_id": result["rule_id"],
                "source_path": result["source_path"],
                "destination": result["destination"],
                "reason": reason,
                "passed": True,
                "safety_checks": safety_checks,
            },
        )

    _move_with_audit_rollback(source_path, destination, audit)
    return result


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
    result = {
        "adopted": True,
        "rule_id": rule.get("id"),
        "source": str(source_path),
        "destination": str(destination),
        "safety_checks": safety_checks,
    }
    _append_audit_event(
        root,
        {
            "event": "adopt",
            "rule_id": result["rule_id"],
            "source": result["source"],
            "destination": result["destination"],
            "passed": True,
            "safety_checks": safety_checks,
        },
    )
    return result


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
        result = {
            **dry_run,
            "executed": False,
            "passed": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "rule failed safety checks; command not executed",
        }
        _append_audit_event(
            root,
            {
                "event": "execute",
                "rule_id": dry_run["rule_id"],
                "source": dry_run["source"],
                "path": dry_run["path"],
                "executed": False,
                "passed": False,
                "exit_code": None,
                "expected_exit_code": dry_run["expected_exit_code"],
                "failed_safety_checks": _failed_safety_checks(dry_run["safety_checks"]),
            },
        )
        return result

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
    result = {
        **dry_run,
        "would_execute": True,
        "executed": True,
        "exit_code": completed.returncode,
        "expected_exit_code": expected_exit_code,
        "passed": completed.returncode == expected_exit_code,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    _append_audit_event(
        root,
        {
            "event": "execute",
            "rule_id": dry_run["rule_id"],
            "source": dry_run["source"],
            "path": dry_run["path"],
            "executed": True,
            "passed": result["passed"],
            "exit_code": result["exit_code"],
            "expected_exit_code": expected_exit_code,
            "failed_safety_checks": [],
        },
    )
    return result


def _load_retired_rules(root: Path) -> list[tuple[dict[str, Any], Path]]:
    retired_dir = root / RETIRED_RULE_DIR
    if not retired_dir.is_dir():
        return []
    return [(_load_json(path), path) for path in sorted(retired_dir.glob("*.json"))]


def _audit_required_field_issues(event: dict[str, Any], *, line_number: int) -> list[dict[str, Any]]:
    required = {"schema_version", "timestamp", "event", "rule_id", "passed"}
    missing = sorted(name for name in required if name not in event)
    if not missing:
        return []
    return [
        {
            "severity": "error",
            "code": "audit_event_missing_fields",
            "line": line_number,
            "missing_fields": missing,
        }
    ]


def doctor_evolution_state(root: Path) -> dict[str, Any]:
    """Read-only health check for the project-local evolution lifecycle.

    Inspired by the closed-loop model: reactive fix learning, proactive feedback
    learning, and meta effectiveness review are useful only when the local rule
    registry and audit trail are parseable, safety-checked, and project-scoped.
    """

    root = root.resolve()
    issues: list[dict[str, Any]] = []
    active_rules: list[dict[str, Any]] = []
    retired_rules: list[dict[str, Any]] = []

    active_ids: set[str] = set()
    retired_ids: set[str] = set()

    for loader, bucket, ids, source, issue_code in [
        (_load_project_rules, active_rules, active_ids, "active", "unsafe_active_rule"),
        (_load_retired_rules, retired_rules, retired_ids, "retired", "unsafe_retired_rule"),
    ]:
        try:
            loaded = loader(root)
        except json.JSONDecodeError as exc:
            issues.append(
                {
                    "severity": "error",
                    "code": f"invalid_{source}_rule_json",
                    "message": str(exc),
                }
            )
            loaded = []
        for rule, path in loaded:
            rule_id = rule.get("id") or path.stem
            safety_checks = _safety_checks(rule)
            failed = _failed_safety_checks(safety_checks)
            ids.add(str(rule_id))
            bucket.append(
                {
                    "id": rule_id,
                    "path": str(path),
                    "safe_to_execute": not failed,
                    "safety_checks": safety_checks,
                    "failed_safety_checks": failed,
                }
            )
            if failed:
                issues.append(
                    {
                        "severity": "error" if source == "active" else "warning",
                        "code": issue_code,
                        "rule_id": rule_id,
                        "path": str(path),
                        "failed_safety_checks": failed,
                    }
                )

    for duplicate in sorted(active_ids & retired_ids):
        issues.append(
            {
                "severity": "error",
                "code": "duplicate_active_retired_rule",
                "rule_id": duplicate,
            }
        )

    audit_path = root / AUDIT_LOG_PATH
    audit_events_count = 0
    last_event: dict[str, Any] | None = None
    if audit_path.is_file():
        for line_number, line in enumerate(audit_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                issues.append(
                    {
                        "severity": "error",
                        "code": "invalid_audit_json",
                        "line": line_number,
                        "message": str(exc),
                    }
                )
                continue
            audit_events_count += 1
            last_event = event
            issues.extend(_audit_required_field_issues(event, line_number=line_number))

    return {
        "ok": not any(issue.get("severity") == "error" for issue in issues),
        "root": str(root),
        "summary": {
            "active_rules": len(active_rules),
            "retired_rules": len(retired_rules),
            "audit_events": audit_events_count,
            "last_event": last_event,
            "unsafe_active_rules": sum(1 for rule in active_rules if not rule["safe_to_execute"]),
            "unsafe_retired_rules": sum(1 for rule in retired_rules if not rule["safe_to_execute"]),
            "restore_candidates": len(retired_rules),
        },
        "active_rules": active_rules,
        "retired_rules": retired_rules,
        "audit_log": str(audit_path),
        "closed_loop_surfaces": {
            "reactive_fix_learning": "advisory_metadata_only",
            "proactive_feedback_learning": "raw_text_disabled",
            "meta_effectiveness_review": "audit_backed_only",
        },
        "issues": issues,
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
    for rule, path in _load_example_rules(root):
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
