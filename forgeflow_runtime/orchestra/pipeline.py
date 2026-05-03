"""Pipeline strategy — sequential chain where each provider refines the previous output."""

from __future__ import annotations

import logging

from forgeflow_runtime.executor import RunTaskRequest, RunTaskResult, dispatch
from forgeflow_runtime.orchestra.strategy import (
    OrchestrationConfig,
    OrchestrationResult,
    _merge_token_usage,
    _provider_details,
)

logger = logging.getLogger(__name__)


def pipeline_merge(results: list[RunTaskResult]) -> RunTaskResult:
    """Merge pipeline results — return the last successful result."""
    successful = [r for r in results if r.status == "success"]
    if successful:
        return successful[-1]
    return results[0] if results else RunTaskResult(status="failure", error="no results")


def run_pipeline(
    request: RunTaskRequest,
    config: OrchestrationConfig,
    *,
    use_real: bool = False,
) -> OrchestrationResult:
    """Sequential pipeline: each provider refines the output of the previous one.

    Provider 1 gets the original prompt.  Provider N gets the original prompt
    plus the output of Provider N-1, and is asked to refine it.
    """
    providers = config.providers
    current_prompt = request.prompt
    all_results: list[RunTaskResult] = []

    for i, provider in enumerate(providers):
        if i > 0 and current_prompt:
            # Append previous output as context for refinement
            prev_output = all_results[-1].raw_output or ""
            current_prompt = (
                f"{request.prompt}\n\n"
                f"## Previous Output (to refine)\n\n{prev_output}\n\n"
                f"## Instructions\n"
                f"Refine and improve the previous output above. Fix any issues "
                f"and enhance quality. Output the improved version."
            )

        req = RunTaskRequest(
            prompt=current_prompt,
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
        all_results.append(result)

        if result.status == "success" and result.raw_output:
            current_prompt = result.raw_output
        elif result.status in ("failure", "blocked"):
            # Pipeline breaks on failure
            break

    final = all_results[-1] if all_results else RunTaskResult(status="failure", error="no results")
    successful = [r for r in all_results if r.status == "success"]

    return OrchestrationResult(
        status=final.status,
        raw_output=final.raw_output,
        token_usage=_merge_token_usage(all_results),
        artifacts_produced=final.artifacts_produced,
        error=final.error,
        strategy_used="pipeline",
        provider_results=_provider_details(all_results, providers),
    )
