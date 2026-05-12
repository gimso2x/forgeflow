from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from forgeflow_runtime.executor import RunTaskRequest, RunTaskResult, dispatch
from forgeflow_runtime.generator import PromptContext, generate_prompt


def _write_worker_output(task_dir: Path, worker: dict[str, Any], result: RunTaskResult) -> None:
    output_ref = worker.get("output_ref")
    if not isinstance(output_ref, str) or not output_ref.strip():
        return
    output_path = task_dir / output_ref
    output_path.parent.mkdir(parents=True, exist_ok=True)
    owned_paths = worker.get("owned_paths") if isinstance(worker.get("owned_paths"), list) else []
    lines = [
        f"# Worker Output — {worker.get('plan_task_id', 'unknown')}",
        "",
        f"- status: {result.status}",
        f"- plan_task_id: {worker.get('plan_task_id', 'unknown')}",
        f"- worktree: {worker.get('worktree', {}).get('path') if isinstance(worker.get('worktree'), dict) else ''}",
        f"- owned_paths: {', '.join(str(path) for path in owned_paths)}",
        "",
        "## Raw Output",
        "```text",
        result.raw_output or "",
        "```",
    ]
    if result.error:
        lines.extend(["", "## Error", "```text", result.error, "```"])
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def execute_parallel_workers(
    *,
    task_dir: Path,
    task_id: str,
    route: str,
    adapter_target: str = "claude",
    workers: list[dict[str, Any]],
    use_real: bool = False,
    max_workers: int | None = None,
) -> list[dict[str, Any]]:
    """Dispatch worker tasks concurrently inside their allocated worktrees.

    Each worker dict must carry a ``worktree.path`` and ``output_ref`` produced
    by the orchestrator allocation step. The shared task workspace remains the
    source of artifacts, while the executor cwd is the worker worktree.
    """
    if not workers:
        return []

    def _run(worker: dict[str, Any]) -> dict[str, Any]:
        plan_task_id = str(worker.get("plan_task_id") or "unknown")
        worktree = worker.get("worktree") if isinstance(worker.get("worktree"), dict) else {}
        worktree_path = Path(str(worktree.get("path") or ""))
        if not worktree_path.exists():
            result = RunTaskResult(status="failure", error=f"worker worktree missing: {worktree_path}")
        else:
            worker["status"] = "in_progress"
            result = execute_stage(
                task_dir=worktree_path,
                task_id=task_id,
                stage="execute",
                route=route,
                role="worker",
                adapter_target=adapter_target,
                extra_context={
                    "task_workspace": str(task_dir),
                    "plan_task_id": plan_task_id,
                    "owned_paths": worker.get("owned_paths", []),
                    "worker_output_ref": worker.get("output_ref"),
                    "constraint": "Modify only owned_paths in this worker worktree. Do not merge.",
                },
                artifacts_to_stream=[str(worker.get("output_ref"))] if worker.get("output_ref") else None,
                use_real=use_real,
            )
        worker["status"] = "completed" if result.status == "success" else result.status
        _write_worker_output(task_dir, worker, result)
        return {"plan_task_id": plan_task_id, "worker": worker, "result": result}

    ordered: dict[str, dict[str, Any]] = {}
    count = max_workers or len(workers)
    with ThreadPoolExecutor(max_workers=max(1, count)) as pool:
        future_to_index = {pool.submit(_run, worker): index for index, worker in enumerate(workers)}
        for future in as_completed(future_to_index):
            ordered[str(future_to_index[future])] = future.result()
    return [ordered[str(index)] for index in range(len(workers))]


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

    result: RunTaskResult | None = None
    try:
        result = dispatch(request, use_real=use_real)
        return result
    finally:
        if collector is not None:
            timer.__exit__(None, None, None)
            if result is not None:
                collector.record_stage(result)
