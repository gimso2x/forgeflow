from __future__ import annotations

import dataclasses

import pytest

from forgeflow_runtime.context_freshness import (
    ContextState,
    ContextWindow,
    compute_context_window,
    format_context_report,
    inject_context_for_task,
    is_context_stale,
    prioritize_windows,
    refresh_context,
    trim_context,
)


# ── compute_context_window ──────────────────────────────────────────────

class TestComputeContextWindow:
    def test_returns_window_with_estimated_tokens(self) -> None:
        lines = ["word " * 40] * 5  # ~10 tokens per line
        w = compute_context_window(lines, max_tokens=4000, task_id="t1")
        assert w.task_id == "t1"
        assert w.start_marker == lines[0][:50]
        assert w.max_tokens == 4000
        assert len(w.end_marker) > 0

    def test_empty_lines_yields_zero_tokens_window(self) -> None:
        w = compute_context_window([], max_tokens=100)
        assert w.start_marker == ""
        assert w.end_marker == ""


# ── is_context_stale ────────────────────────────────────────────────────

class TestIsContextStale:
    def test_old_timestamp_returns_true(self) -> None:
        state = ContextState(windows=[], total_tokens=0, last_refreshed="2020-01-01T00:00:00Z")
        assert is_context_stale(state, max_age_seconds=1800) is True

    def test_recent_timestamp_returns_false(self) -> None:
        from forgeflow_runtime.context_freshness import _utc_now
        state = ContextState(windows=[], total_tokens=0, last_refreshed=_utc_now())
        assert is_context_stale(state, max_age_seconds=1800) is False

    def test_invalid_timestamp_returns_true(self) -> None:
        state = ContextState(windows=[], total_tokens=0, last_refreshed="not-a-date")
        assert is_context_stale(state) is True


# ── refresh_context ─────────────────────────────────────────────────────

class TestRefreshContext:
    def test_updates_last_refreshed(self) -> None:
        state = ContextState(windows=[], total_tokens=0, last_refreshed="2020-01-01T00:00:00Z")
        refreshed = refresh_context(state)
        assert refreshed.windows == state.windows
        assert refreshed.total_tokens == state.total_tokens
        assert refreshed.last_refreshed != state.last_refreshed


# ── prioritize_windows ──────────────────────────────────────────────────

class TestPrioritizeWindows:
    def test_high_priority_first_then_by_max_tokens(self) -> None:
        windows = [
            ContextWindow(task_id="a", start_marker="", end_marker="", max_tokens=100, priority="low"),
            ContextWindow(task_id="b", start_marker="", end_marker="", max_tokens=200, priority="high"),
            ContextWindow(task_id="c", start_marker="", end_marker="", max_tokens=300, priority="high"),
            ContextWindow(task_id="d", start_marker="", end_marker="", max_tokens=150, priority="normal"),
        ]
        result = prioritize_windows(windows)
        priorities = [w.priority for w in result]
        assert priorities == ["high", "high", "normal", "low"]
        assert result[0].max_tokens >= result[1].max_tokens


# ── trim_context ────────────────────────────────────────────────────────

class TestTrimContext:
    def test_keeps_recent_lines_within_budget(self) -> None:
        lines = ["word " * 40] * 10  # ~10 tokens each
        result = trim_context(lines, max_tokens=25)
        assert len(result) < 10
        assert all(line in lines for line in result)
        # Most recent lines should be kept
        assert result == lines[-len(result):]

    def test_empty_input_returns_empty_output(self) -> None:
        assert trim_context([], max_tokens=100) == []


# ── inject_context_for_task ─────────────────────────────────────────────

class TestInjectContextForTask:
    def test_matching_task_returns_correct_substring(self) -> None:
        windows = [
            ContextWindow(
                task_id="t1",
                start_marker="BEGIN",
                end_marker="END",
                max_tokens=100,
                priority="normal",
            ),
        ]
        all_context = "BEGIN some middle content END"
        result = inject_context_for_task(all_context, windows, "t1")
        assert result == "BEGIN some middle content END"

    def test_no_match_returns_empty_string(self) -> None:
        windows = [
            ContextWindow(
                task_id="t1",
                start_marker="BEGIN",
                end_marker="END",
                max_tokens=100,
                priority="normal",
            ),
        ]
        result = inject_context_for_task("nothing here", windows, "t1")
        assert result == ""

    def test_no_matching_task_id_returns_empty(self) -> None:
        windows = [
            ContextWindow(
                task_id="t1",
                start_marker="BEGIN",
                end_marker="END",
                max_tokens=100,
                priority="normal",
            ),
        ]
        result = inject_context_for_task("BEGIN content END", windows, "other")
        assert result == ""


# ── format_context_report ───────────────────────────────────────────────

class TestFormatContextReport:
    def test_contains_token_count_and_window_count(self) -> None:
        from forgeflow_runtime.context_freshness import _utc_now
        w = ContextWindow(task_id="t", start_marker="", end_marker="", max_tokens=100, priority="normal")
        state = ContextState(windows=[w], total_tokens=42, last_refreshed=_utc_now())
        report = format_context_report(state)
        assert "42 tokens" in report
        assert "1 window" in report
        assert "FRESH" in report

    def test_stale_report_shows_stale(self) -> None:
        state = ContextState(windows=[], total_tokens=0, last_refreshed="2020-01-01T00:00:00Z")
        report = format_context_report(state)
        assert "STALE" in report


# ── frozen immutability ─────────────────────────────────────────────────

class TestFrozenImmutability:
    def test_context_window_is_frozen(self) -> None:
        w = ContextWindow(task_id="t", start_marker="s", end_marker="e", max_tokens=100, priority="high")
        assert dataclasses.is_dataclass(w)
        with pytest.raises(dataclasses.FrozenInstanceError):
            w.task_id = "changed"  # type: ignore[misc]

    def test_context_state_is_frozen(self) -> None:
        state = ContextState(windows=[], total_tokens=0, last_refreshed="now")
        assert dataclasses.is_dataclass(state)
        with pytest.raises(dataclasses.FrozenInstanceError):
            state.total_tokens = 99  # type: ignore[misc]
