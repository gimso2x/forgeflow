from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from forgeflow_runtime.executor import RunTaskRequest, RunTaskResult
from forgeflow_runtime.policy_loader import GateRetryConfig


@dataclass(frozen=True)
class RALFAttempt:
    """Record of a single RALF loop iteration."""

    attempt: int
    passed: bool
    rejection_reason: str | None = None
    fix_prompt: str | None = None
    fix_result: RunTaskResult | None = None
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class RALFResult:
    """Outcome of a RALF self-healing gate loop."""

    passed: bool
    attempts: list[RALFAttempt]
    circuit_breaker_tripped: bool = False
    escalated: bool = False
    final_output: str | None = None


def _build_fix_prompt(stage_name: str, reason: str) -> str:
    return f"Gate '{stage_name}' failed: {reason}. Fix the issues and re-run."


def ralf_loop(
    gate_fn: Callable[[], None],
    fix_executor: Callable[[str], RunTaskResult],
    *,
    max_attempts: int = 3,
    circuit_breaker: int = 3,
    stage_name: str = "",
    request: RunTaskRequest | None = None,
) -> RALFResult:
    """Run a gate check with RALF self-healing retry logic.

    The loop evaluates *gate_fn* (which must raise ``RuntimeViolation`` on
    failure).  On failure, a fix prompt is constructed from the rejection
    reason and dispatched to *fix_executor*.  The gate is then re-evaluated
    up to *max_attempts* total attempts.

    A *circuit breaker* tracks consecutive failures with the **same**
    rejection reason.  If that count reaches *circuit_breaker*, the loop
    terminates early and the result is marked as escalated.

    Args:
        gate_fn: Callable that passes silently or raises ``RuntimeViolation``.
        fix_executor: Callable accepting a fix-prompt string and returning
            a ``RunTaskResult``.
        max_attempts: Maximum number of gate evaluations (default 3).
        circuit_breaker: Consecutive same-reason failures before tripping
            (default 3).
        stage_name: Human-readable stage name for fix prompts.
        request: Optional ``RunTaskRequest`` for context (not used directly
            by the loop, but available to callers).

    Returns:
        A ``RALFResult`` with attempt history and final status.
    """
    from forgeflow_runtime.errors import RuntimeViolation

    attempts: list[RALFAttempt] = []
    consecutive_same_reason = 0
    last_reason: str | None = None
    final_output: str | None = None
    escalated = False

    for attempt_num in range(1, max_attempts + 1):
        t0 = time.monotonic()

        try:
            gate_fn()
            # Gate passed
            elapsed = time.monotonic() - t0
            attempts.append(
                RALFAttempt(
                    attempt=attempt_num,
                    passed=True,
                    duration_seconds=round(elapsed, 4),
                )
            )
            return RALFResult(
                passed=True,
                attempts=attempts,
                final_output=final_output,
            )
        except RuntimeViolation as exc:
            elapsed = time.monotonic() - t0
            reason = str(exc)

            # Circuit breaker tracking
            if reason == last_reason:
                consecutive_same_reason += 1
            else:
                consecutive_same_reason = 1
                last_reason = reason

            if consecutive_same_reason >= circuit_breaker:
                attempts.append(
                    RALFAttempt(
                        attempt=attempt_num,
                        passed=False,
                        rejection_reason=reason,
                        duration_seconds=round(elapsed, 4),
                    )
                )
                escalated = True
                return RALFResult(
                    passed=False,
                    attempts=attempts,
                    circuit_breaker_tripped=True,
                    escalated=True,
                    final_output=final_output,
                )

            # Generate fix prompt and attempt repair
            fix_prompt = _build_fix_prompt(stage_name, reason)
            fix_result = fix_executor(fix_prompt)
            final_output = fix_result.raw_output

            attempts.append(
                RALFAttempt(
                    attempt=attempt_num,
                    passed=False,
                    rejection_reason=reason,
                    fix_prompt=fix_prompt,
                    fix_result=fix_result,
                    duration_seconds=round(elapsed, 4),
                )
            )

    # Exhausted max_attempts without passing
    return RALFResult(
        passed=False,
        attempts=attempts,
        final_output=final_output,
    )


def ralf_config_from_policy(
    policy: Any | None,
    *,
    max_attempts: int = 3,
    circuit_breaker: int = 3,
) -> GateRetryConfig:
    """Extract ``GateRetryConfig`` from a policy object.

    If the policy has a ``gate_retry`` dict, its keys are used to
    override the defaults.  Falls back to defaults when the policy
    has no ``gate_retry`` field or it is ``None``.
    """
    config_dict: dict[str, Any] | None = getattr(policy, "gate_retry", None)
    if isinstance(config_dict, dict):
        return GateRetryConfig(
            max_attempts=int(config_dict.get("max_attempts", max_attempts)),
            circuit_breaker=int(config_dict.get("circuit_breaker", circuit_breaker)),
        )
    return GateRetryConfig(max_attempts=max_attempts, circuit_breaker=circuit_breaker)
