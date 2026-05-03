from __future__ import annotations

import dataclasses

import pytest

from forgeflow_runtime.complexity import (
    ComplexityFactors,
    ComplexityScore,
    ComplexityWeights,
    assess_complexity,
    extract_factors,
    select_route,
    weights_from_policy,
)
from forgeflow_runtime.policy_loader import RuntimePolicy
from forgeflow_runtime.route_execution import adaptive_route_selection


# ── extract_factors ──────────────────────────────────────────────────────

class TestExtractFactors:
    def test_simple_brief_yields_low_file_count(self) -> None:
        brief = "Fix the typo in the README."
        factors = extract_factors(brief)
        assert factors.file_count == 0
        assert factors.requirement_count == 0
        assert factors.dependency_count == 0
        assert factors.risk_keywords == []

    def test_brief_with_file_paths(self) -> None:
        brief = "Update src/main.py, src/utils.py, and tests/test_main.py"
        factors = extract_factors(brief)
        assert factors.file_count >= 3

    def test_brief_with_risk_keywords(self) -> None:
        brief = "Deploy to production after migration of the database schema."
        factors = extract_factors(brief)
        assert "production" in factors.risk_keywords
        assert "deploy" in factors.risk_keywords
        assert "migration" in factors.risk_keywords
        assert "database" in factors.risk_keywords
        assert "schema" in factors.risk_keywords

    def test_brief_with_requirements(self) -> None:
        brief = "The module must handle errors. It should log failures. Required: auth."
        factors = extract_factors(brief)
        assert factors.requirement_count >= 3  # must, should, required

    def test_brief_with_numbered_items(self) -> None:
        brief = "1. Do thing\n2. Do other\n- [ ] Checkbox item\n3. Third item"
        factors = extract_factors(brief)
        assert factors.requirement_count >= 3

    def test_plan_with_step_estimation(self) -> None:
        brief = "Refactor module"
        plan = "Step 1. Extract interface\nStep 2. Implement adapter\nStep 3. Update tests"
        factors = extract_factors(brief, plan)
        # 3 steps × 20 lines = 60 estimated
        assert factors.estimated_lines == 60

    def test_plan_with_explicit_loc(self) -> None:
        brief = "Add feature"
        plan = "Estimated 150 LOC changed, 50 lines added"
        factors = extract_factors(brief, plan)
        assert factors.estimated_lines >= 150

    def test_dependency_imports_detected(self) -> None:
        brief = "from forgeflow_runtime.engine import execute_stage"
        factors = extract_factors(brief)
        assert factors.dependency_count >= 1

    def test_dependency_api_reference(self) -> None:
        brief = "Call the api: /v1/users endpoint"
        factors = extract_factors(brief)
        assert factors.dependency_count >= 1

    def test_combined_brief_and_plan(self) -> None:
        brief = "Update src/main.py"
        plan = "from pathlib import Path\nImport os module"
        factors = extract_factors(brief, plan)
        assert factors.file_count >= 1
        assert factors.dependency_count >= 1


# ── assess_complexity ────────────────────────────────────────────────────

class TestAssessComplexity:
    def test_low_complexity_brief(self) -> None:
        brief = "Fix a typo in the README."
        score = assess_complexity(brief)
        assert score.level == "LOW"
        assert score.route_name == "small"
        assert score.raw_score < 10.0

    def test_medium_complexity_brief(self) -> None:
        brief = (
            "The module must handle errors. It should log failures. "
            "Update src/main.py, src/utils.py, src/config.py. "
            "Required: rate limiting. Need to add retries."
            "from pathlib import Path"
        )
        score = assess_complexity(brief)
        assert score.level == "MEDIUM"
        assert score.route_name == "medium"

    def test_high_complexity_brief(self) -> None:
        brief = (
            "Deploy to production after migration of the database schema. "
            "Must update auth, security, and infrastructure modules. "
            "Breaking change to the architecture. "
            "from forgeflow_runtime.engine import execute_stage "
            "from forgeflow_runtime.executor import dispatch "
            "Update src/main.py, src/utils.py, src/auth.py, src/config.py, tests/test_all.py "
            "1. First step 2. Second step 3. Third step "
            "The system must support rollback. It should handle retries. Required: audit log."
        )
        score = assess_complexity(brief)
        assert score.level == "HIGH"
        assert score.route_name == "large_high_risk"

    def test_custom_weights_override_defaults(self) -> None:
        brief = "Deploy to production."
        # With default weights, 1 risk keyword = 3.0, total ~3.0 → LOW
        default_score = assess_complexity(brief)
        assert default_score.level == "LOW"

        # With very high risk weight, 1 keyword should push to HIGH
        heavy = ComplexityWeights(risk_keyword=50.0, high_threshold=25.0)
        score = assess_complexity(brief, weights=heavy)
        assert score.level == "HIGH"

    def test_custom_thresholds_change_boundaries(self) -> None:
        brief = "Must fix bug. Should add test. Update src/main.py."
        default_score = assess_complexity(brief)

        # Tight thresholds so even small score is HIGH
        tight = ComplexityWeights(low_threshold=1.0, high_threshold=2.0)
        score = assess_complexity(brief, weights=tight)
        # score should be HIGH because raw >= high_threshold (2.0)
        assert score.level == "HIGH"

    def test_rationale_is_human_readable(self) -> None:
        brief = "Deploy to production."
        score = assess_complexity(brief)
        assert "adaptive" in score.rationale.lower() or "Adaptive" in score.rationale
        assert score.route_name in score.rationale


