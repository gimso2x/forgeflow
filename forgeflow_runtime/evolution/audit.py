from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from forgeflow_runtime.evolution.paths import global_audit_log_path


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class EvolutionCase:
    """Immutable record of a single evolution event."""

    id: str
    title: str
    trigger: str  # repeated_error | pattern_learning | performance_optimization | convention_adoption
    description: str
    before_state: str
    after_state: str
    impact: str  # low | medium | high
    timestamp: str
    tags: list[str] = field(default_factory=list)


def generate_case_id(trigger: str, timestamp: str) -> str:
    """Deterministic case ID from trigger and timestamp."""

    digest = hashlib.md5((trigger + timestamp).encode()).hexdigest()[:8].upper()
    return f"EVC-{digest}"


def record_evolution_case(case: EvolutionCase, cases: list[EvolutionCase]) -> list[EvolutionCase]:
    """Append *case* to *cases* and return a new list."""

    return [*cases, case]


def find_cases_by_trigger(cases: list[EvolutionCase], trigger: str) -> list[EvolutionCase]:
    """Return cases whose trigger matches *trigger*."""

    return [case for case in cases if case.trigger == trigger]


def find_cases_by_tag(cases: list[EvolutionCase], tag: str) -> list[EvolutionCase]:
    """Return cases that carry *tag* in their tags list."""

    return [case for case in cases if tag in case.tags]


def summarize_impact(cases: list[EvolutionCase]) -> dict[str, Any]:
    """Aggregate statistics across a list of evolution cases."""

    by_trigger: dict[str, int] = {}
    by_impact: dict[str, int] = {}
    for case in cases:
        by_trigger[case.trigger] = by_trigger.get(case.trigger, 0) + 1
        by_impact[case.impact] = by_impact.get(case.impact, 0) + 1
    return {"total": len(cases), "by_trigger": by_trigger, "by_impact": by_impact}


_IMPACT_BADGE: dict[str, str] = {"low": "🟢", "medium": "🟡", "high": "🔴"}


def format_evolution_report(cases: list[EvolutionCase]) -> str:
    """Human-readable evolution report."""

    lines: list[str] = [f"=== Evolution Report ({len(cases)} cases) ===", ""]
    for case in cases:
        badge = _IMPACT_BADGE.get(case.impact, "⚪")
        lines.append(f"[{case.id}] {case.title}")
        lines.append(f"  Trigger: {case.trigger}  Impact: {badge} {case.impact}")
        lines.append(f"  Before: {case.before_state}")
        lines.append(f"  After:  {case.after_state}")
        lines.append("")
    summary = summarize_impact(cases)
    if summary["total"]:
        lines.append("--- Impact Distribution ---")
        for impact, count in sorted(summary["by_impact"].items()):
            badge = _IMPACT_BADGE.get(impact, "⚪")
            lines.append(f"  {badge} {impact}: {count}")
    return "\n".join(lines)


def generate_readme_section(cases: list[EvolutionCase]) -> str:
    """Markdown section suitable for a README."""

    lines = ["## Evolution in Action", ""]
    if not cases:
        lines.append("_No evolution cases recorded yet._")
        return "\n".join(lines)
    lines.append("| ID | Trigger | Impact | Description |")
    lines.append("|----|---------|--------|-------------|")
    for case in cases:
        badge = _IMPACT_BADGE.get(case.impact, "⚪")
        lines.append(f"| {case.id} | {case.trigger} | {badge} | {case.description} |")
    return "\n".join(lines)


def append_audit_event(root: Path, event: dict[str, Any]) -> None:
    audit_path = global_audit_log_path()
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "timestamp": utc_timestamp(), **event}
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def read_audit_events(root: Path) -> list[dict[str, Any]]:
    audit_path = global_audit_log_path()
    if not audit_path.is_file():
        return []
    lines = [line for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def audit_events(root: Path, *, limit: int = 20) -> dict[str, Any]:
    root = root.resolve()
    audit_path = global_audit_log_path()
    if limit < 1:
        raise ValueError("audit limit must be >= 1")
    events = read_audit_events(root)[-limit:]
    return {"audit_log": str(audit_path), "events": events}


def effectiveness_review(root: Path, rule_id: str, *, since_days: int = 30) -> dict[str, Any]:
    """Read-only audit-backed effectiveness review for one evolution rule."""

    root = root.resolve()
    if since_days < 1:
        raise ValueError("since_days must be >= 1")
    cutoff = datetime.now(UTC).timestamp() - since_days * 86400
    matching_events = []
    for event in read_audit_events(root):
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
