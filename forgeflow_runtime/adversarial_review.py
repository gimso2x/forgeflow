from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ReviewVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_DISCUSSION = "NEEDS_DISCUSSION"


@dataclass(frozen=True)
class ReviewerResult:
    reviewer_id: str
    model: str
    verdict: ReviewVerdict
    score: float
    findings: list[str]
    confidence: float


@dataclass(frozen=True)
class AdversarialConfig:
    primary_model: str
    secondary_model: str
    tiebreaker_model: str | None = None
    min_confidence: float = 0.7
    agreement_threshold: float = 0.3


def compute_agreement(r1: ReviewerResult, r2: ReviewerResult) -> float:
    """Return agreement score between two review results.

    1.0 if same verdict, 0.0 if opposite (PASS vs FAIL),
    partial (0.5) if one or both are NEEDS_DISCUSSION.
    """
    if r1.verdict == r2.verdict:
        return 1.0
    opposite = {ReviewVerdict.PASS, ReviewVerdict.FAIL}
    if r1.verdict in opposite and r2.verdict in opposite:
        return 0.0
    return 0.5


def resolve_verdict(
    results: list[ReviewerResult], config: AdversarialConfig
) -> dict[str, Any]:
    """Resolve final verdict from one or two reviewer results."""
    if len(results) == 1:
        r = results[0]
        return {
            "verdict": r.verdict,
            "confidence": r.confidence,
            "reason": f"Single reviewer ({r.reviewer_id}) verdict: {r.verdict.value}",
            "needs_tiebreaker": False,
        }

    if len(results) >= 2:
        r1, r2 = results[0], results[1]
        avg_confidence = (r1.confidence + r2.confidence) / 2.0

        if r1.verdict == r2.verdict:
            return {
                "verdict": r1.verdict,
                "confidence": avg_confidence,
                "reason": (
                    f"Reviewers agree: {r1.reviewer_id} and "
                    f"{r2.reviewer_id} both returned {r1.verdict.value}"
                ),
                "needs_tiebreaker": False,
            }

        if config.tiebreaker_model is not None:
            return {
                "verdict": ReviewVerdict.NEEDS_DISCUSSION,
                "confidence": avg_confidence,
                "reason": (
                    f"Reviewers disagree: {r1.reviewer_id}={r1.verdict.value}, "
                    f"{r2.reviewer_id}={r2.verdict.value}; "
                    f"tiebreaker via {config.tiebreaker_model} required"
                ),
                "needs_tiebreaker": True,
            }

        return {
            "verdict": ReviewVerdict.NEEDS_DISCUSSION,
            "confidence": avg_confidence,
            "reason": (
                f"Reviewers disagree: {r1.reviewer_id}={r1.verdict.value}, "
                f"{r2.reviewer_id}={r2.verdict.value}; no tiebreaker configured"
            ),
            "needs_tiebreaker": False,
        }

    return {
        "verdict": ReviewVerdict.NEEDS_DISCUSSION,
        "confidence": 0.0,
        "reason": "No reviewer results provided",
        "needs_tiebreaker": False,
    }


def format_adversarial_report(
    results: list[ReviewerResult], resolution: dict[str, Any]
) -> str:
    """Produce a human-readable multi-line adversarial review report."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("ADVERSARIAL REVIEW REPORT")
    lines.append("=" * 60)
    lines.append("")

    for r in results:
        lines.append(f"--- {r.reviewer_id} ({r.model}) ---")
        lines.append(f"  Verdict:    {r.verdict.value}")
        lines.append(f"  Score:      {r.score:.2f}")
        lines.append(f"  Confidence: {r.confidence:.2f}")
        if r.findings:
            for finding in r.findings:
                lines.append(f"  - {finding}")
        lines.append("")

    lines.append("-" * 60)
    lines.append("RESOLUTION")
    lines.append("-" * 60)
    lines.append(f"  Verdict:         {resolution['verdict'].value}")
    lines.append(f"  Confidence:      {resolution['confidence']:.2f}")
    lines.append(f"  Needs Tiebreaker:{' Yes' if resolution['needs_tiebreaker'] else ' No'}")
    lines.append(f"  Reason:          {resolution['reason']}")
    lines.append("=" * 60)
    return "\n".join(lines)
