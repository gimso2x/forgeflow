"""Tests for forgeflow_runtime.cost — token budget enforcement."""

from __future__ import annotations

import pytest

from forgeflow_runtime.cost import (
    BudgetConfig,
    BudgetReport,
    CostEstimate,
    accumulate_costs,
    check_budget,
    estimate_cost,
    token_budget_from_cost,
)


# -- estimate_cost ----------------------------------------------------------

class TestEstimateCost:
    def test_known_model_claude_sonnet(self) -> None:
        est = estimate_cost(1_000_000, 1_000_000, "claude-sonnet-4")
        assert est.model == "claude-sonnet-4"
        assert est.input_tokens == 1_000_000
        assert est.output_tokens == 1_000_000
        assert est.input_cost_usd == pytest.approx(3.0)
        assert est.output_cost_usd == pytest.approx(15.0)
        assert est.total_cost_usd == pytest.approx(18.0)

    def test_known_model_gpt4o(self) -> None:
        est = estimate_cost(2_000_000, 500_000, "gpt-4o")
        assert est.input_cost_usd == pytest.approx(5.0)
        assert est.output_cost_usd == pytest.approx(5.0)
        assert est.total_cost_usd == pytest.approx(10.0)

    def test_known_model_gpt4o_mini(self) -> None:
        est = estimate_cost(1_000_000, 1_000_000, "gpt-4o-mini")
        assert est.input_cost_usd == pytest.approx(0.15)
        assert est.output_cost_usd == pytest.approx(0.60)
        assert est.total_cost_usd == pytest.approx(0.75)

    def test_known_model_claude_opus(self) -> None:
        est = estimate_cost(1_000_000, 1_000_000, "claude-opus-4")
        assert est.input_cost_usd == pytest.approx(15.0)
        assert est.output_cost_usd == pytest.approx(75.0)
        assert est.total_cost_usd == pytest.approx(90.0)

    def test_unknown_model_falls_back_to_default(self) -> None:
        est = estimate_cost(1_000_000, 1_000_000, "nonexistent-model")
        assert est.model == "nonexistent-model"
        assert est.input_cost_usd == pytest.approx(3.0)
        assert est.output_cost_usd == pytest.approx(15.0)

    def test_zero_tokens(self) -> None:
        est = estimate_cost(0, 0, "claude-sonnet-4")
        assert est.total_cost_usd == 0.0
        assert est.input_tokens == 0
        assert est.output_tokens == 0

    def test_small_token_count(self) -> None:
        est = estimate_cost(100, 50, "claude-sonnet-4")
        assert est.input_cost_usd == pytest.approx(0.0003)
        assert est.output_cost_usd == pytest.approx(0.00075)


# -- frozen dataclass immutability ------------------------------------------

class TestImmutability:
    def test_cost_estimate_frozen(self) -> None:
        est = estimate_cost(100, 50)
        with pytest.raises(AttributeError):
            est.input_tokens = 999  # type: ignore[misc]

    def test_budget_config_frozen(self) -> None:
        cfg = BudgetConfig(max_per_task=1.0, max_per_pipeline=10.0)
        with pytest.raises(AttributeError):
            cfg.max_per_task = 99.0  # type: ignore[misc]

    def test_budget_report_frozen(self) -> None:
        rpt = BudgetReport(
            total_cost_usd=0.5,
            task_count=1,
            over_budget=False,
            remaining_usd=9.5,
            estimates=[],
        )
        with pytest.raises(AttributeError):
            rpt.total_cost_usd = 999.0  # type: ignore[misc]


# -- check_budget -----------------------------------------------------------

class TestCheckBudget:
    def test_within_budget(self) -> None:
        est = estimate_cost(100_000, 50_000, "claude-sonnet-4")
        report = BudgetReport(
            total_cost_usd=est.total_cost_usd,
            task_count=1,
            over_budget=False,
            remaining_usd=10.0 - est.total_cost_usd,
            estimates=[est],
        )
        config = BudgetConfig(max_per_task=2.0, max_per_pipeline=10.0)
        assert check_budget(report, config) is True

    def test_over_pipeline_budget(self) -> None:
        est = estimate_cost(10_000_000, 10_000_000, "claude-sonnet-4")
        report = BudgetReport(
            total_cost_usd=est.total_cost_usd,
            task_count=1,
            over_budget=True,
            remaining_usd=-80.0,
            estimates=[est],
        )
        config = BudgetConfig(max_per_task=100.0, max_per_pipeline=10.0)
        assert check_budget(report, config) is False

    def test_single_task_over_per_task_limit(self) -> None:
        # Very expensive single task
        est = estimate_cost(10_000_000, 10_000_000, "claude-opus-4")
        report = BudgetReport(
            total_cost_usd=est.total_cost_usd,
            task_count=1,
            over_budget=True,
            remaining_usd=1000.0 - est.total_cost_usd,
            estimates=[est],
        )
        config = BudgetConfig(max_per_task=1.0, max_per_pipeline=1000.0)
        assert check_budget(report, config) is False


