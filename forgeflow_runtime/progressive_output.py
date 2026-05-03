"""Progressive error disclosure for verbose CLI output.

Split large outputs into a short summary (sent to the LLM) and a stored
detail record that can be retrieved on demand.  This keeps context windows
lean while preserving full data for drill-down.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class OutputDetail:
    """Immutable record storing the full output for later retrieval."""

    detail_id: str
    summary: str
    full_output: str
    severity: Literal["info", "warning", "error"]
    source: Literal["pytest", "git_diff", "lint", "generic"]


@dataclass(frozen=True)
class StructuredOutput:
    """Immutable summary envelope returned to the caller."""

    summary_lines: list[str]
    detail_ids: list[str]
    total_lines: int
    truncated: bool


def generate_detail_id(source: str, timestamp: str) -> str:
    """Return a deterministic 8-hex-char ID derived from *source* and *timestamp*."""
    digest = hashlib.md5((source + timestamp).encode()).hexdigest()[:8]
    return f"{source}-{digest}"


def structure_output(
    text: str,
    source: str = "generic",
    summary_max_lines: int = 5,
) -> tuple[StructuredOutput, OutputDetail]:
    """Split *text* into a short summary and an optional detail record.

    If the text is short enough (≤ *summary_max_lines*) no detail record is
    needed; the returned ``OutputDetail`` will have ``detail_id=""`` and
    ``full_output=""``.
    """
    lines = text.splitlines()
    total_lines = len(lines)
    summary_lines = lines[:summary_max_lines]
    truncated = total_lines > summary_max_lines

    if not truncated:
        detail = OutputDetail(
            detail_id="",
            summary="\n".join(summary_lines),
            full_output="",
            severity="info",
            source=source,  # type: ignore[arg-type]
        )
        return (
            StructuredOutput(
                summary_lines=summary_lines,
                detail_ids=[],
                total_lines=total_lines,
                truncated=False,
            ),
            detail,
        )

    ts = str(time.time())
    detail_id = generate_detail_id(source, ts)
    detail = OutputDetail(
        detail_id=detail_id,
        summary="\n".join(summary_lines),
        full_output=text,
        severity="info",
        source=source,  # type: ignore[arg-type]
    )
    return (
        StructuredOutput(
            summary_lines=summary_lines,
            detail_ids=[detail_id],
            total_lines=total_lines,
            truncated=True,
        ),
        detail,
    )


def store_detail(
    detail: OutputDetail,
    store: dict[str, OutputDetail],
) -> None:
    """Persist *detail* into *store* keyed by ``detail.detail_id``."""
    store[detail.detail_id] = detail


def retrieve_detail(
    detail_id: str,
    store: dict[str, OutputDetail],
) -> OutputDetail | None:
    """Look up a previously stored detail, or ``None`` if missing."""
    return store.get(detail_id)


def format_progressive_summary(structured: StructuredOutput) -> str:
    """Human-readable summary string with detail IDs listed."""
    parts = [f"Summary ({structured.total_lines} total lines):"]
    parts.extend(f"  {line}" for line in structured.summary_lines)
    if structured.truncated and structured.detail_ids:
        parts.append("Truncated. Detail IDs: " + ", ".join(structured.detail_ids))
    return "\n".join(parts)


def format_detail_drilldown(detail: OutputDetail) -> str:
    """Full output with a header showing severity, source, and ID."""
    header = (
        f"=== Detail Drilldown ===\n"
        f"ID: {detail.detail_id}\n"
        f"Severity: {detail.severity}\n"
        f"Source: {detail.source}\n"
        f"{'=' * 23}\n"
    )
    return header + detail.full_output
