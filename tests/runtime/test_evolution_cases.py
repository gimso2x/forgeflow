from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

from forgeflow_runtime.evolution_cases import (
    EvolutionCase,
    find_cases_by_tag,
    find_cases_by_trigger,
    format_evolution_report,
    generate_case_id,
    generate_readme_section,
    record_evolution_case,
    summarize_impact,
)

NOW = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _make_case(
    trigger: str = "repeated_error",
    impact: str = "high",
    tags: list[str] | None = None,
) -> EvolutionCase:
    return EvolutionCase(
        id=generate_case_id(trigger, NOW),
        title=f"Fix {trigger}",
        trigger=trigger,
        description=f"Resolved {trigger} issue",
        before_state="broken",
        after_state="fixed",
        impact=impact,
        timestamp=NOW,
        tags=tags or [],
    )


# -- generate_case_id --------------------------------------------------------

class TestGenerateCaseId:
    def test_deterministic(self) -> None:
        id1 = generate_case_id("repeated_error", "2025-01-01T00:00:00Z")
        id2 = generate_case_id("repeated_error", "2025-01-01T00:00:00Z")
        assert id1 == id2
        assert id1.startswith("EVC-")

    def test_different_inputs_different_ids(self) -> None:
        id1 = generate_case_id("repeated_error", "2025-01-01T00:00:00Z")
        id2 = generate_case_id("pattern_learning", "2025-01-01T00:00:00Z")
        assert id1 != id2


# -- record_evolution_case ----------------------------------------------------

class TestRecordEvolutionCase:
    def test_appends_to_list(self) -> None:
        case = _make_case()
        result = record_evolution_case(case, [])
        assert len(result) == 1
        assert result[0] is case

    def test_preserves_existing(self) -> None:
        original = [_make_case()]
        new_case = _make_case(trigger="pattern_learning")
        result = record_evolution_case(new_case, original)
        assert len(result) == 2
        assert result[0] is original[0]
        assert result[1] is new_case


# -- find_cases_by_trigger ----------------------------------------------------

class TestFindCasesByTrigger:
    def test_returns_matching(self) -> None:
        cases = [
            _make_case(trigger="repeated_error"),
            _make_case(trigger="pattern_learning"),
            _make_case(trigger="repeated_error"),
        ]
        result = find_cases_by_trigger(cases, "repeated_error")
        assert len(result) == 2

    def test_no_match_empty(self) -> None:
        result = find_cases_by_trigger([], "repeated_error")
        assert result == []


# -- find_cases_by_tag --------------------------------------------------------

class TestFindCasesByTag:
    def test_returns_matching(self) -> None:
        cases = [
            _make_case(tags=["bug", "critical"]),
            _make_case(tags=["refactor"]),
            _make_case(tags=["bug"]),
        ]
        result = find_cases_by_tag(cases, "bug")
        assert len(result) == 2


# -- summarize_impact ---------------------------------------------------------

class TestSummarizeImpact:
    def test_correct_counts(self) -> None:
        cases = [
            _make_case(trigger="repeated_error", impact="high"),
            _make_case(trigger="repeated_error", impact="low"),
            _make_case(trigger="pattern_learning", impact="high"),
        ]
        result = summarize_impact(cases)
        assert result["total"] == 3
        assert result["by_trigger"]["repeated_error"] == 2
        assert result["by_trigger"]["pattern_learning"] == 1
        assert result["by_impact"]["high"] == 2
        assert result["by_impact"]["low"] == 1

    def test_empty_cases_zero_totals(self) -> None:
        result = summarize_impact([])
        assert result["total"] == 0
        assert result["by_trigger"] == {}
        assert result["by_impact"] == {}


# -- format_evolution_report --------------------------------------------------

class TestFormatEvolutionReport:
    def test_contains_case_ids(self) -> None:
        case = _make_case()
        report = format_evolution_report([case])
        assert case.id in report
        assert "Evolution Report" in report

    def test_empty_cases_minimal_output(self) -> None:
        report = format_evolution_report([])
        assert "0 cases" in report


# -- generate_readme_section --------------------------------------------------

class TestGenerateReadmeSection:
    def test_markdown_table_format(self) -> None:
        case = _make_case()
        section = generate_readme_section([case])
        assert "## Evolution in Action" in section
        assert "| ID | Trigger | Impact | Description |" in section
        assert case.id in section
        assert "|----|---------|--------|" in section


# -- frozen dataclass ---------------------------------------------------------

class TestEvolutionCaseFrozen:
    def test_immutable(self) -> None:
        import pytest

        case = _make_case()
        with pytest.raises(dataclasses.FrozenInstanceError):
            case.title = "changed"  # type: ignore[misc]
