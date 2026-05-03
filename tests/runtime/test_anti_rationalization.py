"""Tests for forgeflow_runtime.anti_rationalization."""

from __future__ import annotations

from forgeflow_runtime.anti_rationalization import (
    BUILTIN_PATTERNS,
    AntiRationalizationCheck,
    RationalizationPattern,
    check_rationalization,
    format_rationalization_report,
    get_patterns_for_stage,
)


# --------------------------------------------------------------------------- #
# check_rationalization
# --------------------------------------------------------------------------- #


class TestCheckRationalization:
    def test_korean_pattern_detected(self) -> None:
        text = "요구사항이 너무 명확해서 clarify가 필요 없다"
        results = check_rationalization(text)
        assert len(results) >= 1
        assert results[0].detected is True
        assert results[0].pattern.thought == text

    def test_english_pattern_detected(self) -> None:
        text = "This is just a quick fix"
        results = check_rationalization(text)
        assert len(results) >= 1
        assert results[0].detected is True
        assert results[0].pattern.stage == "run"

    def test_no_match_returns_empty(self) -> None:
        results = check_rationalization("This text has nothing suspicious at all.")
        assert results == []

    def test_case_insensitive_match(self) -> None:
        text = "THIS IS JUST A QUICK FIX"
        results = check_rationalization(text)
        assert len(results) >= 1
        assert results[0].detected is True

    def test_uses_builtin_patterns_when_none(self) -> None:
        text = "I need more context first"
        results = check_rationalization(text, patterns=None)
        assert len(results) >= 1
        # Same result as passing BUILTIN_PATTERNS explicitly
        results_explicit = check_rationalization(text, patterns=BUILTIN_PATTERNS)
        assert [r.pattern for r in results] == [r.pattern for r in results_explicit]


# --------------------------------------------------------------------------- #
# get_patterns_for_stage
# --------------------------------------------------------------------------- #


class TestGetPatternsForStage:
    def test_returns_correct_subset(self) -> None:
        plan_patterns = get_patterns_for_stage("plan")
        assert len(plan_patterns) == 3
        assert all(p.stage == "plan" for p in plan_patterns)

    def test_unknown_stage_returns_empty(self) -> None:
        assert get_patterns_for_stage("nonexistent") == []

    def test_uses_builtin_when_none(self) -> None:
        clarify = get_patterns_for_stage("clarify", patterns=None)
        assert len(clarify) == 2


# --------------------------------------------------------------------------- #
# format_rationalization_report
# --------------------------------------------------------------------------- #


class TestFormatRationalizationReport:
    def test_contains_thought_and_reality(self) -> None:
        pattern = RationalizationPattern(
            thought="skip it",
            reality="don't skip",
            stage="plan",
            severity="high",
        )
        check = AntiRationalizationCheck(pattern=pattern, detected=True, context="x")
        report = format_rationalization_report([check])
        assert "skip it" in report
        assert "don't skip" in report

    def test_empty_checks_minimal_output(self) -> None:
        report = format_rationalization_report([])
        assert "No rationalization patterns detected" in report


# --------------------------------------------------------------------------- #
# BUILTIN_PATTERNS coverage
# --------------------------------------------------------------------------- #


class TestBuiltinPatterns:
    def test_all_five_stages_present(self) -> None:
        stages = {p.stage for p in BUILTIN_PATTERNS}
        assert stages == {"clarify", "plan", "review", "run", "verify"}
