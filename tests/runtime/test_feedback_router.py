"""Tests for forgeflow_runtime.feedback_router."""

from __future__ import annotations

import dataclasses

import pytest

from forgeflow_runtime.feedback_router import (
    FeedbackEvent,
    FeedbackSource,
    RoutingRule,
    format_feedback_report,
    get_feedback_history,
    match_rule,
    record_feedback_event,
    route_feedback,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    *,
    id: str = "e1",
    source: FeedbackSource = FeedbackSource.CI_WEBHOOK,
    task_id: str | None = "t1",
    message: str = "tests failed",
    severity: str = "high",
    timestamp: str = "2025-01-01T00:00:00Z",
    metadata: dict | None = None,
) -> FeedbackEvent:
    return FeedbackEvent(
        id=id,
        source=source,
        task_id=task_id,
        message=message,
        severity=severity,
        timestamp=timestamp,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# match_rule
# ---------------------------------------------------------------------------

class TestMatchRule:
    def test_exact_source_and_severity_match(self) -> None:
        event = _make_event(source=FeedbackSource.CI_WEBHOOK, severity="high")
        rule = RoutingRule(source=FeedbackSource.CI_WEBHOOK, severity="high")
        assert match_rule(event, rule) is True

    def test_none_rule_fields_match_any(self) -> None:
        event = _make_event(source=FeedbackSource.PR_COMMENT, severity="low")
        rule = RoutingRule()  # all None
        assert match_rule(event, rule) is True

    def test_mismatched_source(self) -> None:
        event = _make_event(source=FeedbackSource.CI_WEBHOOK, severity="high")
        rule = RoutingRule(source=FeedbackSource.USER_FEEDBACK, severity="high")
        assert match_rule(event, rule) is False

    def test_mismatched_severity(self) -> None:
        event = _make_event(source=FeedbackSource.CI_WEBHOOK, severity="high")
        rule = RoutingRule(source=FeedbackSource.CI_WEBHOOK, severity="low")
        assert match_rule(event, rule) is False


# ---------------------------------------------------------------------------
# route_feedback
# ---------------------------------------------------------------------------

class TestRouteFeedback:
    def test_first_matching_rule_wins(self) -> None:
        event = _make_event(source=FeedbackSource.CI_WEBHOOK, severity="high")
        rules = [
            RoutingRule(source=FeedbackSource.CI_WEBHOOK, severity="high", action="retry"),
            RoutingRule(source=FeedbackSource.CI_WEBHOOK, severity="high", action="skip"),
        ]
        result = route_feedback(event, rules, retry_counts={})
        assert result == "retry"

    def test_retry_exceeded_escalates(self) -> None:
        event = _make_event(source=FeedbackSource.CI_WEBHOOK, severity="high", task_id="t1")
        rules = [
            RoutingRule(
                source=FeedbackSource.CI_WEBHOOK,
                severity="high",
                action="retry",
                max_retries=2,
            ),
        ]
        result = route_feedback(event, rules, retry_counts={"t1": 3})
        assert result == "escalate"

    def test_no_match_returns_log(self) -> None:
        event = _make_event(source=FeedbackSource.USER_FEEDBACK, severity="low")
        rules = [
            RoutingRule(source=FeedbackSource.CI_WEBHOOK, severity="high", action="retry"),
        ]
        result = route_feedback(event, rules, retry_counts={})
        assert result == "log"

    def test_retry_within_budget(self) -> None:
        event = _make_event(source=FeedbackSource.CI_WEBHOOK, severity="high", task_id="t1")
        rules = [
            RoutingRule(
                source=FeedbackSource.CI_WEBHOOK,
                severity="high",
                action="retry",
                max_retries=3,
            ),
        ]
        result = route_feedback(event, rules, retry_counts={"t1": 2})
        assert result == "retry"


# ---------------------------------------------------------------------------
# record_feedback_event / get_feedback_history
# ---------------------------------------------------------------------------

class TestFeedbackState:
    def test_record_appends_to_run_state(self) -> None:
        run_state: dict = {}
        event = _make_event()
        record_feedback_event(run_state, event)
        assert len(run_state["feedback_events"]) == 1
        assert run_state["feedback_events"][0] is event

    def test_get_feedback_history_returns_all(self) -> None:
        run_state: dict = {"feedback_events": []}
        e1 = _make_event(id="e1")
        e2 = _make_event(id="e2", task_id="t2")
        record_feedback_event(run_state, e1)
        record_feedback_event(run_state, e2)
        history = get_feedback_history(run_state)
        assert len(history) == 2

    def test_get_feedback_history_filters_by_task_id(self) -> None:
        run_state: dict = {"feedback_events": []}
        e1 = _make_event(id="e1", task_id="t1")
        e2 = _make_event(id="e2", task_id="t2")
        e3 = _make_event(id="e3", task_id="t1")
        record_feedback_event(run_state, e1)
        record_feedback_event(run_state, e2)
        record_feedback_event(run_state, e3)
        filtered = get_feedback_history(run_state, task_id="t1")
        assert len(filtered) == 2
        assert all(e.task_id == "t1" for e in filtered)


# ---------------------------------------------------------------------------
# format_feedback_report
# ---------------------------------------------------------------------------

class TestFormatFeedbackReport:
    def test_contains_source_names(self) -> None:
        events = [
            _make_event(id="e1", source=FeedbackSource.CI_WEBHOOK, severity="high"),
            _make_event(id="e2", source=FeedbackSource.PR_COMMENT, severity="low", task_id="t2"),
        ]
        report = format_feedback_report(events)
        assert "CI_WEBHOOK" in report
        assert "PR_COMMENT" in report

    def test_empty_events(self) -> None:
        assert format_feedback_report([]) == "No feedback events."

    def test_groups_by_source(self) -> None:
        events = [
            _make_event(id="e1", source=FeedbackSource.CI_WEBHOOK, message="build fail"),
            _make_event(id="e2", source=FeedbackSource.CI_WEBHOOK, message="lint fail"),
        ]
        report = format_feedback_report(events)
        assert report.count("CI_WEBHOOK") == 1  # header once
        assert "build fail" in report
        assert "lint fail" in report


# ---------------------------------------------------------------------------
# FeedbackEvent immutability
# ---------------------------------------------------------------------------

class TestFeedbackEventFrozen:
    def test_frozen_immutability(self) -> None:
        event = _make_event()
        with pytest.raises(dataclasses.FrozenInstanceError):
            event.message = "changed"  # type: ignore[misc]

    def test_id_and_severity(self) -> None:
        event = _make_event(id="x", severity="medium")
        assert event.id == "x"
        assert event.severity == "medium"
