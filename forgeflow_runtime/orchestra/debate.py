"""Debate strategy — 2-round adversarial with cross-pollination and ICE judge."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Any

from forgeflow_runtime.executor import RunTaskRequest, RunTaskResult, dispatch
from forgeflow_runtime.orchestra.strategy import (
    OrchestrationConfig,
    OrchestrationResult,
    _merge_artifacts,
    _merge_token_usage,
    _provider_details,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _RoundResult:
    """Tracks a single adapter's output across debate rounds."""

    provider: str
    round1_output: str | None
    round2_output: str | None


def _ice_score(round1: str | None, round2: str | None) -> float:
    """Compute ICE (Improved, Complete, Efficient) score for a debate entry.

    - Improved: length increase from round1 → round2 (refinement signal).
    - Complete: more unique lines in round2.
    - Efficient: shorter round2 that still covers round1 key terms.

    Returns a composite score in [0, 1].
    """
    if not round1 or not round2:
        return 0.0

    r1_lines = set(round1.strip().splitlines())
    r2_lines = set(round2.strip().splitlines())

    if not r1_lines or not r2_lines:
        return 0.0

    # Improved: length ratio (round2 / round1), capped at 1.0
    r1_len = sum(len(l) for l in r1_lines)
    r2_len = sum(len(l) for l in r2_lines)
    if r1_len == 0:
        improved = 0.0
    else:
        improved = min(1.0, r2_len / r1_len) if r2_len >= r1_len else 0.3

    # Complete: proportion of unique lines in round2 vs round1
    new_lines = r2_lines - r1_lines
    completeness = min(1.0, len(new_lines) / max(len(r1_lines), 1))

    # Efficient: if round2 is shorter but shares key terms
    # Extract "key terms" from round1 (words >= 4 chars)
    r1_terms: set[str] = set()
    for line in r1_lines:
        for word in line.split():
            if len(word) >= 4:
                r1_terms.add(word.lower())

    if r1_terms:
        r2_text = round2.lower()
        coverage = sum(1 for t in r1_terms if t in r2_text) / len(r1_terms)
        # Bonus if round2 is more concise
        conciseness = min(1.0, r1_len / max(r2_len, 1)) if r2_len < r1_len else 0.5
        efficient = 0.6 * coverage + 0.4 * conciseness
    else:
        efficient = 0.5

    # Weighted composite
    return 0.35 * improved + 0.35 * completeness + 0.30 * efficient


def _run_cross_pollination(
    request: RunTaskRequest,
    provider: str,
    other_outputs: dict[str, str],
    *,
    use_real: bool = False,
) -> RunTaskResult:
    """Round 2: an adapter sees others' outputs and revises."""
    context_parts = []
    for other_provider, output in other_outputs.items():
        context_parts.append(f"--- {other_provider} output ---\n{output}\n")
    context = "\n".join(context_parts)

    revised_prompt = (
        f"{request.prompt}\n\n"
        f"## Peer Outputs (for reference and refinement)\n\n"
        f"{context}\n\n"
        f"## Instructions\n"
        f"Review the peer outputs above and produce an improved, refined answer. "
        f"Incorporate the best ideas from peers while correcting any issues."
    )

    revised_request = RunTaskRequest(
        prompt=revised_prompt,
        role=request.role,
        stage=request.stage,
        task_dir=request.task_dir,
        task_id=request.task_id,
        token_budget_input=request.token_budget_input,
        token_budget_output=request.token_budget_output,
        adapter_target=provider,
        artifacts_to_stream=request.artifacts_to_stream,
        extra=request.extra,
    )
    return dispatch(revised_request, use_real=use_real)


def run_debate(
    request: RunTaskRequest,
    config: OrchestrationConfig,
    *,
    use_real: bool = False,
) -> OrchestrationResult:
    """2-round adversarial debate strategy.

    Round 1: each adapter produces output independently.
    Round 2: each adapter sees others' outputs (cross-pollination) and revises.
    Judge: pick the output with highest ICE score.
    """
    providers = config.providers
    round_results: list[_RoundResult] = []

    # --- Round 1: independent ---
    round1_outputs: dict[str, str] = {}
    round1_results: list[RunTaskResult] = []
    for provider in providers:
        req = RunTaskRequest(
            prompt=request.prompt,
            role=request.role,
            stage=request.stage,
            task_dir=request.task_dir,
            task_id=request.task_id,
            token_budget_input=request.token_budget_input,
            token_budget_output=request.token_budget_output,
            adapter_target=provider,
            artifacts_to_stream=request.artifacts_to_stream,
            extra=request.extra,
        )
        result = dispatch(req, use_real=use_real)
        round1_results.append(result)
        if result.status == "success" and result.raw_output:
            round1_outputs[provider] = result.raw_output

    if not round1_outputs:
        first_error = next((r.error for r in round1_results if r.error), "all providers failed")
        return OrchestrationResult(
            status="failure",
            error=first_error,
            strategy_used="debate",
            provider_results=_provider_details(round1_results, providers),
        )

    # --- Round 2: cross-pollination ---
    round2_outputs: dict[str, str] = {}
    round2_results: list[RunTaskResult] = []
    for provider in providers:
        other_outputs = {k: v for k, v in round1_outputs.items() if k != provider}
        if not other_outputs:
            # Single provider — no cross-pollination possible
            round2_outputs[provider] = round1_outputs[provider]
            round2_results.append(round1_results[providers.index(provider)])
            continue

        r2_result = _run_cross_pollination(
            request, provider, other_outputs, use_real=use_real
        )
        round2_results.append(r2_result)
        if r2_result.status == "success" and r2_result.raw_output:
            round2_outputs[provider] = r2_result.raw_output
        else:
            # Fall back to round 1 output for this provider
            round2_outputs[provider] = round1_outputs[provider]

    # --- Judge: ICE scoring ---
    best_provider = providers[0]
    best_score = -1.0
    for provider in providers:
        r1 = round1_outputs.get(provider)
        r2 = round2_outputs.get(provider)
        score = _ice_score(r1, r2)
        if score > best_score:
            best_score = score
            best_provider = provider

    best_output = round2_outputs.get(best_provider, round1_outputs.get(best_provider))

    # Build round results for tracking
    for provider in providers:
        round_results.append(_RoundResult(
            provider=provider,
            round1_output=round1_outputs.get(provider),
            round2_output=round2_outputs.get(provider),
        ))

    all_results = round1_results + round2_results
    provider_details = []
    for rr in round_results:
        provider_details.append({
            "provider": rr.provider,
            "round1_output": rr.round1_output,
            "round2_output": rr.round2_output,
            "ice_score": round(  # type: ignore[arg-type]
                _ice_score(rr.round1_output, rr.round2_output), 3
            ),
        })

    return OrchestrationResult(
        status="success",
        raw_output=best_output,
        token_usage=_merge_token_usage(all_results),
        artifacts_produced=_merge_artifacts(round1_results),
        strategy_used="debate",
        provider_results=provider_details,
    )
