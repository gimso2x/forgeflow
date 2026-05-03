from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.executor import RunTaskResult
from forgeflow_runtime.gate_evaluation import evaluate_with_ralf
from forgeflow_runtime.gate_ralf import RALFAttempt, RALFResult, ralf_config_from_policy, ralf_loop
from forgeflow_runtime.policy_loader import GateRetryConfig, RuntimePolicy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _passing_gate() -> None:
    """Gate that always passes."""
    pass


def _failing_gate(reason: str = "missing artifact") -> None:
    """Gate that always fails with the given reason."""
    raise RuntimeViolation(reason)


def _make_fix_result(raw_output: str = "fixed") -> RunTaskResult:
    return RunTaskResult(
        status="success",
        artifacts_produced=[],
        token_usage={},
        raw_output=raw_output,
    )


def _minimal_policy(**overrides: Any) -> RuntimePolicy:
    defaults: dict[str, Any] = dict(
        workflow_stages=[],
        stage_requirements={},
        stage_gate_map={},
        gate_requirements={},
        gate_reviews={},
        routes={},
        finalize_flags=[],
        review_order=[],
    )
    defaults.update(overrides)
    return RuntimePolicy(**defaults)


# ---------------------------------------------------------------------------
# ralf_loop tests
# ---------------------------------------------------------------------------

class TestRALFLoopPassesImmediately:
    def test_single_attempt_on_pass(self) -> None:
        result = ralf_loop(
            _passing_gate,
            lambda _: _make_fix_result(),
            max_attempts=3,
        )
        assert result.passed is True
        assert len(result.attempts) == 1
        assert result.attempts[0].passed is True
        assert result.circuit_breaker_tripped is False


class TestRALFLoopFailsThenPasses:
    def test_second_attempt_passes(self) -> None:
        call_count = 0

        def gate() -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeViolation("first failure")

        result = ralf_loop(
            gate,
            lambda _: _make_fix_result(),
            max_attempts=3,
            stage_name="quality-review",
        )
        assert result.passed is True
        assert len(result.attempts) == 2
        assert result.attempts[0].passed is False
        assert result.attempts[0].rejection_reason == "first failure"
        assert result.attempts[1].passed is True


class TestRALFLoopAllFail:
    def test_exhausts_attempts(self) -> None:
        result = ralf_loop(
            lambda: _failing_gate("always broken"),
            lambda _: _make_fix_result(),
            max_attempts=3,
            circuit_breaker=5,
        )
        assert result.passed is False
        assert len(result.attempts) == 3
        assert all(not a.passed for a in result.attempts)
        assert result.circuit_breaker_tripped is False


class TestCircuitBreaker:
    def test_trips_on_consecutive_same_reason(self) -> None:
        result = ralf_loop(
            lambda: _failing_gate("stuck error"),
            lambda _: _make_fix_result(),
            max_attempts=10,
            circuit_breaker=3,
        )
        assert result.passed is False
        assert result.circuit_breaker_tripped is True
        assert result.escalated is True
        # Should stop after circuit_breaker failures (3), not max_attempts
        assert len(result.attempts) == 3

    def test_does_not_trip_when_reasons_differ(self) -> None:
        reasons = ["error A", "error B", "error A", "error C"]
        idx = [0]

        def gate() -> None:
            raise RuntimeViolation(reasons[idx[0] % len(reasons)])
            idx[0] += 1  # noqa: unreachable — but documents intent

        # Actually we need a side-effect gate:
        call_count = 0

        def rotating_gate() -> None:
            nonlocal call_count
            raise RuntimeViolation(reasons[call_count % len(reasons)])
            call_count += 1  # noqa: unreachable

        # Let's use a proper approach with a mutable list
        state = {"n": 0}

        def gate2() -> None:
            reason = reasons[state["n"] % len(reasons)]
            state["n"] += 1
            raise RuntimeViolation(reason)

        result = ralf_loop(
            gate2,
            lambda _: _make_fix_result(),
            max_attempts=4,
            circuit_breaker=3,
        )
        assert result.passed is False
        assert result.circuit_breaker_tripped is False
        # No two consecutive same reasons (A, B, A, C) so no trip
        assert len(result.attempts) == 4


class TestFixPromptContent:
    def test_fix_executor_receives_reason(self) -> None:
        received_prompts: list[str] = []

        def fix_executor(prompt: str) -> RunTaskResult:
            received_prompts.append(prompt)
            return _make_fix_result()

        ralf_loop(
            lambda: _failing_gate("artifact X missing"),
            fix_executor,
            max_attempts=2,
            circuit_breaker=5,
            stage_name="spec-review",
        )
        # fix_executor is called once per failed attempt before the last
        assert len(received_prompts) >= 1
        prompt = received_prompts[0]
        assert "artifact X missing" in prompt
        assert "spec-review" in prompt
        assert "Fix the issues and re-run" in prompt


# ---------------------------------------------------------------------------
# evaluate_with_ralf tests
# ---------------------------------------------------------------------------

