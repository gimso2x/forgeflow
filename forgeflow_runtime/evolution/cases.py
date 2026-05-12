from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


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
