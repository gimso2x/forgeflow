"""Tests for forgeflow_runtime.progressive_output."""

from __future__ import annotations

import dataclasses

import pytest

from forgeflow_runtime.progressive_output import (
    OutputDetail,
    StructuredOutput,
    format_detail_drilldown,
    format_progressive_summary,
    generate_detail_id,
    retrieve_detail,
    store_detail,
    structure_output,
)


# -- generate_detail_id -------------------------------------------------------


class TestGenerateDetailId:
    def test_deterministic_for_same_input(self) -> None:
        id1 = generate_detail_id("pytest", "1234")
        id2 = generate_detail_id("pytest", "1234")
        assert id1 == id2

    def test_different_for_different_input(self) -> None:
        id1 = generate_detail_id("pytest", "1234")
        id2 = generate_detail_id("pytest", "9999")
        assert id1 != id2

    def test_format_includes_source_prefix(self) -> None:
        did = generate_detail_id("lint", "42")
        assert did.startswith("lint-")
        assert len(did.split("-")[1]) == 8


# -- structure_output ----------------------------------------------------------


class TestStructureOutput:
    def test_short_text_not_truncated(self) -> None:
        text = "line1\nline2\nline3"
        structured, detail = structure_output(text, summary_max_lines=5)
        assert structured.truncated is False
        assert detail.detail_id == ""

    def test_long_text_truncated(self) -> None:
        lines = "\n".join(f"line{i}" for i in range(10))
        structured, detail = structure_output(lines, summary_max_lines=3)
        assert structured.truncated is True
        assert detail.detail_id != ""
        assert detail.full_output == lines

    def test_summary_contains_first_n_lines(self) -> None:
        lines = "\n".join(f"line{i}" for i in range(10))
        structured, _ = structure_output(lines, summary_max_lines=3)
        assert structured.summary_lines == ["line0", "line1", "line2"]

    def test_total_lines_reflects_input(self) -> None:
        text = "a\nb\nc"
        structured, _ = structure_output(text)
        assert structured.total_lines == 3


# -- store / retrieve ----------------------------------------------------------


class TestStoreRetrieve:
    def test_round_trip(self) -> None:
        detail = OutputDetail(
            detail_id="pytest-abcd1234",
            summary="short",
            full_output="long output here",
            severity="error",
            source="pytest",
        )
        store: dict[str, OutputDetail] = {}
        store_detail(detail, store)
        result = retrieve_detail("pytest-abcd1234", store)
        assert result is not None
        assert result == detail

    def test_missing_returns_none(self) -> None:
        store: dict[str, OutputDetail] = {}
        assert retrieve_detail("no-such-id", store) is None


# -- formatting ----------------------------------------------------------------


class TestFormatting:
    def test_progressive_summary_contains_detail_ids(self) -> None:
        structured = StructuredOutput(
            summary_lines=["a", "b"],
            detail_ids=["pytest-abcd1234", "lint-efgh5678"],
            total_lines=100,
            truncated=True,
        )
        out = format_progressive_summary(structured)
        assert "pytest-abcd1234" in out
        assert "lint-efgh5678" in out

    def test_detail_drilldown_contains_severity_and_source(self) -> None:
        detail = OutputDetail(
            detail_id="pytest-abcd1234",
            summary="short",
            full_output="traceback line 1\ntraceback line 2",
            severity="error",
            source="pytest",
        )
        out = format_detail_drilldown(detail)
        assert "Severity: error" in out
        assert "Source: pytest" in out
        assert "traceback line 1" in out


# -- frozen immutability -------------------------------------------------------


class TestFrozenImmutability:
    def test_output_detail_is_frozen(self) -> None:
        detail = OutputDetail(
            detail_id="id1",
            summary="s",
            full_output="f",
            severity="info",
            source="generic",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            detail.severity = "error"  # type: ignore[misc]

    def test_structured_output_is_frozen(self) -> None:
        structured = StructuredOutput(
            summary_lines=[],
            detail_ids=[],
            total_lines=0,
            truncated=False,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            structured.truncated = True  # type: ignore[misc]
