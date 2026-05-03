"""Execution Crystallization — distill repeated successful paths into reusable rules.

Tracks execution histories, extracts patterns from successful runs, and
promotes them through soft → hard-candidate → hard rule levels.  Pure
stdlib — no external deps.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class RuleLevel(str, Enum):
    SOFT = "SOFT"
    HARD_CANDIDATE = "HARD_CANDIDATE"
    HARD = "HARD"


@dataclass(frozen=True)
class ExecutionPath:
    steps: list[str]
    signals: list[str]
    result: str  # "success" or "failure"
    duration_seconds: float
    timestamp: str


@dataclass(frozen=True)
class CrystallizedRule:
    id: str
    pattern: list[str]
    level: RuleLevel
    success_count: int
    failure_count: int
    created_at: str
    promoted_at: str | None


# ---------------------------------------------------------------------------
# Pattern extraction
# ---------------------------------------------------------------------------

def extract_pattern(path: ExecutionPath) -> list[str]:
    """Extract key steps as a pattern: first, last, and any verify/test steps."""
    if not path.steps:
        return []
    seen: set[str] = set()
    pattern: list[str] = []
    def _add(step: str) -> None:
        if step not in seen:
            seen.add(step)
            pattern.append(step)
    _add(path.steps[0])
    for step in path.steps[1:-1]:
        if "verify" in step or "test" in step:
            _add(step)
    if len(path.steps) > 1:
        _add(path.steps[-1])
    return pattern


def pattern_key(pattern: list[str]) -> str:
    """Deterministic string key from a pattern list."""
    return "→".join(pattern)


# ---------------------------------------------------------------------------
# Execution recording
# ---------------------------------------------------------------------------

def record_execution(
    paths: list[ExecutionPath],
    pattern_counts: dict[str, dict],
) -> dict[str, dict]:
    """Group paths by pattern, counting successes and failures.

    *pattern_counts* maps ``pattern_key`` →
    ``{successes: int, failures: int, last_seen: str}``.
    Returns a **new** dict (does not mutate the input).
    """
    counts: dict[str, dict] = {
        k: dict(v) for k, v in pattern_counts.items()
    }
    for path in paths:
        key = pattern_key(extract_pattern(path))
        entry = counts.get(key)
        if entry is None:
            entry = {"successes": 0, "failures": 0, "last_seen": ""}
            counts[key] = entry
        if path.result == "success":
            entry["successes"] += 1
        else:
            entry["failures"] += 1
        entry["last_seen"] = path.timestamp
    return counts


# ---------------------------------------------------------------------------
# Crystallization decisions
# ---------------------------------------------------------------------------

def should_crystallize(
    counts: dict,
    soft_threshold: int = 3,
    hard_threshold: int = 10,
) -> RuleLevel | None:
    """Decide whether a pattern should become a rule (and at what level)."""
    successes = counts.get("successes", 0)
    if successes >= hard_threshold:
        return RuleLevel.HARD_CANDIDATE
    if successes >= soft_threshold:
        return RuleLevel.SOFT
    return None


def promote_rule(rule: CrystallizedRule, new_level: RuleLevel) -> CrystallizedRule:
    """Return a new rule with updated level and promoted_at timestamp."""
    return replace(
        rule,
        level=new_level,
        promoted_at=__import__("datetime").datetime.now().isoformat(),
    )


# ---------------------------------------------------------------------------
# Rule lookup
# ---------------------------------------------------------------------------

def get_applicable_rules(
    rules: list[CrystallizedRule],
    current_steps: list[str],
) -> list[CrystallizedRule]:
    """Find rules whose pattern is a prefix of *current_steps*."""
    return [
        rule
        for rule in rules
        if len(current_steps) >= len(rule.pattern)
        and all(
            current_steps[i] == rule.pattern[i]
            for i in range(len(rule.pattern))
        )
    ]


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def format_crystallization_report(rules: list[CrystallizedRule]) -> str:
    """Human-readable report grouped by rule level."""
    by_level: dict[RuleLevel, list[CrystallizedRule]] = {
        level: [] for level in RuleLevel
    }
    for rule in rules:
        by_level[rule.level].append(rule)

    lines: list[str] = []
    for level in RuleLevel:
        group = by_level[level]
        if not group:
            continue
        lines.append(f"[{level.value}] ({len(group)} rules)")
        for rule in group:
            total = rule.success_count + rule.failure_count
            rate = (
                f"{rule.success_count / total:.0%}"
                if total > 0
                else "N/A"
            )
            lines.append(
                f"  {rule.id}: {pattern_key(rule.pattern)} "
                f"({rule.success_count}/{total} success, rate={rate})"
            )
    return "\n".join(lines)
