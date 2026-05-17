from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from forgeflow_runtime.executor import RunTaskRequest, RunTaskResult, dispatch
from forgeflow_runtime.generator import PromptContext, generate_prompt

logger = logging.getLogger(__name__)


def _worker_artifact_dir(task_dir: Path, worker: dict[str, Any]) -> Path:
    plan_task_id = str(worker.get("plan_task_id", "")).strip().replace("/", "-").replace("\\", "-")
    if not plan_task_id:
        plan_task_id = "unknown"
    return task_dir / "workers" / plan_task_id


def _persist_worker_state(task_dir: Path, worker: dict[str, Any]) -> None:
    """Atomically write worker-state.json to disk after each worker completes."""
    artifact_dir = _worker_artifact_dir(task_dir, worker)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    state_path = artifact_dir / "worker-state.json"
    tmp_path = state_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(worker, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(state_path)


def _write_worker_output(task_dir: Path, worker: dict[str, Any], result: RunTaskResult) -> None:
    output_ref = worker.get("output_ref")
    if not isinstance(output_ref, str) or not output_ref.strip():
        return
    # Prevent path traversal — output_ref must stay under task_dir
    resolved = (task_dir / output_ref).resolve()
    if not str(resolved).startswith(str(task_dir.resolve())):
        logger.warning("worker output_ref escapes task_dir, skipping: %s", output_ref)
        return
    output_path = resolved
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
        _persist_worker_state(task_dir, worker)
        return {"plan_task_id": plan_task_id, "worker": worker, "result": result}

    ordered: dict[str, dict[str, Any]] = {}
    count = max_workers or len(workers)
    with ThreadPoolExecutor(max_workers=max(1, count)) as pool:
        future_to_index = {pool.submit(_run, worker): index for index, worker in enumerate(workers)}
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result_dict = future.result()
                ordered[str(index)] = result_dict
            except Exception as exc:
                # C1: Don't let one worker's exception kill the whole batch.
                # Record failure so the orchestrator can do partial merge.
                worker = workers[index]
                worker["status"] = "exception"
                _persist_worker_state(task_dir, worker)
                logger.error("worker %s raised: %s", worker.get("plan_task_id"), exc)
                ordered[str(index)] = {
                    "plan_task_id": str(worker.get("plan_task_id", "unknown")),
                    "worker": worker,
                    "result": RunTaskResult(status="failure", error=str(exc)),
                }
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
        assert result.execution_mode in ("stub", "real"), f"invalid execution_mode: {result.execution_mode!r}"
        return result
    finally:
        if collector is not None:
            timer.__exit__(None, None, None)
            if result is not None:
                collector.record_stage(result)
