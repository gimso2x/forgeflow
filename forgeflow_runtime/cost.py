"""Token budget enforcement and cost estimation for ForgeFlow pipelines.

Provides model pricing tables, cost estimation, budget checking, and
USD-to-token budget conversion.  All dataclasses are frozen (immutable).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Model pricing table  (USD per 1 000 000 tokens)
# ---------------------------------------------------------------------------
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4": {"input_per_mtok": 3.0, "output_per_mtok": 15.0},
    "claude-opus-4": {"input_per_mtok": 15.0, "output_per_mtok": 75.0},
    "claude-haiku-3.5": {"input_per_mtok": 0.80, "output_per_mtok": 4.0},
    "gpt-4o": {"input_per_mtok": 2.50, "output_per_mtok": 10.0},
    "gpt-4o-mini": {"input_per_mtok": 0.15, "output_per_mtok": 0.60},
    "codex-1": {"input_per_mtok": 5.0, "output_per_mtok": 15.0},
    "default": {"input_per_mtok": 3.0, "output_per_mtok": 15.0},
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CostEstimate:
    """Cost breakdown for a single model invocation."""

    input_tokens: int
    output_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    model: str


@dataclass(frozen=True)
class BudgetConfig:
    """Budget limits for pipeline and per-task spending."""

    max_per_task: float  # max USD per single task
    max_per_pipeline: float  # max USD per pipeline run
    model: str = "default"


@dataclass(frozen=True)
class BudgetReport:
    """Accumulated cost status for a pipeline run."""

    total_cost_usd: float
    task_count: int
    over_budget: bool
    remaining_usd: float
    estimates: list[CostEstimate]


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------
def _get_pricing(model: str) -> dict[str, float]:
    """Return pricing dict for *model*, falling back to ``default``."""
    return MODEL_PRICING.get(model, MODEL_PRICING["default"])


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "default",
) -> CostEstimate:
    """Estimate USD cost for a single model invocation.

    Args:
        input_tokens: Number of input (prompt) tokens.
        output_tokens: Number of output (completion) tokens.
        model: Model identifier.  Unknown models fall back to ``default`` pricing.

    Returns:
        A frozen :class:`CostEstimate` with cost breakdown.
    """
    pricing = _get_pricing(model)
    input_cost = (input_tokens / 1_000_000) * pricing["input_per_mtok"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_per_mtok"]
    return CostEstimate(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        total_cost_usd=input_cost + output_cost,
        model=model,
    )


def check_budget(report: BudgetReport, config: BudgetConfig) -> bool:
    """Return ``True`` if the *report* is within the limits of *config*.

    Checks both the per-task ceiling (any single estimate) and the
    pipeline total.
    """
    if report.total_cost_usd > config.max_per_pipeline:
        return False
    # Individual task cost check
    for est in report.estimates:
        if est.total_cost_usd > config.max_per_task:
            return False
    return True


def accumulate_costs(
    estimates: list[CostEstimate],
    config: BudgetConfig,
) -> BudgetReport:
    """Accumulate a list of :class:`CostEstimate` into a :class:`BudgetReport`.

    Args:
        estimates: Cost estimates for completed tasks.
        config: Budget limits to compare against.

    Returns:
        A frozen :class:`BudgetReport` with totals and budget status.
    """
    total_cost = sum(e.total_cost_usd for e in estimates)
    task_count = len(estimates)
    remaining = config.max_per_pipeline - total_cost
    over = total_cost > config.max_per_pipeline or any(
        e.total_cost_usd > config.max_per_task for e in estimates
    )
    return BudgetReport(
        total_cost_usd=total_cost,
        task_count=task_count,
        over_budget=over,
        remaining_usd=remaining,
        estimates=tuple(estimates),  # type: ignore[assignment]
    )


def token_budget_from_cost(
    max_usd: float,
    model: str = "default",
    ratio: float = 3.0,
) -> tuple[int, int]:
    """Convert a USD budget into (input_tokens, output_tokens) limits.

    Uses a *ratio* of input:output cost allocation (default 3:1).  The
    budget is split so that ``ratio`` parts go to input cost and 1 part
    to output cost, then token counts are derived from model pricing.

    Args:
        max_usd: Maximum USD to spend.
        model: Model identifier for pricing lookup.
        ratio: Input-to-output cost ratio (default 3.0).

    Returns:
        ``(input_token_limit, output_token_limit)`` as non-negative ints.
    """
    pricing = _get_pricing(model)
    input_cost_share = max_usd * (ratio / (ratio + 1))
    output_cost_share = max_usd * (1.0 / (ratio + 1))

    input_tokens = int(
        (input_cost_share / pricing["input_per_mtok"]) * 1_000_000
    )
    output_tokens = int(
        (output_cost_share / pricing["output_per_mtok"]) * 1_000_000
    )
    return (max(0, input_tokens), max(0, output_tokens))
