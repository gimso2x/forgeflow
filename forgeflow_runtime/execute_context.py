from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forgeflow_runtime.plan_ledger import current_plan_task


def _load_plan_ledger(task_dir: Path) -> dict[str, Any] | None:
    """Load plan-ledger.json from *task_dir* if it exists, else return None."""
    ledger_path = task_dir / "plan-ledger.json"
    if not ledger_path.is_file():
        return None
    return json.loads(ledger_path.read_text(encoding="utf-8"))


def _empty_context() -> dict[str, Any]:
    """Return the canonical empty context when there is no current task."""
    return {
        "current_task": None,
        "ready_to_work": False,
        "blocked_by": [],
        "files_to_edit": [],
        "gates_needed": [],
        "attempt_count": 0,
        "progress_summary": "",
        "task_index": "",
    }


def build_execute_context(task_dir: Path) -> dict[str, Any]:
    """Build execution context from plan-ledger's current task.

    Returns a dict with:
    - current_task: the full task dict from plan-ledger (or None)
    - ready_to_work: True if all depends_on tasks are "done"
    - blocked_by: list of task IDs that are not yet done (blocking current)
    - files_to_edit: list of file paths from the current task
    - gates_needed: list of required gates
    - attempt_count: how many times this task has been attempted
    - progress_summary: human-readable one-liner like "T2/5 — sector_rotation fix"
    - task_index: "T{i}/{total}" string
    """
    plan_ledger = _load_plan_ledger(task_dir)
    if plan_ledger is None:
        return _empty_context()

    task = current_plan_task(plan_ledger)
    if task is None:
        return _empty_context()

    tasks = plan_ledger.get("tasks", [])
    total = len(tasks)

    # 1-based index of the current task within the tasks array.
    idx = 0
    for i, t in enumerate(tasks, start=1):
        if t.get("id") == task.get("id"):
            idx = i
            break

    task_index = f"T{idx}/{total}" if idx else ""

    # Determine blocking dependencies.
    depends_on: list[str] = task.get("depends_on", []) or []
    task_status_map: dict[str, str] = {
        t.get("id", ""): t.get("status", "pending") for t in tasks
    }
    blocked_by = [dep_id for dep_id in depends_on if task_status_map.get(dep_id) != "done"]
    ready_to_work = len(blocked_by) == 0

    # Build a human-readable progress summary.
    title = task.get("title", "")
    progress_summary = f"{task_index} — {title}" if task_index and title else task_index

    return {
        "current_task": task,
        "ready_to_work": ready_to_work,
        "blocked_by": blocked_by,
        "files_to_edit": list(task.get("files", []) or []),
        "gates_needed": list(task.get("required_gates", []) or []),
        "attempt_count": int(task.get("attempt_count", 0)),
        "progress_summary": progress_summary,
        "task_index": task_index,
    }


def format_execute_prompt(context: dict[str, Any]) -> str:
    """Format the execute context into a prompt string for the agent.

    Produces a clear multi-line summary such as::

        ## Current Task: T2/5 — Fix sector_rotation selection
        **Files**: backend/reporting_watchlist.py
        **Gates**: machine, validator
        **Attempt**: 3
        **Status**: ready / blocked by [T1]
    """
    task = context.get("current_task")
    if task is None:
        return "## No current task — plan-ledger is empty or all tasks complete."

    lines: list[str] = []

    # Header line.
    title = task.get("title", "untitled")
    task_index = context.get("task_index", "")
    header = f"## Current Task: {task_index} — {title}" if task_index else f"## Current Task: {title}"
    lines.append(header)

    # Files.
    files = context.get("files_to_edit", [])
    if files:
        lines.append(f"**Files**: {', '.join(files)}")
    else:
        lines.append("**Files**: (none specified)")

    # Gates.
    gates = context.get("gates_needed", [])
    if gates:
        lines.append(f"**Gates**: {', '.join(gates)}")
    else:
        lines.append("**Gates**: (none)")

    # Attempt count.
    attempt = context.get("attempt_count", 0)
    lines.append(f"**Attempt**: {attempt}")

    # Status — ready or blocked.
    if context.get("ready_to_work"):
        lines.append("**Status**: ready")
    else:
        blocked_by = context.get("blocked_by", [])
        if blocked_by:
            lines.append(f"**Status**: blocked by {blocked_by}")
        else:
            lines.append("**Status**: blocked")

    # Evidence refs (helpful context for the agent).
    evidence_refs = task.get("evidence_refs", []) or []
    if evidence_refs:
        lines.append(f"**Evidence**: {', '.join(evidence_refs)}")

    return "\n".join(lines)
