from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from forgeflow_runtime.evolution_audit import AUDIT_LOG_PATH
from forgeflow_runtime.evolution_rules import failed_safety_checks, safety_checks

RuleLoader = Callable[[Path], list[tuple[dict[str, Any], Path]]]


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


def doctor_evolution_state(
    root: Path,
    *,
    project_rule_loader: RuleLoader,
    retired_rule_loader: RuleLoader,
) -> dict[str, Any]:
    """Read-only health check for the project-local evolution lifecycle."""

    root = root.resolve()
    issues: list[dict[str, Any]] = []
    active_rules: list[dict[str, Any]] = []
    retired_rules: list[dict[str, Any]] = []

    active_ids: set[str] = set()
    retired_ids: set[str] = set()

    for loader, bucket, ids, source, issue_code in [
        (project_rule_loader, active_rules, active_ids, "active", "unsafe_active_rule"),
        (retired_rule_loader, retired_rules, retired_ids, "retired", "unsafe_retired_rule"),
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
            rule_safety_checks = safety_checks(rule)
            failed = failed_safety_checks(rule_safety_checks)
            ids.add(str(rule_id))
            bucket.append(
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
            issues.extend(audit_required_field_issues(event, line_number=line_number))

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
