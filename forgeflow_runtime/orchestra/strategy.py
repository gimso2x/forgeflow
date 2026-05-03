"""Strategy registry and orchestration dispatcher."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

from forgeflow_runtime.executor import (
    RunTaskRequest,
    RunTaskResult,
    dispatch,
)

logger = logging.getLogger(__name__)

StrategyFunc = Callable[[list[RunTaskResult]], RunTaskResult]


@dataclass(frozen=True)
class OrchestrationConfig:
    """Configuration for a multi-model orchestration run."""

    strategy: str  # "consensus" | "debate" | "pipeline" | "fastest"
    providers: list[str]  # adapter targets, e.g. ["claude", "codex"]
    fallback: str = "first"  # "first" | "none"
    timeout: float = 120.0  # for fastest strategy
    consensus_threshold: float = 0.6

    def __post_init__(self) -> None:
        if not self.providers:
            raise ValueError("OrchestrationConfig.providers must not be empty")
        if self.strategy not in STRATEGY_REGISTRY:
            raise ValueError(
                f"Unknown strategy '{self.strategy}'; "
                f"available: {sorted(STRATEGY_REGISTRY)}"
            )
        if not 0.0 < self.consensus_threshold <= 1.0:
            raise ValueError("consensus_threshold must be in (0, 1]")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")


@dataclass(frozen=True)
class OrchestrationResult:
    """Rich result from an orchestration run, wrapping RunTaskResult."""

    status: str
    raw_output: str | None = None
    token_usage: dict[str, int] = field(default_factory=dict)
    artifacts_produced: list[str] = field(default_factory=list)
    error: str | None = None
    strategy_used: str = ""
    provider_results: list[dict] = field(default_factory=list)

    def to_run_task_result(self) -> RunTaskResult:
        """Convert back to a plain RunTaskResult for compatibility."""
        return RunTaskResult(
            status=self.status,
            artifacts_produced=list(self.artifacts_produced),
            token_usage=dict(self.token_usage),
            raw_output=self.raw_output,
            error=self.error,
        )


def _fan_out(
    request: RunTaskRequest, providers: list[str], *, use_real: bool = False
) -> list[RunTaskResult]:
    """Dispatch the same request to multiple providers concurrently.

    Uses ThreadPoolExecutor so that multi-model strategies (consensus,
    debate round-1, etc.) run in parallel instead of sequentially.
    """
    if len(providers) <= 1:
        # Single provider — no need for thread pool overhead
        if not providers:
            return []
        req = RunTaskRequest(
            prompt=request.prompt,
            role=request.role,
            stage=request.stage,
            task_dir=request.task_dir,
            task_id=request.task_id,
            token_budget_input=request.token_budget_input,
            token_budget_output=request.token_budget_output,
            adapter_target=providers[0],
            artifacts_to_stream=request.artifacts_to_stream,
            extra=request.extra,
        )
        return [dispatch(req, use_real=use_real)]

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
        return provider, dispatch(req, use_real=use_real)

    ordered: list[tuple[str, RunTaskResult] | None] = [None] * len(providers)

    with ThreadPoolExecutor(max_workers=len(providers)) as pool:
        futures = {pool.submit(_dispatch_one, p): i for i, p in enumerate(providers)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                ordered[idx] = future.result()
            except Exception as exc:
                ordered[idx] = (providers[idx], RunTaskResult(status="failure", error=str(exc)))

    return [r for _, r in ordered if r is not None]


def _merge_token_usage(results: list[RunTaskResult]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for r in results:
        for k, v in r.token_usage.items():
            merged[k] = merged.get(k, 0) + v
    return merged


def _merge_artifacts(results: list[RunTaskResult]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for r in results:
        for a in r.artifacts_produced:
            if a not in seen:
                seen.add(a)
                merged.append(a)
    return merged


def _provider_details(results: list[RunTaskResult], providers: list[str]) -> list[dict]:
    details: list[dict] = []
    for provider, result in zip(providers, results):
        details.append({
            "provider": provider,
            "status": result.status,
            "token_usage": dict(result.token_usage),
            "error": result.error,
        })
    return details


def run_orchestration(
    request: RunTaskRequest,
    config: OrchestrationConfig,
    *,
    use_real: bool = False,
) -> OrchestrationResult:
    """Fan-out to multiple adapters and apply the configured strategy.

    Args:
        request: Original run task request (adapter_target is ignored;
            providers from config are used instead).
        config: Orchestration configuration with strategy and providers.
        use_real: Whether to use real (vs stub) adapters.

    Returns:
        OrchestrationResult with the merged/selected output.
    """
    strategy_fn = STRATEGY_REGISTRY.get(config.strategy)
    if strategy_fn is None:
        return OrchestrationResult(
            status="failure",
            error=f"Unknown strategy: {config.strategy}",
            strategy_used=config.strategy,
        )

    if config.strategy == "fastest":
        from forgeflow_runtime.orchestra.fastest import run_fastest
        return run_fastest(request, config, use_real=use_real)

    if config.strategy == "debate":
        from forgeflow_runtime.orchestra.debate import run_debate
        return run_debate(request, config, use_real=use_real)

    if config.strategy == "pipeline":
        from forgeflow_runtime.orchestra.pipeline import run_pipeline
        return run_pipeline(request, config, use_real=use_real)

    # consensus — simple fan-out + strategy merge
    results = _fan_out(request, config.providers, use_real=use_real)
    provider_results = _provider_details(results, config.providers)

    # Check for total failure
    if all(r.status in ("failure", "blocked") for r in results):
        first_error = next((r.error for r in results if r.error), "all providers failed")
        return OrchestrationResult(
            status="failure",
            error=first_error,
            strategy_used=config.strategy,
            provider_results=provider_results,
        )

    merged = strategy_fn(results)

    return OrchestrationResult(
        status=merged.status,
        raw_output=merged.raw_output,
        token_usage=_merge_token_usage(results),
        artifacts_produced=_merge_artifacts(results),
        error=merged.error,
        strategy_used=config.strategy,
        provider_results=provider_results,
    )


# --- Strategy implementations ---

from forgeflow_runtime.orchestra.consensus import consensus_merge  # noqa: E402

STRATEGY_REGISTRY: dict[str, StrategyFunc] = {
    "consensus": consensus_merge,
    "pipeline": lambda results: results[-1] if results else RunTaskResult(status="failure"),
    "debate": lambda results: results[0],  # placeholder; debate has its own path
    "fastest": lambda results: results[0],  # placeholder; fastest has its own path
}
