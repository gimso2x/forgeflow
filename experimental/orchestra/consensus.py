"""Consensus strategy — line-based merge with configurable agreement threshold."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from forgeflow_runtime.executor import RunTaskResult

logger = logging.getLogger(__name__)


def consensus_merge(
    results: list[RunTaskResult],
    *,
    threshold: float = 0.6,
) -> RunTaskResult:
    """Merge multiple results by line-level agreement.

    Lines that appear in a proportion of outputs >= *threshold* are included
    in the merged output.  If no lines reach consensus, falls back to the
    first adapter's output with a warning.

    Args:
        results: List of RunTaskResult from each provider.
        threshold: Fraction of providers that must agree on a line (0, 1].

    Returns:
        A single RunTaskResult with the consensus output.
    """
    successful = [r for r in results if r.status == "success" and r.raw_output]
    if not successful:
        # Fall back to first result regardless of status
        first = results[0] if results else RunTaskResult(status="failure", error="no results")
        return RunTaskResult(
            status=first.status,
            raw_output=first.raw_output,
            token_usage=first.token_usage,
            artifacts_produced=first.artifacts_produced,
            error=first.error,
        )

    n = len(successful)
    # Collect all lines with their frequency
    line_counter: Counter[str] = Counter()
    for r in successful:
        lines = (r.raw_output or "").splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped:
                line_counter[stripped] += 1

    # Select lines meeting threshold
    consensus_lines: list[str] = []
    for line, count in line_counter.most_common():
        ratio = count / n
        if ratio >= threshold:
            consensus_lines.append(line)

    if not consensus_lines:
        logger.warning(
            "No consensus reached (threshold=%.2f, providers=%d); "
            "falling back to first adapter output",
            threshold,
            n,
        )
        first = successful[0]
        return RunTaskResult(
            status=first.status,
            raw_output=first.raw_output,
            token_usage=first.token_usage,
            artifacts_produced=first.artifacts_produced,
            error=first.error,
        )

    merged_output = "\n".join(consensus_lines)
    # Merge artifacts from all successful results
    seen: set[str] = set()
    artifacts: list[str] = []
    for r in successful:
        for a in r.artifacts_produced:
            if a not in seen:
                seen.add(a)
                artifacts.append(a)

    # Merge token usage (take max per key for a conservative estimate)
    token_usage: dict[str, int] = {}
    for r in successful:
        for k, v in r.token_usage.items():
            token_usage[k] = max(token_usage.get(k, 0), v)

    return RunTaskResult(
        status="success",
        raw_output=merged_output,
        token_usage=token_usage,
        artifacts_produced=artifacts,
    )
