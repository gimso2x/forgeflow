"""Simplicity scoring for XLOOP experiment changes."""

from __future__ import annotations


def simplicity_score(
    files_changed: int,
    lines_added: int,
    lines_removed: int,
) -> float:
    """Calculate simplicity score (0.0-1.0).

    Higher = simpler (better). Penalizes:
    - Many files changed (scatter)
    - Large line additions (bloat)
    Rewards:
    - Net line reduction
    - Focused changes (few files)

    Formula: base = 1.0
    - subtract 0.1 per file beyond 3
    - subtract 0.001 per added line beyond 50
    - add 0.001 per removed line beyond 20
    - clamp to [0.0, 1.0]
    """
    score = 1.0
    if files_changed > 3:
        score -= 0.1 * (files_changed - 3)
    if lines_added > 50:
        score -= 0.001 * (lines_added - 50)
    if lines_removed > 20:
        score += 0.001 * (lines_removed - 20)
    return max(0.0, min(1.0, score))


def improvement_efficiency(metric_improvement: float, simplicity: float) -> float:
    """Combined score: improvement weighted by simplicity.

    Prevents accepting complex solutions for marginal metric gains.
    score = metric_improvement * (0.3 + 0.7 * simplicity)
    """
    return metric_improvement * (0.3 + 0.7 * simplicity)
