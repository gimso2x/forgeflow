from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

AUDIT_LOG_PATH = Path(".forgeflow") / "evolution" / "audit-log.jsonl"
PROPOSAL_DIR = Path(".forgeflow") / "evolution" / "proposals"


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def append_audit_event(root: Path, event: dict[str, Any]) -> None:
    audit_path = root / AUDIT_LOG_PATH
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "timestamp": utc_timestamp(), **event}
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def read_audit_events(root: Path) -> list[dict[str, Any]]:
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
    timestamp = utc_timestamp().replace(":", "").replace("-", "")
    proposal_path = proposals_dir / f"{timestamp}-{safe_rule_id}-promotion-plan.json"
    payload = {
        **plan,
        "proposal_written": True,
        "proposal_path": str(proposal_path),
    }
    proposal_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


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
    return [c for c in cases if c.trigger == trigger]


def find_cases_by_tag(cases: list[EvolutionCase], tag: str) -> list[EvolutionCase]:
    """Return cases that carry *tag* in their tags list."""
    return [c for c in cases if tag in c.tags]


def summarize_impact(cases: list[EvolutionCase]) -> dict[str, Any]:
    """Aggregate statistics across a list of evolution cases."""
    by_trigger: dict[str, int] = {}
    by_impact: dict[str, int] = {}
    for c in cases:
        by_trigger[c.trigger] = by_trigger.get(c.trigger, 0) + 1
        by_impact[c.impact] = by_impact.get(c.impact, 0) + 1
    return {
        "total": len(cases),
        "by_trigger": by_trigger,
        "by_impact": by_impact,
    }


_IMPACT_BADGE: dict[str, str] = {"low": "🟢", "medium": "🟡", "high": "🔴"}


def format_evolution_report(cases: list[EvolutionCase]) -> str:
    """Human-readable evolution report."""
    lines: list[str] = []
    lines.append(f"=== Evolution Report ({len(cases)} cases) ===")
    lines.append("")
    for c in cases:
        badge = _IMPACT_BADGE.get(c.impact, "⚪")
        lines.append(f"[{c.id}] {c.title}")
        lines.append(f"  Trigger: {c.trigger}  Impact: {badge} {c.impact}")
        lines.append(f"  Before: {c.before_state}")
        lines.append(f"  After:  {c.after_state}")
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
    for c in cases:
        badge = _IMPACT_BADGE.get(c.impact, "⚪")
        lines.append(f"| {c.id} | {c.trigger} | {badge} | {c.description} |")
    return "\n".join(lines)
