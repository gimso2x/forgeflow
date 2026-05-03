"""CLI output compression utilities.

Trim, filter, and summarise verbose CLI output (git diffs, pytest runs,
lint reports, etc.) so it fits comfortably in LLM context windows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CompressionResult:
    """Immutable snapshot of a compression pass."""

    original_length: int
    compressed_length: int
    ratio: float
    output: str
    lines_dropped: int


@dataclass(frozen=True)
class CompressConfig:
    """Tuning knobs for :func:`compress_output`."""

    max_lines: int = 50
    max_chars: int = 10_000
    keep_first: int = 10
    keep_last: int = 10
    drop_patterns: list[str] = ()  # type: ignore[assignment]


def drop_matching_lines(text: str, patterns: list[str]) -> tuple[str, int]:
    """Remove lines matching any of *patterns* (regular expressions).

    Returns ``(filtered_text, count_dropped)``.
    """
    if not patterns:
        return text, 0
    compiled = [re.compile(p) for p in patterns]
    lines = text.splitlines()
    kept: list[str] = []
    dropped = 0
    for line in lines:
        if any(rx.search(line) for rx in compiled):
            dropped += 1
        else:
            kept.append(line)
    return "\n".join(kept), dropped


def compress_output(
    text: str,
    config: CompressConfig | None = None,
) -> CompressionResult:
    """Compress *text* according to *config*.

    1. Apply :func:`drop_matching_lines` first.
    2. If the result fits within *max_lines* **and** *max_chars*, return
       it unchanged (``ratio=1.0``).
    3. Otherwise keep ``keep_first`` and ``keep_last`` lines, replacing
       the middle with a single summary line.
    """
    if config is None:
        config = CompressConfig()

    original_length = len(text)
    filtered, lines_dropped = drop_matching_lines(text, config.drop_patterns)
    lines = filtered.splitlines()

    if len(lines) <= config.max_lines and len(filtered) <= config.max_chars:
        return CompressionResult(
            original_length=original_length,
            compressed_length=len(filtered),
            ratio=1.0,
            output=filtered,
            lines_dropped=lines_dropped,
        )

    head = lines[: config.keep_first]
    tail = lines[-config.keep_last :]
    middle_count = len(lines) - config.keep_first - config.keep_last
    if middle_count < 0:
        middle_count = 0
    compressed_lines = head + [f"[... {middle_count} lines compressed ...]"] + tail
    compressed = "\n".join(compressed_lines)

    compressed_length = len(compressed)
    ratio = compressed_length / original_length if original_length else 1.0

    return CompressionResult(
        original_length=original_length,
        compressed_length=compressed_length,
        ratio=ratio,
        output=compressed,
        lines_dropped=lines_dropped,
    )


def compress_git_diff(text: str) -> CompressionResult:
    """Preset for git diff output."""
    return compress_output(
        text,
        CompressConfig(
            max_lines=30,
            drop_patterns=["^\\+\\+\\+", "^---", "^@@ ", "^index ", "^diff "],
        ),
    )


def compress_pytest(text: str) -> CompressionResult:
    """Preset for pytest output."""
    return compress_output(
        text,
        CompressConfig(
            max_lines=40,
            drop_patterns=["^=", "^PASSED", "^test session starts", "^platform "],
        ),
    )


def compress_lint(text: str) -> CompressionResult:
    """Preset for lint output."""
    return compress_output(
        text,
        CompressConfig(
            max_lines=50,
            drop_patterns=["^$", "^\\s*$"],
        ),
    )


def format_compression_summary(
    result: CompressionResult,
    label: str = "output",
) -> str:
    """One-line human-readable summary, e.g.::

        output: 5000→1200 chars (76% reduction, 340 lines dropped)
    """
    pct = (1.0 - result.ratio) * 100
    return (
        f"{label}: {result.original_length}→{result.compressed_length} chars "
        f"({pct:.0f}% reduction, {result.lines_dropped} lines dropped)"
    )
