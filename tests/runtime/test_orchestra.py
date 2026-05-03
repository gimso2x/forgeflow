"""Tests for the multi-model orchestration layer (issue #88)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from forgeflow_runtime.executor import (
    RunTaskRequest,
    RunTaskResult,
    StubClaudeAdapter,
    StubCodexAdapter,
    orchestrate,
)
from forgeflow_runtime.orchestra import (
    STRATEGY_REGISTRY,
    OrchestrationConfig,
    OrchestrationResult,
    run_orchestration,
)
from forgeflow_runtime.orchestra.consensus import consensus_merge
from forgeflow_runtime.orchestra.debate import _ice_score, run_debate
from forgeflow_runtime.orchestra.fastest import run_fastest
from forgeflow_runtime.orchestra.pipeline import run_pipeline
from forgeflow_runtime.policy_loader import RuntimePolicy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_request(prompt: str = "hello world", **kwargs: Any) -> RunTaskRequest:
    defaults = dict(
        prompt=prompt,
        role="worker",
        stage="execute",
        task_dir=Path("/tmp"),
        task_id="t1",
        token_budget_input=8000,
        token_budget_output=4000,
        adapter_target="claude",
    )
    defaults.update(kwargs)
    return RunTaskRequest(**defaults)


def _make_result(
    status: str = "success",
    raw_output: str | None = "output line",
    artifacts: list[str] | None = None,
    token_usage: dict[str, int] | None = None,
    error: str | None = None,
) -> RunTaskResult:
    return RunTaskResult(
        status=status,
        raw_output=raw_output,
        artifacts_produced=artifacts or [],
        token_usage=token_usage or {"input": 10, "output": 5},
        error=error,
    )


def _consensus_config(**overrides: Any) -> OrchestrationConfig:
    defaults = dict(
        strategy="consensus",
        providers=["claude", "codex"],
        fallback="first",
        timeout=120.0,
        consensus_threshold=0.6,
    )
    defaults.update(overrides)
    return OrchestrationConfig(**defaults)


def _debate_config(**overrides: Any) -> OrchestrationConfig:
    defaults = dict(
        strategy="debate",
        providers=["claude", "codex"],
        fallback="first",
        timeout=120.0,
        consensus_threshold=0.6,
    )
    defaults.update(overrides)
    return OrchestrationConfig(**defaults)


def _fastest_config(**overrides: Any) -> OrchestrationConfig:
    defaults = dict(
        strategy="fastest",
        providers=["claude", "codex"],
        fallback="first",
        timeout=120.0,
        consensus_threshold=0.6,
    )
    defaults.update(overrides)
    return OrchestrationConfig(**defaults)


def _pipeline_config(**overrides: Any) -> OrchestrationConfig:
    defaults = dict(
        strategy="pipeline",
        providers=["claude", "codex"],
        fallback="first",
        timeout=120.0,
        consensus_threshold=0.6,
    )
    defaults.update(overrides)
    return OrchestrationConfig(**defaults)


# ---------------------------------------------------------------------------
# Strategy Registry
# ---------------------------------------------------------------------------

class TestStrategyRegistry:
    def test_all_strategies_registered(self):
        assert "consensus" in STRATEGY_REGISTRY
        assert "debate" in STRATEGY_REGISTRY
        assert "pipeline" in STRATEGY_REGISTRY
        assert "fastest" in STRATEGY_REGISTRY

    def test_registry_values_are_callable(self):
        for name, fn in STRATEGY_REGISTRY.items():
            assert callable(fn), f"{name} is not callable"


# ---------------------------------------------------------------------------
# OrchestrationConfig Validation
# ---------------------------------------------------------------------------

class TestOrchestrationConfig:
    def test_valid_config(self):
        config = _consensus_config()
        assert config.strategy == "consensus"
        assert config.providers == ["claude", "codex"]
        assert config.consensus_threshold == 0.6

    def test_empty_providers_raises(self):
        with pytest.raises(ValueError, match="providers must not be empty"):
            OrchestrationConfig(strategy="consensus", providers=[])

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            OrchestrationConfig(strategy="nonexistent", providers=["claude"])

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError, match="consensus_threshold"):
            OrchestrationConfig(strategy="consensus", providers=["claude"], consensus_threshold=0.0)

    def test_threshold_above_one_raises(self):
        with pytest.raises(ValueError, match="consensus_threshold"):
            OrchestrationConfig(strategy="consensus", providers=["claude"], consensus_threshold=1.5)

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout must be positive"):
            OrchestrationConfig(strategy="consensus", providers=["claude"], timeout=0.0)

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout must be positive"):
            OrchestrationConfig(strategy="consensus", providers=["claude"], timeout=-10.0)

    def test_frozen(self):
        config = _consensus_config()
        with pytest.raises(AttributeError):
            config.strategy = "debate"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# OrchestrationResult
# ---------------------------------------------------------------------------

class TestOrchestrationResult:
    def test_to_run_task_result(self):
        orch = OrchestrationResult(
            status="success",
            raw_output="hello",
            token_usage={"input": 10, "output": 5},
            artifacts_produced=["a.txt"],
            strategy_used="consensus",
            provider_results=[],
        )
        rtr = orch.to_run_task_result()
        assert rtr.status == "success"
        assert rtr.raw_output == "hello"
        assert rtr.token_usage == {"input": 10, "output": 5}
        assert rtr.artifacts_produced == ["a.txt"]

    def test_frozen(self):
        orch = OrchestrationResult(status="success")
        with pytest.raises(AttributeError):
            orch.status = "failure"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Consensus Strategy
# ---------------------------------------------------------------------------

class TestConsensusStrategy:
    def test_full_agreement(self):
        results = [
            _make_result(raw_output="line one\nline two\nline three"),
            _make_result(raw_output="line one\nline two\nline three"),
            _make_result(raw_output="line one\nline two\nline three"),
        ]
        merged = consensus_merge(results, threshold=0.6)
        assert merged.status == "success"
        lines = (merged.raw_output or "").splitlines()
        assert "line one" in lines
        assert "line two" in lines
        assert "line three" in lines

    def test_partial_agreement(self):
        results = [
            _make_result(raw_output="common line\nalpha only"),
            _make_result(raw_output="common line\nbeta only"),
            _make_result(raw_output="common line\ngamma only"),
        ]
        merged = consensus_merge(results, threshold=0.6)
        lines = (merged.raw_output or "").splitlines()
        assert "common line" in lines
        assert "alpha only" not in lines
        assert "beta only" not in lines
        assert "gamma only" not in lines

    def test_high_threshold_excludes_partial(self):
        results = [
            _make_result(raw_output="common\nalpha"),
            _make_result(raw_output="common\nbeta"),
        ]
        # With threshold 1.0, only universally-agreed lines pass
        merged = consensus_merge(results, threshold=1.0)
        lines = (merged.raw_output or "").splitlines()
        assert "common" in lines
        assert "alpha" not in lines
        assert "beta" not in lines

    def test_no_consensus_fallback(self):
        results = [
            _make_result(raw_output="alpha only"),
            _make_result(raw_output="beta only"),
        ]
        merged = consensus_merge(results, threshold=1.0)
        assert merged.status == "success"
        # Falls back to first adapter
        assert "alpha only" in (merged.raw_output or "")

    def test_all_failures_fallback(self):
        results = [
            _make_result(status="failure", raw_output=None, error="err1"),
            _make_result(status="failure", raw_output=None, error="err2"),
        ]
        merged = consensus_merge(results, threshold=0.6)
        assert merged.status == "failure"
        assert merged.error == "err1"

    def test_empty_results(self):
        merged = consensus_merge([], threshold=0.6)
        assert merged.status == "failure"

    def test_merges_artifacts(self):
        results = [
            _make_result(raw_output="line", artifacts=["a.txt"]),
            _make_result(raw_output="line", artifacts=["b.txt"]),
        ]
        merged = consensus_merge(results, threshold=0.5)
        assert "a.txt" in merged.artifacts_produced
        assert "b.txt" in merged.artifacts_produced

    def test_varying_thresholds(self):
        results = [
            _make_result(raw_output="shared\nunique_a"),
            _make_result(raw_output="shared\nunique_b"),
            _make_result(raw_output="shared\nunique_c"),
        ]
        # Low threshold: all lines pass
        merged_low = consensus_merge(results, threshold=0.1)
        assert "shared" in (merged_low.raw_output or "")
        # High threshold: only shared
        merged_high = consensus_merge(results, threshold=1.0)
        lines = (merged_high.raw_output or "").splitlines()
        assert "shared" in lines
        assert not any("unique" in l for l in lines)

    def test_run_orchestration_consensus(self):
        config = _consensus_config()
        request = _make_request()
        result = run_orchestration(request, config)
        assert result.status == "success"
        assert result.strategy_used == "consensus"
        assert len(result.provider_results) == 2


# ---------------------------------------------------------------------------
# Debate Strategy
# ---------------------------------------------------------------------------

class TestDebateStrategy:
    def test_ice_score_improved(self):
        r1 = "short answer"
        r2 = "short answer with more detail and refinement"
        score = _ice_score(r1, r2)
        assert score > 0.0

    def test_ice_score_identical(self):
        text = "some output here"
        score = _ice_score(text, text)
        # Identical outputs: improved=0.3 (no growth), complete=0, efficient=0.5
        assert 0.0 < score < 1.0

    def test_ice_score_none_inputs(self):
        assert _ice_score(None, "output") == 0.0
        assert _ice_score("output", None) == 0.0
        assert _ice_score(None, None) == 0.0

    def test_ice_score_empty(self):
        assert _ice_score("", "") == 0.0

    def test_run_debate_two_providers(self):
        config = _debate_config()
        request = _make_request()
        result = run_debate(request, config)
        assert result.status == "success"
        assert result.strategy_used == "debate"
        assert result.raw_output is not None
        assert len(result.provider_results) == 2
        # Each provider result should have round1 and round2
        for pr in result.provider_results:
            assert "round1_output" in pr
            assert "round2_output" in pr
            assert "ice_score" in pr

    def test_run_debate_single_provider(self):
        config = _debate_config(providers=["claude"])
        request = _make_request()
        result = run_debate(request, config)
        assert result.status == "success"
        assert result.raw_output is not None

    def test_run_debate_all_fail(self):
        config = _debate_config()
        request = _make_request(token_budget_input=1)  # Will be blocked
        result = run_debate(request, config)
        assert result.status == "failure"

    def test_run_orchestration_debate(self):
        config = _debate_config()
        request = _make_request()
        result = run_orchestration(request, config)
        assert result.status == "success"
        assert result.strategy_used == "debate"


# ---------------------------------------------------------------------------
# Fastest Strategy
# ---------------------------------------------------------------------------

class TestFastestStrategy:
    def test_returns_first_success(self):
        config = _fastest_config(timeout=30.0)
        request = _make_request()
        result = run_fastest(request, config)
        assert result.status == "success"
        assert result.strategy_used == "fastest"
        assert result.raw_output is not None

    def test_all_fail(self):
        config = _fastest_config(timeout=30.0)
        request = _make_request(token_budget_input=1)  # blocked
        result = run_fastest(request, config)
        assert result.status == "failure"

    def test_timeout_handling(self):
        config = _fastest_config(timeout=0.001)  # Very short timeout
        request = _make_request()
        result = run_fastest(request, config)
        # Should still succeed with stubs (they're instant)
        assert result.status == "success"

    def test_provider_results_populated(self):
        config = _fastest_config(timeout=30.0)
        request = _make_request()
        result = run_fastest(request, config)
        assert len(result.provider_results) == 2
        for pr in result.provider_results:
            assert "provider" in pr
            assert "status" in pr

    def test_run_orchestration_fastest(self):
        config = _fastest_config()
        request = _make_request()
        result = run_orchestration(request, config)
        assert result.status == "success"
        assert result.strategy_used == "fastest"


# ---------------------------------------------------------------------------
# Pipeline Strategy
# ---------------------------------------------------------------------------

class TestPipelineStrategy:
    def test_sequential_refinement(self):
        config = _pipeline_config()
        request = _make_request()
        result = run_pipeline(request, config)
        assert result.status == "success"
        assert result.strategy_used == "pipeline"
        assert result.raw_output is not None
        assert len(result.provider_results) == 2

    def test_pipeline_breaks_on_failure(self):
        config = _pipeline_config(providers=["claude", "codex"])
        request = _make_request(token_budget_input=1)  # first step blocked
        result = run_pipeline(request, config)
        assert result.status in ("failure", "blocked")

    def test_single_provider_pipeline(self):
        config = _pipeline_config(providers=["claude"])
        request = _make_request()
        result = run_pipeline(request, config)
        assert result.status == "success"
        assert len(result.provider_results) == 1

    def test_run_orchestration_pipeline(self):
        config = _pipeline_config()
        request = _make_request()
        result = run_orchestration(request, config)
        assert result.status == "success"
        assert result.strategy_used == "pipeline"


# ---------------------------------------------------------------------------
# Fallback Behavior
# ---------------------------------------------------------------------------

class TestFallbackBehavior:
    def test_consensus_no_agreement_falls_to_first(self):
        results = [
            _make_result(raw_output="first adapter output"),
            _make_result(raw_output="completely different output"),
        ]
        merged = consensus_merge(results, threshold=1.0)
        assert "first adapter output" in (merged.raw_output or "")

    def test_all_providers_fail(self):
        config = _consensus_config()
        request = _make_request(token_budget_input=1)
        result = run_orchestration(request, config)
        assert result.status == "failure"
        assert result.error is not None


# ---------------------------------------------------------------------------
# Policy Integration
# ---------------------------------------------------------------------------

class TestPolicyIntegration:
    def _make_policy(self, orchestration: dict[str, Any] | None = None) -> RuntimePolicy:
        return RuntimePolicy(
            workflow_stages=["plan", "execute"],
            stage_requirements={"plan": [], "execute": ["plan"]},
            stage_gate_map={},
            gate_requirements={},
            gate_reviews={},
            routes={},
            finalize_flags=[],
            review_order=[],
            orchestration=orchestration,
        )

    def test_orchestrate_without_orchestration_config(self):
        """No orchestration config → falls back to dispatch."""
        request = _make_request()
        policy = self._make_policy(orchestration=None)
        result = orchestrate(request, policy)
        assert result.status == "success"

    def test_orchestrate_with_empty_orchestration(self):
        """Empty dict → no strategy key → falls back to dispatch."""
        request = _make_request()
        policy = self._make_policy(orchestration={})
        result = orchestrate(request, policy)
        assert result.status == "success"

    def test_orchestrate_with_consensus_policy(self):
        """Policy with orchestration config → uses consensus."""
        request = _make_request()
        policy = self._make_policy(orchestration={
            "strategy": "consensus",
            "providers": ["claude", "codex"],
            "consensus_threshold": 0.5,
        })
        result = orchestrate(request, policy)
        assert result.status == "success"

    def test_orchestrate_with_none_policy(self):
        """None policy → falls back to dispatch."""
        request = _make_request()
        result = orchestrate(request, None)
        assert result.status == "success"

    def test_orchestrate_with_fastest_policy(self):
        request = _make_request()
        policy = self._make_policy(orchestration={
            "strategy": "fastest",
            "providers": ["claude", "codex"],
            "timeout": 30.0,
        })
        result = orchestrate(request, policy)
        assert result.status == "success"

    def test_orchestrate_with_pipeline_policy(self):
        request = _make_request()
        policy = self._make_policy(orchestration={
            "strategy": "pipeline",
            "providers": ["claude", "codex"],
        })
        result = orchestrate(request, policy)
        assert result.status == "success"

    def test_orchestrate_with_debate_policy(self):
        request = _make_request()
        policy = self._make_policy(orchestration={
            "strategy": "debate",
            "providers": ["claude", "codex"],
        })
        result = orchestrate(request, policy)
        assert result.status == "success"

    def test_runtime_policy_default_orchestration_is_none(self):
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
        assert policy.orchestration is None


# ---------------------------------------------------------------------------
# Unknown Strategy via run_orchestration
# ---------------------------------------------------------------------------

class TestUnknownStrategy:
    def test_run_orchestration_unknown(self):
        # Bypass config validation to test the runtime path
        config = OrchestrationConfig.__new__(OrchestrationConfig)
        # Manually set fields without validation
        object.__setattr__(config, "strategy", "nonexistent")
        object.__setattr__(config, "providers", ["claude"])
        object.__setattr__(config, "fallback", "first")
        object.__setattr__(config, "timeout", 120.0)
        object.__setattr__(config, "consensus_threshold", 0.6)
        # Make it hashable (frozen)
        object.__setattr__(config, "__hash__", lambda self: id(self))  # type: ignore[assignment]

        request = _make_request()
        # This should fail at the STRATEGY_REGISTRY lookup
        result = run_orchestration(request, config)
        assert result.status == "failure"
        assert "Unknown strategy" in (result.error or "")


# ---------------------------------------------------------------------------
# Token Usage Merging
# ---------------------------------------------------------------------------

class TestTokenUsageMerge:
    def test_consensus_merges_token_usage(self):
        config = _consensus_config()
        request = _make_request()
        result = run_orchestration(request, config)
        assert "input" in result.token_usage
        assert "output" in result.token_usage
        # Should have usage from both providers
        assert result.token_usage["input"] > 0

    def test_debate_merges_token_usage(self):
        config = _debate_config()
        request = _make_request()
        result = run_orchestration(request, config)
        assert result.token_usage["input"] > 0


# ---------------------------------------------------------------------------
# Public API Exports
# ---------------------------------------------------------------------------

class TestPublicAPI:
    def test_init_exports(self):
        from forgeflow_runtime.orchestra import (
            OrchestrationConfig,
            OrchestrationResult,
            STRATEGY_REGISTRY,
            run_orchestration,
        )
        assert OrchestrationConfig is not None
        assert OrchestrationResult is not None
        assert STRATEGY_REGISTRY is not None
        assert callable(run_orchestration)
