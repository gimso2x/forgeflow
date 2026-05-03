"""Tests for stopping conditions and iteration metrics."""

from __future__ import annotations

from forgeflow_runtime.experiment.stopping import (
    IterationMetric,
    StopCondition,
    build_default_conditions,
    check_condition,
    evaluate_stopping,
    format_iteration_report,
)


# ---------------------------------------------------------------------------
# check_condition — one test per operator
# ---------------------------------------------------------------------------

class TestCheckCondition:
    def test_eq(self) -> None:
        metric = IterationMetric(name="a", value=5.0, iteration=1, timestamp="")
        cond = StopCondition(metric_name="a", operator="eq", threshold=5.0, description="")
        assert check_condition(metric, cond) is True

    def test_lt(self) -> None:
        metric = IterationMetric(name="a", value=3.0, iteration=1, timestamp="")
        cond = StopCondition(metric_name="a", operator="lt", threshold=5.0, description="")
        assert check_condition(metric, cond) is True

    def test_lt_false(self) -> None:
        metric = IterationMetric(name="a", value=5.0, iteration=1, timestamp="")
        cond = StopCondition(metric_name="a", operator="lt", threshold=5.0, description="")
        assert check_condition(metric, cond) is False

    def test_gt(self) -> None:
        metric = IterationMetric(name="a", value=10.0, iteration=1, timestamp="")
        cond = StopCondition(metric_name="a", operator="gt", threshold=5.0, description="")
        assert check_condition(metric, cond) is True

    def test_lte(self) -> None:
        metric = IterationMetric(name="a", value=5.0, iteration=1, timestamp="")
        cond = StopCondition(metric_name="a", operator="lte", threshold=5.0, description="")
        assert check_condition(metric, cond) is True

    def test_gte(self) -> None:
        metric = IterationMetric(name="a", value=5.0, iteration=1, timestamp="")
        cond = StopCondition(metric_name="a", operator="gte", threshold=5.0, description="")
        assert check_condition(metric, cond) is True

    def test_name_mismatch(self) -> None:
        metric = IterationMetric(name="other", value=5.0, iteration=1, timestamp="")
        cond = StopCondition(metric_name="a", operator="eq", threshold=5.0, description="")
        assert check_condition(metric, cond) is False


# ---------------------------------------------------------------------------
# evaluate_stopping
# ---------------------------------------------------------------------------

class TestEvaluateStopping:
    def test_single_condition_met(self) -> None:
        metrics = [IterationMetric(name="x", value=0.0, iteration=1, timestamp="")]
        conditions = [StopCondition(metric_name="x", operator="eq", threshold=0.0, description="x==0")]
        should_stop, reason = evaluate_stopping(metrics, conditions)
        assert should_stop is True
        assert "x==0" in reason

    def test_single_condition_not_met(self) -> None:
        metrics = [IterationMetric(name="x", value=3.0, iteration=1, timestamp="")]
        conditions = [StopCondition(metric_name="x", operator="eq", threshold=0.0, description="x==0")]
        should_stop, reason = evaluate_stopping(metrics, conditions)
        assert should_stop is False
        assert "x=" in reason

    def test_multiple_conditions_all_met(self) -> None:
        metrics = [
            IterationMetric(name="blocker_count", value=0.0, iteration=1, timestamp=""),
            IterationMetric(name="test_pass_rate", value=1.0, iteration=1, timestamp=""),
        ]
        conditions = build_default_conditions()
        should_stop, reason = evaluate_stopping(metrics, conditions)
        assert should_stop is True
        assert "all conditions met" in reason

    def test_multiple_conditions_partial(self) -> None:
        metrics = [
            IterationMetric(name="blocker_count", value=1.0, iteration=1, timestamp=""),
            IterationMetric(name="test_pass_rate", value=1.0, iteration=1, timestamp=""),
        ]
        conditions = build_default_conditions()
        should_stop, _reason = evaluate_stopping(metrics, conditions)
        assert should_stop is False

    def test_missing_metric(self) -> None:
        metrics: list[IterationMetric] = []
        conditions = [StopCondition(metric_name="x", operator="eq", threshold=0.0, description="")]
        should_stop, reason = evaluate_stopping(metrics, conditions)
        assert should_stop is False
        assert "not found" in reason

    def test_empty_conditions(self) -> None:
        metrics = [IterationMetric(name="x", value=0.0, iteration=1, timestamp="")]
        should_stop, reason = evaluate_stopping(metrics, [])
        assert should_stop is False
        assert "no conditions" in reason


# ---------------------------------------------------------------------------
# build_default_conditions
# ---------------------------------------------------------------------------

class TestBuildDefaultConditions:
    def test_returns_expected_defaults(self) -> None:
        conditions = build_default_conditions()
        names = {c.metric_name for c in conditions}
        assert "blocker_count" in names
        assert "test_pass_rate" in names

    def test_blocker_condition_is_eq_zero(self) -> None:
        conditions = build_default_conditions()
        blocker = next(c for c in conditions if c.metric_name == "blocker_count")
        assert blocker.operator == "eq"
        assert blocker.threshold == 0.0

    def test_pass_rate_condition_is_gte_one(self) -> None:
        conditions = build_default_conditions()
        rate = next(c for c in conditions if c.metric_name == "test_pass_rate")
        assert rate.operator == "gte"
        assert rate.threshold == 1.0


# ---------------------------------------------------------------------------
# format_iteration_report
# ---------------------------------------------------------------------------

class TestFormatIterationReport:
    def test_output_contains_metric_values(self) -> None:
        metrics = [
            IterationMetric(name="score", value=42.5, iteration=3, timestamp="t"),
        ]
        conditions: list[StopCondition] = []
        report = format_iteration_report(metrics, conditions, iteration=3)
        assert "score: 42.5" in report
        assert "Iteration 3" in report

    def test_output_shows_stop_when_met(self) -> None:
        metrics = [IterationMetric(name="x", value=0.0, iteration=1, timestamp="")]
        conditions = [StopCondition(metric_name="x", operator="eq", threshold=0.0, description="done")]
        report = format_iteration_report(metrics, conditions, iteration=1)
        assert "STOP" in report

    def test_output_shows_continue_when_not_met(self) -> None:
        metrics = [IterationMetric(name="x", value=5.0, iteration=1, timestamp="")]
        conditions = [StopCondition(metric_name="x", operator="eq", threshold=0.0, description="done")]
        report = format_iteration_report(metrics, conditions, iteration=1)
        assert "CONTINUE" in report