# ── select_route ─────────────────────────────────────────────────────────

class TestSelectRoute:
    def test_adaptive_enabled_uses_score(self) -> None:
        score = ComplexityScore(
            raw_score=5.0,
            level="LOW",
            route_name="small",
            factors=ComplexityFactors(),
            rationale="test",
        )
        assert select_route(score, manual_route="large_high_risk", adaptive_enabled=True) == "small"

    def test_adaptive_disabled_uses_manual(self) -> None:
        score = ComplexityScore(
            raw_score=5.0,
            level="LOW",
            route_name="small",
            factors=ComplexityFactors(),
            rationale="test",
        )
        assert select_route(score, manual_route="large_high_risk", adaptive_enabled=False) == "large_high_risk"

    def test_no_manual_and_adaptive_off_defaults_to_medium(self) -> None:
        score = ComplexityScore(
            raw_score=5.0,
            level="LOW",
            route_name="small",
            factors=ComplexityFactors(),
            rationale="test",
        )
        assert select_route(score, manual_route=None, adaptive_enabled=False) == "medium"


# ── Integration ──────────────────────────────────────────────────────────

class TestIntegration:
    def test_runtime_policy_with_adaptive_routing(self) -> None:
        policy = RuntimePolicy(
            workflow_stages=[],
            stage_requirements={},
            stage_gate_map={},
            gate_requirements={},
            gate_reviews={},
            routes={},
            finalize_flags=[],
            review_order=[],
            adaptive_routing={
                "enabled": True,
                "weights": {"file_count": 1.0},
                "thresholds": {"low": 5.0, "high": 15.0},
            },
        )
        assert policy.adaptive_routing is not None
        assert policy.adaptive_routing["enabled"] is True

    def test_runtime_policy_without_adaptive_routing(self) -> None:
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
        assert policy.adaptive_routing is None

    def test_adaptive_route_selection_enabled(self) -> None:
        policy = RuntimePolicy(
            workflow_stages=[],
            stage_requirements={},
            stage_gate_map={},
            gate_requirements={},
            gate_reviews={},
            routes={},
            finalize_flags=[],
            review_order=[],
            adaptive_routing={"enabled": True, "weights": {}, "thresholds": {}},
        )
        decision = adaptive_route_selection(
            brief_text="Deploy to production. Must update auth.",
            policy=policy,
        )
        assert decision.decision.startswith("adaptive route selected:")
        assert decision.already_complete is False

    def test_adaptive_route_selection_disabled(self) -> None:
        policy = RuntimePolicy(
            workflow_stages=[],
            stage_requirements={},
            stage_gate_map={},
            gate_requirements={},
            gate_reviews={},
            routes={},
            finalize_flags=[],
            review_order=[],
            adaptive_routing={"enabled": False, "weights": {}, "thresholds": {}},
        )
        decision = adaptive_route_selection(
            brief_text="Deploy to production.",
            policy=policy,
            manual_route="small",
        )
        assert decision.decision == "route selected: small"

    def test_adaptive_route_selection_no_policy(self) -> None:
        decision = adaptive_route_selection(
            brief_text="Fix typo.",
            manual_route="small",
        )
        assert decision.decision == "route selected: small"

    def test_weights_from_policy(self) -> None:
        config = {
            "weights": {"file_count": 2.0, "risk_keyword": 5.0},
            "thresholds": {"low": 8.0, "high": 20.0},
        }
        w = weights_from_policy(config)
        assert w.file_count == 2.0
        assert w.risk_keyword == 5.0
        assert w.low_threshold == 8.0
        assert w.high_threshold == 20.0
        # defaults preserved
        assert w.estimated_lines == 0.1
        assert w.requirement_count == 2.0

    def test_complexity_factors_frozen(self) -> None:
        factors = ComplexityFactors()
        with pytest.raises(dataclasses.FrozenInstanceError):
            factors.file_count = 5  # type: ignore[misc]

    def test_complexity_weights_frozen(self) -> None:
        weights = ComplexityWeights()
        with pytest.raises(dataclasses.FrozenInstanceError):
            weights.risk_keyword = 10.0  # type: ignore[misc]

    def test_complexity_score_frozen(self) -> None:
        score = ComplexityScore(
            raw_score=1.0,
            level="LOW",
            route_name="small",
            factors=ComplexityFactors(),
            rationale="test",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            score.level = "HIGH"  # type: ignore[misc]
