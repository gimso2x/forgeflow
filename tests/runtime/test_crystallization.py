"""Tests for forgeflow_runtime.crystallization — execution path crystallization."""

from __future__ import annotations

from datetime import datetime

import pytest

from forgeflow_runtime.crystallization import (
    CrystallizedRule,
    ExecutionPath,
    RuleLevel,
    extract_pattern,
    format_crystallization_report,
    get_applicable_rules,
    pattern_key,
    promote_rule,
    record_execution,
    should_crystallize,
)


# -- Helpers ----------------------------------------------------------------

def _make_path(
    steps: list[str],
    result: str = "success",
    timestamp: str | None = None,
) -> ExecutionPath:
    return ExecutionPath(
        steps=steps,
        signals=[],
        result=result,
        duration_seconds=1.0,
        timestamp=timestamp or datetime.now().isoformat(),
    )


def _make_rule(
    pattern: list[str],
    level: RuleLevel = RuleLevel.SOFT,
    success_count: int = 5,
    failure_count: int = 1,
    promoted_at: str | None = None,
) -> CrystallizedRule:
    return CrystallizedRule(
        id="rule-1",
        pattern=pattern,
        level=level,
        success_count=success_count,
        failure_count=failure_count,
        created_at="2025-01-01T00:00:00",
        promoted_at=promoted_at,
    )


# -- extract_pattern ---------------------------------------------------------

class TestExtractPattern:
    def test_extracts_key_steps(self) -> None:
        path = _make_path(["step_a", "step_b", "step_c", "step_d"])
        pattern = extract_pattern(path)
        assert pattern == ["step_a", "step_d"]

    def test_path_with_verify_step_includes_it(self) -> None:
        path = _make_path(["step_a", "verify_output", "step_c"])
        pattern = extract_pattern(path)
        assert "verify_output" in pattern
        assert pattern[0] == "step_a"
        assert pattern[-1] == "step_c"

    def test_path_with_test_step_includes_it(self) -> None:
        path = _make_path(["step_a", "run_tests", "step_c"])
        pattern = extract_pattern(path)
        assert "run_tests" in pattern

    def test_empty_steps(self) -> None:
        path = _make_path([])
        assert extract_pattern(path) == []

    def test_single_step(self) -> None:
        path = _make_path(["only_step"])
        assert extract_pattern(path) == ["only_step"]

    def test_deduplicates(self) -> None:
        path = _make_path(["only_step", "verify_only_step"])
        pattern = extract_pattern(path)
        assert len(pattern) == len(set(pattern))


# -- pattern_key ------------------------------------------------------------

class TestPatternKey:
    def test_deterministic_for_same_input(self) -> None:
        pattern = ["a", "b", "c"]
        assert pattern_key(pattern) == pattern_key(pattern)
        assert pattern_key(pattern) == "a→b→c"

    def test_different_for_different_input(self) -> None:
        assert pattern_key(["a", "b"]) != pattern_key(["b", "a"])

    def test_empty_pattern(self) -> None:
        assert pattern_key([]) == ""


# -- record_execution --------------------------------------------------------

class TestRecordExecution:
    def test_counts_successes_correctly(self) -> None:
        path = _make_path(["step_a", "step_b"])
        result = record_execution([path], {})
        key = pattern_key(extract_pattern(path))
        assert result[key]["successes"] == 1
        assert result[key]["failures"] == 0

    def test_groups_by_pattern(self) -> None:
        p1 = _make_path(["step_a", "step_b"])
        p2 = _make_path(["step_a", "step_b"])
        result = record_execution([p1, p2], {})
        key = pattern_key(extract_pattern(p1))
        assert result[key]["successes"] == 2

    def test_tracks_failures(self) -> None:
        p1 = _make_path(["step_a", "step_b"], result="success")
        p2 = _make_path(["step_a", "step_b"], result="failure")
        result = record_execution([p1, p2], {})
        key = pattern_key(extract_pattern(p1))
        assert result[key]["successes"] == 1
        assert result[key]["failures"] == 1

    def test_does_not_mutate_input(self) -> None:
        original: dict[str, dict] = {}
        record_execution([_make_path(["a", "b"])], original)
        assert original == {}

    def test_updates_last_seen(self) -> None:
        ts = "2025-06-15T12:00:00"
        path = _make_path(["a", "b"], timestamp=ts)
        result = record_execution([path], {})
        key = pattern_key(extract_pattern(path))
        assert result[key]["last_seen"] == ts


