"""Feedback routing for ForgeFlow runtime.

Classifies incoming feedback events and applies routing rules to determine
the appropriate action (retry, escalate, log, or skip).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class FeedbackSource(Enum):
    CI_WEBHOOK = "ci_webhook"
    PR_COMMENT = "pr_comment"
    USER_FEEDBACK = "user_feedback"
    SIGNAL_PIPELINE = "signal_pipeline"
    ADVERSARIAL_REVIEW = "adversarial_review"


@dataclass(frozen=True)
class FeedbackEvent:
    id: str
    source: FeedbackSource
    task_id: str | None
    message: str
    severity: str  # "low" | "medium" | "high"
    timestamp: str
    metadata: dict


@dataclass(frozen=True)
class RoutingRule:
    source: FeedbackSource | None = None
    severity: str | None = None
    target_task_id: str | None = None
    action: str = "log"  # "retry" | "escalate" | "log" | "skip"
    max_retries: int = 3


# ---------------------------------------------------------------------------
# Matching & routing
# ---------------------------------------------------------------------------

def match_rule(event: FeedbackEvent, rule: RoutingRule) -> bool:
    """Return *True* if *event* satisfies *rule*'s source and severity."""
    if rule.source is not None and event.source != rule.source:
        return False
    if rule.severity is not None and event.severity != rule.severity:
        return False
    return True


def route_feedback(
    event: FeedbackEvent,
    rules: list[RoutingRule],
    retry_counts: dict[str, int],
) -> str:
    """Return the action for *event* given ordered *rules*.

    The first matching rule wins.  If the rule's action is ``"retry"`` and
    the retry budget for the relevant task is exhausted, ``"escalate"`` is
    returned instead.  Falls back to ``"log"`` when no rule matches.
    """
    for rule in rules:
        if not match_rule(event, rule):
            continue
        if rule.action == "retry":
            key = rule.target_task_id or event.task_id or event.id
            if retry_counts.get(key, 0) >= rule.max_retries:
                return "escalate"
        return rule.action
    return "log"


# ---------------------------------------------------------------------------
# Run-state helpers
# ---------------------------------------------------------------------------

def record_feedback_event(run_state: dict, event: FeedbackEvent) -> None:
    """Append *event* to ``run_state["feedback_events"]``."""
    run_state.setdefault("feedback_events", []).append(event)


def get_feedback_history(
    run_state: dict,
    task_id: str | None = None,
) -> list[FeedbackEvent]:
    """Retrieve feedback events, optionally filtered by *task_id*."""
    events: list[FeedbackEvent] = run_state.get("feedback_events", [])
    if task_id is not None:
        events = [e for e in events if e.task_id == task_id]
    return events


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def format_feedback_report(events: list[FeedbackEvent]) -> str:
    """Return a human-readable summary grouped by source."""
    if not events:
        return "No feedback events."

    grouped: dict[FeedbackSource, list[FeedbackEvent]] = defaultdict(list)
    for event in events:
        grouped[event.source].append(event)

    lines: list[str] = []
    for source, source_events in grouped.items():
        lines.append(f"[{source.name}] ({len(source_events)} event(s))")
        for ev in source_events:
            lines.append(f"  - {ev.severity}: {ev.message}")

    return "\n".join(lines)
