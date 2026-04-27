from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from forgeflow_runtime.evolution_audit import AUDIT_LOG_PATH
from forgeflow_runtime.evolution_rules import failed_safety_checks, safety_checks

RuleLoader = Callable[[Path], list[tuple[dict[str, Any], Path]]]


@dataclass(frozen=True)
class RuleHealth:
    rules: list[dict[str, Any]]
    rule_ids: set[str]
    issues: list[dict[str, Any]]


@dataclass(frozen=True)
class AuditLogHealth:
    events_count: int
    last_event: dict[str, Any] | None
    issues: list[dict[str, Any]]


def audit_required_field_issues(event: dict[str, Any], *, line_number: int) -> list[dict[str, Any]]:
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


def _collect_rule_health(root: Path, *, loader: RuleLoader, source: str, issue_code: str) -> RuleHealth:
    rules: list[dict[str, Any]] = []
    rule_ids: set[str] = set()
    issues: list[dict[str, Any]] = []

    try:
        loaded = loader(root)
    except json.JSONDecodeError as exc:
        return RuleHealth(
            rules=[],
            rule_ids=set(),
            issues=[
                {
                    "severity": "error",
                    "code": f"invalid_{source}_rule_json",
                    "message": str(exc),
                }
            ],
        )

    for rule, path in loaded:
        rule_id = rule.get("id") or path.stem
        rule_safety_checks = safety_checks(rule)
        failed = failed_safety_checks(rule_safety_checks)
        rule_ids.add(str(rule_id))
        rules.append(
            {
                "id": rule_id,
                "path": str(path),
                "safe_to_execute": not failed,
                "safety_checks": rule_safety_checks,
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

    return RuleHealth(rules=rules, rule_ids=rule_ids, issues=issues)


def _audit_log_health(audit_path: Path) -> AuditLogHealth:
    issues: list[dict[str, Any]] = []
    events_count = 0
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
            events_count += 1
            last_event = event
            issues.extend(audit_required_field_issues(event, line_number=line_number))

    return AuditLogHealth(events_count=events_count, last_event=last_event, issues=issues)


def doctor_evolution_state(
    root: Path,
    *,
    project_rule_loader: RuleLoader,
    retired_rule_loader: RuleLoader,
) -> dict[str, Any]:
    """Read-only health check for the project-local evolution lifecycle."""

    root = root.resolve()
    active_health = _collect_rule_health(
        root,
        loader=project_rule_loader,
        source="active",
        issue_code="unsafe_active_rule",
    )
    retired_health = _collect_rule_health(
        root,
        loader=retired_rule_loader,
        source="retired",
        issue_code="unsafe_retired_rule",
    )
    issues = [*active_health.issues, *retired_health.issues]
    active_rules = active_health.rules
    retired_rules = retired_health.rules

    for duplicate in sorted(active_health.rule_ids & retired_health.rule_ids):
        issues.append(
            {
                "severity": "error",
                "code": "duplicate_active_retired_rule",
                "rule_id": duplicate,
            }
        )

    audit_path = root / AUDIT_LOG_PATH
    audit_health = _audit_log_health(audit_path)
    issues.extend(audit_health.issues)

    return {
        "ok": not any(issue.get("severity") == "error" for issue in issues),
        "root": str(root),
        "summary": {
            "active_rules": len(active_rules),
            "retired_rules": len(retired_rules),
            "audit_events": audit_health.events_count,
            "last_event": audit_health.last_event,
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
