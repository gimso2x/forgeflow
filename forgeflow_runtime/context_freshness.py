"""Context freshness tracking for task context windows.

Manages context window lifecycle: creation, staleness detection,
refresh, prioritisation, and trimming to token budgets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContextWindow:
    """A bounded slice of context associated with a task."""

    task_id: str
    start_marker: str
    end_marker: str
    max_tokens: int
    priority: str  # "high" | "normal" | "low"


@dataclass(frozen=True)
class ContextState:
    """Snapshot of all active context windows and metadata."""

    windows: list[ContextWindow]
    total_tokens: int
    last_refreshed: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PRIORITY_ORDER: dict[str, int] = {"high": 0, "normal": 1, "low": 2}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _estimate_tokens(lines: list[str]) -> int:
    """Rough token estimate: words / 4 per line."""
    total = 0
    for line in lines:
        total += max(1, len(line.split()) // 4)
    return total


def _parse_timestamp(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_context_window(
    lines: list[str],
    max_tokens: int = 4000,
    task_id: str = "",
    priority: str = "normal",
) -> ContextWindow:
    """Build a ContextWindow from *lines*, stopping at *max_tokens*."""
    start_marker = lines[0][:50] if lines else ""
    end_marker = ""
    used = 0
    for line in lines:
        cost = max(1, len(line.split()) // 4)
        if used + cost > max_tokens:
            break
        used += cost
        end_marker = line[:50]

    return ContextWindow(
        task_id=task_id,
        start_marker=start_marker,
        end_marker=end_marker,
        max_tokens=max_tokens,
        priority=priority,
    )


def is_context_stale(state: ContextState, max_age_seconds: int = 1800) -> bool:
    """Return True if *state.last_refreshed* is older than *max_age_seconds*."""
    try:
        refreshed = _parse_timestamp(state.last_refreshed)
    except (ValueError, AttributeError):
        return True
    age = (datetime.now(UTC) - refreshed).total_seconds()
    return age > max_age_seconds


def refresh_context(state: ContextState) -> ContextState:
    """Return a new ContextState with last_refreshed set to now."""
    return ContextState(
        windows=state.windows,
        total_tokens=state.total_tokens,
        last_refreshed=_utc_now(),
    )


def prioritize_windows(windows: list[ContextWindow]) -> list[ContextWindow]:
    """Sort windows by priority (high > normal > low), then max_tokens desc."""
    return sorted(
        windows,
        key=lambda w: (_PRIORITY_ORDER.get(w.priority, 99), -w.max_tokens),
    )


def trim_context(lines: list[str], max_tokens: int) -> list[str]:
    """Keep lines from the end (most recent) that fit within *max_tokens*."""
    if not lines:
        return []
    result: list[str] = []
    budget = max_tokens
    for line in reversed(lines):
        cost = max(1, len(line.split()) // 4)
        if budget - cost < 0:
            break
        budget -= cost
        result.append(line)
    result.reverse()
    return result


def inject_context_for_task(
    all_context: str,
    windows: list[ContextWindow],
    task_id: str,
) -> str:
    """Extract the substring matching *task_id* from *all_context*."""
    for w in windows:
        if w.task_id == task_id:
            start = all_context.find(w.start_marker)
            if start == -1:
                continue
            end = all_context.find(w.end_marker, start)
            if end == -1:
                continue
            return all_context[start : end + len(w.end_marker)]
    return ""


def format_context_report(state: ContextState) -> str:
    """Human-readable summary of context state."""
    stale = is_context_stale(state)
    status = "STALE" if stale else "FRESH"
    return (
        f"Context Report: {len(state.windows)} window(s), "
        f"{state.total_tokens} tokens, status={status}"
    )
