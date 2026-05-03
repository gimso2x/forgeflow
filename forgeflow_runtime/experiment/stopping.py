"""Stopping conditions and iteration metrics for XLOOP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import operator as _op


@dataclass(frozen=True)
class StopCondition:
    """A single stopping condition to evaluate against iteration metrics."""

    metric_name: str
    operator: str  # "eq", "lt", "gt", "lte", "gte"
    threshold: float
    description: str


@dataclass(frozen=True)
class IterationMetric:
    """A metric snapshot captured at a specific iteration."""

    name: str
    value: float
    iteration: int
    timestamp: str


_OPERATORS: dict[str, tuple[_op._CompareType, str]] = {
    "eq": (_op.eq, "=="),
    "lt": (_op.lt, "<"),
    "gt": (_op.gt, ">"),
    "lte": (_op.le, "<="),
    "gte": (_op.ge, ">="),
}


def check_condition(metric: IterationMetric, condition: StopCondition) -> bool:
    """Check whether a single metric satisfies a stopping condition.

    Returns True when the condition *is met* (meaning the stopping
    criterion is satisfied and the loop should consider halting).
    """
    if metric.name != condition.metric_name:
        return False
    op_func, _symbol = _OPERATORS.get(condition.operator, (_op.eq, "=="))
    return bool(op_func(metric.value, condition.threshold))


def evaluate_stopping(
    metrics: list[IterationMetric],
    conditions: list[StopCondition],
) -> tuple[bool, str]:
    """Evaluate all conditions against current metrics.

    Returns (should_stop, reason).  All conditions must be satisfied
    for should_stop to be True.  If any condition is not met the
    reason string explains which one failed.
    """
    if not conditions:
        return False, "no conditions configured"

    metrics_by_name: dict[str, IterationMetric] = {
        m.name: m for m in metrics
    }

    for cond in conditions:
        metric = metrics_by_name.get(cond.metric_name)
        if metric is None:
            return False, f"metric '{cond.metric_name}' not found"
        if not check_condition(metric, cond):
            _, symbol = _OPERATORS.get(cond.operator, (_op.eq, "=="))
            return False, (
                f"{cond.metric_name}={metric.value} "
                f"(need {symbol} {cond.threshold})"
            )

    satisfied = ", ".join(c.description for c in conditions)
    return True, f"all conditions met: {satisfied}"


def build_default_conditions() -> list[StopCondition]:
    """Return common default stopping conditions.

    - blocker_count == 0  (no blockers remain)
    - test_pass_rate >= 1.0  (all tests pass)
    """
    return [
        StopCondition(
            metric_name="blocker_count",
            operator="eq",
            threshold=0.0,
            description="blocker_count == 0",
        ),
        StopCondition(
            metric_name="test_pass_rate",
            operator="gte",
            threshold=1.0,
            description="test_pass_rate >= 1.0",
        ),
    ]


def format_iteration_report(
    metrics: list[IterationMetric],
    conditions: list[StopCondition],
    iteration: int,
) -> str:
    """Produce a human-readable summary for the current iteration."""
    lines = [f"Iteration {iteration} report:", ""]
    for m in metrics:
        lines.append(f"  {m.name}: {m.value} (iter {m.iteration})")
    lines.append("")
    should_stop, reason = evaluate_stopping(metrics, conditions)
    status = "STOP" if should_stop else "CONTINUE"
    lines.append(f"Status: {status} — {reason}")
    return "\n".join(lines)
