"""Fastest strategy — race adapters concurrently, return first success."""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from forgeflow_runtime.executor import RunTaskRequest, RunTaskResult, dispatch
from forgeflow_runtime.orchestra.strategy import (
    OrchestrationConfig,
    OrchestrationResult,
    _merge_artifacts,
    _provider_details,
)

logger = logging.getLogger(__name__)


def run_fastest(
    request: RunTaskRequest,
    config: OrchestrationConfig,
    *,
    use_real: bool = False,
) -> OrchestrationResult:
    """Race: dispatch to all providers concurrently; first success wins.

    Uses ThreadPoolExecutor with a configurable timeout.  If all providers
    fail or time out, returns the first error.
    """
    providers = config.providers
    timeout = config.timeout
    results_by_provider: dict[str, RunTaskResult] = {}

    def _dispatch_one(provider: str) -> tuple[str, RunTaskResult]:
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
        return provider, result

    with ThreadPoolExecutor(max_workers=len(providers)) as pool:
        futures: dict[Future, str] = {}
        for provider in providers:
            future = pool.submit(_dispatch_one, provider)
            futures[future] = provider

        winner: RunTaskResult | None = None
        winner_provider: str | None = None

        for future in as_completed(futures, timeout=timeout):
            provider = futures[future]
            try:
                _, result = future.result()
            except Exception as exc:
                result = RunTaskResult(status="failure", error=str(exc))
            results_by_provider[provider] = result

            if winner is None and result.status == "success":
                winner = result
                winner_provider = provider
                # Don't cancel remaining futures — let them finish naturally
                # so we have full provider_results for diagnostics

    # If no winner from as_completed (timeout or all failures)
    if winner is None:
        # Collect whatever we have
        for provider, result in results_by_provider.items():
            if result.status == "success":
                winner = result
                winner_provider = provider
                break

    if winner is not None and winner_provider is not None:
        return OrchestrationResult(
            status=winner.status,
            raw_output=winner.raw_output,
            token_usage=winner.token_usage,
            artifacts_produced=winner.artifacts_produced,
            error=winner.error,
            strategy_used="fastest",
            provider_results=_provider_details(
                [results_by_provider.get(p, RunTaskResult(status="failure"))
                 for p in providers],
                providers,
            ),
        )

    # All failed
    first_error = next(
        (r.error for r in results_by_provider.values() if r.error),
        "all providers failed or timed out",
    )
    return OrchestrationResult(
        status="failure",
        error=first_error,
        strategy_used="fastest",
        provider_results=_provider_details(
            [results_by_provider.get(p, RunTaskResult(status="failure"))
             for p in providers],
            providers,
        ),
    )