# -- should_crystallize ------------------------------------------------------

class TestShouldCrystallize:
    def test_below_threshold_returns_none(self) -> None:
        assert should_crystallize({"successes": 1}) is None
        assert should_crystallize({"successes": 2}) is None

    def test_at_soft_threshold(self) -> None:
        assert should_crystallize({"successes": 3}) == RuleLevel.SOFT

    def test_at_hard_threshold(self) -> None:
        assert should_crystallize({"successes": 10}) == RuleLevel.HARD_CANDIDATE

    def test_custom_thresholds(self) -> None:
        assert should_crystallize({"successes": 5}, soft_threshold=5, hard_threshold=20) == RuleLevel.SOFT
        assert should_crystallize({"successes": 20}, soft_threshold=5, hard_threshold=20) == RuleLevel.HARD_CANDIDATE


# -- promote_rule ------------------------------------------------------------

class TestPromoteRule:
    def test_updates_level_and_promoted_at(self) -> None:
        rule = _make_rule(["a", "b"], level=RuleLevel.SOFT)
        promoted = promote_rule(rule, RuleLevel.HARD_CANDIDATE)
        assert promoted.level == RuleLevel.HARD_CANDIDATE
        assert promoted.promoted_at is not None
        assert promoted.promoted_at != rule.promoted_at

    def test_preserves_other_fields(self) -> None:
        rule = _make_rule(["a", "b"], success_count=7, failure_count=2)
        promoted = promote_rule(rule, RuleLevel.HARD)
        assert promoted.pattern == rule.pattern
        assert promoted.success_count == 7
        assert promoted.failure_count == 2
        assert promoted.id == rule.id


# -- get_applicable_rules ---------------------------------------------------

class TestGetApplicableRules:
    def test_prefix_match(self) -> None:
        rule = _make_rule(pattern=["a", "b"])
        result = get_applicable_rules([rule], ["a", "b", "c"])
        assert result == [rule]

    def test_exact_match(self) -> None:
        rule = _make_rule(pattern=["a", "b"])
        result = get_applicable_rules([rule], ["a", "b"])
        assert result == [rule]

    def test_no_match_returns_empty(self) -> None:
        rule = _make_rule(pattern=["x", "y"])
        result = get_applicable_rules([rule], ["a", "b", "c"])
        assert result == []

    def test_pattern_longer_than_steps(self) -> None:
        rule = _make_rule(pattern=["a", "b", "c", "d"])
        result = get_applicable_rules([rule], ["a", "b"])
        assert result == []

    def test_multiple_rules(self) -> None:
        r1 = _make_rule(pattern=["a"])
        r2 = _make_rule(pattern=["a", "b"])
        r3 = _make_rule(pattern=["x"])
        result = get_applicable_rules([r1, r2, r3], ["a", "b", "c"])
        assert r1 in result
        assert r2 in result
        assert r3 not in result


# -- format_crystallization_report -------------------------------------------

class TestFormatCrystallizationReport:
    def test_contains_level_names(self) -> None:
        rules = [
            _make_rule(["a", "b"], level=RuleLevel.SOFT),
            _make_rule(["x", "y"], level=RuleLevel.HARD),
        ]
        report = format_crystallization_report(rules)
        assert "SOFT" in report
        assert "HARD" in report

    def test_empty_rules(self) -> None:
        report = format_crystallization_report([])
        assert report == ""

    def test_shows_success_rate(self) -> None:
        rule = _make_rule(["a", "b"], success_count=9, failure_count=1)
        report = format_crystallization_report([rule])
        assert "90%" in report