# -- accumulate_costs -------------------------------------------------------

class TestAccumulateCosts:
    def test_multiple_estimates(self) -> None:
        e1 = estimate_cost(1_000_000, 500_000, "claude-sonnet-4")
        e2 = estimate_cost(2_000_000, 1_000_000, "claude-sonnet-4")
        config = BudgetConfig(max_per_task=50.0, max_per_pipeline=100.0)
        report = accumulate_costs([e1, e2], config)
        assert report.task_count == 2
        assert report.total_cost_usd == pytest.approx(e1.total_cost_usd + e2.total_cost_usd)
        assert report.remaining_usd == pytest.approx(100.0 - report.total_cost_usd)
        assert report.over_budget is False

    def test_empty_estimates(self) -> None:
        config = BudgetConfig(max_per_task=1.0, max_per_pipeline=10.0)
        report = accumulate_costs([], config)
        assert report.task_count == 0
        assert report.total_cost_usd == 0.0
        assert report.remaining_usd == pytest.approx(10.0)
        assert report.over_budget is False

    def test_over_budget_flag_set(self) -> None:
        e = estimate_cost(100_000_000, 100_000_000, "claude-opus-4")
        config = BudgetConfig(max_per_task=999.0, max_per_pipeline=1.0)
        report = accumulate_costs([e], config)
        assert report.over_budget is True
        assert report.remaining_usd < 0

    def test_estimates_list_is_tuple(self) -> None:
        e = estimate_cost(100, 50)
        config = BudgetConfig(max_per_task=1.0, max_per_pipeline=10.0)
        report = accumulate_costs([e], config)
        assert isinstance(report.estimates, tuple)


# -- token_budget_from_cost -------------------------------------------------

class TestTokenBudgetFromCost:
    def test_basic_conversion(self) -> None:
        inp, out = token_budget_from_cost(1.0, "claude-sonnet-4")
        assert inp > 0
        assert out > 0
        # Verify the USD cost is approximately the budget
        pricing_in = 3.0 / 1_000_000
        pricing_out = 15.0 / 1_000_000
        cost = inp * pricing_in + out * pricing_out
        assert cost <= 1.0 + 0.01  # small tolerance for int truncation

    def test_zero_budget(self) -> None:
        inp, out = token_budget_from_cost(0.0)
        assert inp == 0
        assert out == 0

    def test_custom_ratio(self) -> None:
        inp, out = token_budget_from_cost(1.0, "claude-sonnet-4", ratio=1.0)
        # With ratio=1.0, input and output get equal cost share
        assert inp > 0
        assert out > 0

    def test_returns_ints(self) -> None:
        inp, out = token_budget_from_cost(0.50, "gpt-4o")
        assert isinstance(inp, int)
        assert isinstance(out, int)


# -- RuntimePolicy integration -----------------------------------------------

class TestRuntimePolicyIntegration:
    def test_budget_field_none_by_default(self) -> None:
        from forgeflow_runtime.policy_loader import RuntimePolicy

        policy = RuntimePolicy(
            workflow_stages=[],
            stage_requirements={},
            stage_gate_map={},
            gate_requirements={},
            gate_reviews={},
            routes={},
            finalize_flags=[],
            review_order=[],
        )
        assert policy.budget is None

    def test_budget_field_with_value(self) -> None:
        from forgeflow_runtime.policy_loader import RuntimePolicy

        budget = {"max_per_task": 0.50, "max_per_pipeline": 5.0, "model": "claude-sonnet-4"}
        policy = RuntimePolicy(
            workflow_stages=[],
            stage_requirements={},
            stage_gate_map={},
            gate_requirements={},
            gate_reviews={},
            routes={},
            finalize_flags=[],
            review_order=[],
            budget=budget,
        )
        assert policy.budget == budget

    def test_budget_to_budget_config(self) -> None:
        from forgeflow_runtime.policy_loader import RuntimePolicy

        budget = {"max_per_task": 1.0, "max_per_pipeline": 10.0, "model": "claude-opus-4"}
        policy = RuntimePolicy(
            workflow_stages=[],
            stage_requirements={},
            stage_gate_map={},
            gate_requirements={},
            gate_reviews={},
            routes={},
            finalize_flags=[],
            review_order=[],
            budget=budget,
        )
        if policy.budget is not None:
            cfg = BudgetConfig(
                max_per_task=policy.budget["max_per_task"],
                max_per_pipeline=policy.budget["max_per_pipeline"],
                model=policy.budget.get("model", "default"),
            )
            assert cfg.max_per_task == 1.0
            assert cfg.model == "claude-opus-4"