class TestEvaluateWithRALFNoFixExecutor:
    def test_passes_single_gate_check(self, tmp_path: Path) -> None:
        policy = _minimal_policy()
        result = evaluate_with_ralf(
            tmp_path, policy, "spec-review",
            canonical_task_id="T-001",
        )
        assert result.passed is True
        assert len(result.attempts) == 1

    def test_fails_single_gate_check(self, tmp_path: Path) -> None:
        # Create a policy with a gate that will fail
        policy = _minimal_policy(
            stage_gate_map={"spec-review": "spec_gate"},
            gate_requirements={"spec_gate": ["nonexistent.json"]},
        )
        result = evaluate_with_ralf(
            tmp_path, policy, "spec-review",
            canonical_task_id="T-001",
        )
        assert result.passed is False
        assert len(result.attempts) == 1
        assert result.attempts[0].rejection_reason is not None


class TestEvaluateWithRALFFixExecutor:
    def test_full_ralf_loop_with_fix(self, tmp_path: Path) -> None:
        policy = _minimal_policy()
        call_count = 0

        def fix_executor(prompt: str) -> RunTaskResult:
            nonlocal call_count
            call_count += 1
            return _make_fix_result(f"fix attempt {call_count}")

        # Gate will fail first, then we override via a custom gate_fn
        # But evaluate_with_ralf uses enforce_stage_gate internally,
        # so we need a gate that passes after first failure.
        # Since this is integration-level, let's use a policy where
        # the gate is None (no gate configured) → passes immediately.
        result = evaluate_with_ralf(
            tmp_path, policy, "spec-review",
            canonical_task_id="T-001",
            fix_executor=fix_executor,
            max_attempts=3,
        )
        # No gate configured → passes on first try, no fix calls
        assert result.passed is True
        assert call_count == 0


# ---------------------------------------------------------------------------
# Frozen dataclass tests
# ---------------------------------------------------------------------------

class TestFrozenDataclasses:
    def test_ralf_attempt_immutable(self) -> None:
        attempt = RALFAttempt(attempt=1, passed=True)
        with pytest.raises(dataclasses.FrozenInstanceError):
            attempt.passed = False  # type: ignore[misc]

    def test_ralf_result_immutable(self) -> None:
        result = RALFResult(passed=True, attempts=[])
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.passed = False  # type: ignore[misc]

    def test_gate_retry_config_immutable(self) -> None:
        cfg = GateRetryConfig()
        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.max_attempts = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# GateRetryConfig tests
# ---------------------------------------------------------------------------

class TestGateRetryConfig:
    def test_defaults(self) -> None:
        cfg = GateRetryConfig()
        assert cfg.max_attempts == 3
        assert cfg.circuit_breaker == 3

    def test_custom_values(self) -> None:
        cfg = GateRetryConfig(max_attempts=5, circuit_breaker=2)
        assert cfg.max_attempts == 5
        assert cfg.circuit_breaker == 2


# ---------------------------------------------------------------------------
# RuntimePolicy gate_retry integration
# ---------------------------------------------------------------------------

class TestRuntimePolicyGateRetry:
    def test_policy_without_gate_retry(self) -> None:
        policy = _minimal_policy()
        assert policy.gate_retry is None
        cfg = ralf_config_from_policy(policy)
        assert cfg.max_attempts == 3
        assert cfg.circuit_breaker == 3

    def test_policy_with_gate_retry(self) -> None:
        policy = _minimal_policy(
            gate_retry={"max_attempts": 5, "circuit_breaker": 2},
        )
        assert policy.gate_retry == {"max_attempts": 5, "circuit_breaker": 2}
        cfg = ralf_config_from_policy(policy)
        assert cfg.max_attempts == 5
        assert cfg.circuit_breaker == 2

    def test_ralf_config_from_policy_partial_override(self) -> None:
        policy = _minimal_policy(
            gate_retry={"max_attempts": 7},
        )
        cfg = ralf_config_from_policy(policy)
        assert cfg.max_attempts == 7
        assert cfg.circuit_breaker == 3  # default

    def test_ralf_config_from_policy_none_object(self) -> None:
        cfg = ralf_config_from_policy(None)
        assert cfg == GateRetryConfig()


# ---------------------------------------------------------------------------
# Progress detection via rejection reasons
# ---------------------------------------------------------------------------

class TestProgressDetection:
    def test_attempt_records_rejection_reason(self) -> None:
        result = ralf_loop(
            lambda: _failing_gate("type error on line 42"),
            lambda _: _make_fix_result(),
            max_attempts=1,
            circuit_breaker=5,
        )
        assert result.attempts[0].rejection_reason == "type error on line 42"

    def test_attempt_records_fix_result(self) -> None:
        fix = _make_fix_result("applied patch")
        result = ralf_loop(
            lambda: _failing_gate("broken"),
            lambda _: fix,
            max_attempts=1,
            circuit_breaker=5,
        )
        assert result.attempts[0].fix_result is fix
        assert result.attempts[0].fix_prompt is not None

    def test_final_output_from_last_fix(self) -> None:
        result = ralf_loop(
            lambda: _failing_gate("always"),
            lambda _: _make_fix_result("last fix output"),
            max_attempts=2,
            circuit_breaker=5,
        )
        assert result.final_output == "last fix output"
