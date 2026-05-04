from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from forgeflow_runtime.executor import RunTaskRequest, RunTaskResult, dispatch
from forgeflow_runtime.generator import PromptContext, generate_prompt


def execute_stage(
    *,
    task_dir: Path,
    task_id: str,
    stage: str,
    route: str,
    role: str,
    adapter_target: str = "claude",
    extra_context: dict[str, Any] | None = None,
    artifacts_to_stream: list[str] | None = None,
    use_real: bool = False,
    collector: Any | None = None,
) -> RunTaskResult:
    """Wire prompt generation -> executor dispatch for a single stage.

    This is the runtime glue between the orchestrator (which decides *when*
    a stage runs) and the adapter target (which performs the actual work).

    If *collector* is provided (a :class:`~forgeflow_runtime.profiling.ProfilingCollector`),
    stage timing and token/cost metrics are recorded automatically.
    """
    ctx = PromptContext(
        role=role,
        stage=stage,
        route=route,
        task_dir=task_dir,
        task_id=task_id,
        extra_context=extra_context,
    )
    prompt = generate_prompt(ctx)

    request = RunTaskRequest(
        prompt=prompt.system_prompt + "\n\n" + prompt.task_prompt,
        role=role,
        stage=stage,
        task_dir=task_dir,
        task_id=task_id,
        token_budget_input=prompt.token_budget["input"],
        token_budget_output=prompt.token_budget["output"],
        adapter_target=adapter_target,
        artifacts_to_stream=artifacts_to_stream,
        extra=extra_context,
    )

    if collector is not None:
        timer = collector.stage(stage, model=adapter_target)
        timer.__enter__()

    try:
        result = dispatch(request, use_real=use_real)
    finally:
        if collector is not None:
            timer.__exit__(None, None, None)
            collector.record_stage(result)

    return result
