from __future__ import annotations

import dataclasses

import pytest

from forgeflow_runtime.output_compression import (
    CompressConfig,
    CompressionResult,
    compress_git_diff,
    compress_lint,
    compress_output,
    compress_pytest,
    drop_matching_lines,
    format_compression_summary,
)


# ── drop_matching_lines ─────────────────────────────────────────────────

class TestDropMatchingLines:
    def test_removes_matching_lines_and_returns_count(self) -> None:
        text = "keep\n--- drop\nkeep2\n+++ drop\nkeep3"
        result, count = drop_matching_lines(text, ["^---", "^\\+\\+\\+"])
        lines = result.splitlines()
        assert lines == ["keep", "keep2", "keep3"]
        assert count == 2

    def test_no_patterns_returns_text_unchanged(self) -> None:
        text = "line1\nline2\nline3"
        result, count = drop_matching_lines(text, [])
        assert result == text
        assert count == 0


# ── compress_output ─────────────────────────────────────────────────────

class TestCompressOutput:
    def test_short_text_unchanged_ratio_one(self) -> None:
        text = "hello\nworld"
        result = compress_output(text)
        assert result.ratio == 1.0
        assert result.output == text
        assert result.lines_dropped == 0

    def test_long_text_compressed_ratio_below_one(self) -> None:
        lines = [f"line {i}" for i in range(100)]
        text = "\n".join(lines)
        result = compress_output(text)
        assert result.ratio < 1.0
        assert result.compressed_length < result.original_length
        assert "[... 80 lines compressed ...]" in result.output

    def test_respects_max_lines_keeps_first_and_last(self) -> None:
        config = CompressConfig(max_lines=15, keep_first=5, keep_last=5)
        lines = [f"line {i}" for i in range(50)]
        text = "\n".join(lines)
        result = compress_output(text, config)
        out_lines = result.output.splitlines()
        # first 5 original lines present
        assert out_lines[0] == "line 0"
        assert out_lines[4] == "line 4"
        # last 5 original lines present
        assert out_lines[-1] == "line 49"
        assert out_lines[-5] == "line 45"
        # total: 5 head + 1 summary + 5 tail = 11
        assert len(out_lines) == 11

    def test_respects_drop_patterns(self) -> None:
        config = CompressConfig(drop_patterns=["^skip"])
        text = "keep\nskip me\nkeep2\nskip too\nkeep3"
        result = compress_output(text, config)
        assert result.lines_dropped == 2
        assert "skip" not in result.output


# ── preset compressors ──────────────────────────────────────────────────

class TestCompressGitDiff:
    def test_drops_diff_metadata_lines(self) -> None:
        text = (
            "diff --git a/foo.py b/foo.py\n"
            "index abc1234..def5678 100644\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -1,3 +1,4 @@\n"
            " context line\n"
            "+added line\n"
            "-removed line\n"
        )
        result = compress_git_diff(text)
        # 5 metadata lines should be dropped
        assert result.lines_dropped == 5
        assert "added line" in result.output


class TestCompressPytest:
    def test_drops_pytest_boilerplate(self) -> None:
        text = (
            "test session starts\n"
            "platform linux\n"
            "==== test session starts ====\n"
            "PASSED test_foo.py::test_bar\n"
            "important error message\n"
            "PASSED test_foo.py::test_baz\n"
        )
        result = compress_pytest(text)
        assert "important error message" in result.output
        assert result.lines_dropped >= 1


class TestCompressLint:
    def test_drops_blank_lines(self) -> None:
        text = "error1\n\n   \nerror2\n\nerror3"
        result = compress_lint(text)
        assert result.lines_dropped == 3
        assert "error1" in result.output
        assert "error2" in result.output
        assert "error3" in result.output


# ── format_compression_summary ──────────────────────────────────────────

class TestFormatCompressionSummary:
    def test_contains_label_and_ratio(self) -> None:
        result = CompressionResult(
            original_length=5000,
            compressed_length=1200,
            ratio=0.24,
            output="",
            lines_dropped=340,
        )
        summary = format_compression_summary(result, label="git-diff")
        assert "git-diff" in summary
        assert "5000" in summary
        assert "1200" in summary
        assert "76%" in summary
        assert "340" in summary


# ── frozen dataclass immutability ───────────────────────────────────────

class TestFrozenImmutability:
    def test_compression_result_is_frozen(self) -> None:
        r = CompressionResult(100, 50, 0.5, "out", 2)
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.ratio = 0.9  # type: ignore[misc]

    def test_compress_config_is_frozen(self) -> None:
        c = CompressConfig(max_lines=20)
        with pytest.raises(dataclasses.FrozenInstanceError):
            c.max_lines = 99  # type: ignore[misc]
