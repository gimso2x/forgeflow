"""Progress tracker for ForgeFlow plan-ledger.

Calculates task-level and overall progress, and detects early anomalies
such as excessive retries, circular dependencies, and stalled tasks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def calculate_progress(plan_ledger: dict[str, Any] | None) -> dict[str, Any]:
    """Calculate progress from plan-ledger.

    Args:
        plan_ledger: Parsed plan-ledger dict containing a ``tasks`` list,
            or ``None`` if no ledger is available.

    Returns:
        A dict with keys:
        - total_tasks (int): Total number of tasks.
        - done (int): Tasks with status ``"done"``.
        - in_progress (int): Tasks with status ``"in_progress"``.
        - pending (int): Tasks with status ``"pending"``.
        - blocked (int): Tasks with status ``"blocked"``.
        - cancelled (int): Tasks with status ``"cancelled"``.
        - percent (float): Completion percentage rounded to 1 decimal.
        - per_task (dict[str, str]): Mapping of task_id to its status.
        - next_actionable (list[str]): Task IDs whose depends_on are all
          ``"done"`` and whose own status is ``"pending"``.
    """
    empty: dict[str, Any] = {
        "total_tasks": 0,
        "done": 0,
        "in_progress": 0,
        "pending": 0,
        "blocked": 0,
        "cancelled": 0,
        "percent": 0.0,
        "per_task": {},
        "next_actionable": [],
    }

    if plan_ledger is None:
        return empty

    tasks = plan_ledger.get("tasks") or []

    per_task: dict[str, str] = {}
    task_depends_on: dict[str, list[str]] = {}

    counts: dict[str, int] = {
        "done": 0,
        "in_progress": 0,
        "pending": 0,
        "blocked": 0,
        "cancelled": 0,
    }

    for task in tasks:
        task_id = task.get("id", "")
        status = task.get("status", "pending")
        per_task[task_id] = status
        task_depends_on[task_id] = task.get("depends_on") or []
        counts[status] = counts.get(status, 0) + 1

    total = len(tasks)
    done_count = counts["done"]
    percent = round(done_count / total * 100, 1) if total > 0 else 0.0

    # Determine next actionable tasks:
    # status == "pending" AND every depends_on ID has status "done" in per_task.
    next_actionable: list[str] = []
    for task in tasks:
        task_id = task.get("id", "")
        if per_task.get(task_id) != "pending":
            continue
        deps = task_depends_on.get(task_id, [])
        if all(per_task.get(dep) == "done" for dep in deps):
            next_actionable.append(task_id)

    return {
        "total_tasks": total,
        "done": done_count,
        "in_progress": counts["in_progress"],
        "pending": counts["pending"],
        "blocked": counts["blocked"],
        "cancelled": counts["cancelled"],
        "percent": percent,
        "per_task": per_task,
        "next_actionable": next_actionable,
    }


def detect_progress_anomaly(
    plan_ledger: dict[str, Any] | None,
    run_state: dict[str, Any] | None,
) -> list[str]:
    """Detect early warning signs from plan-ledger and run-state.

    Checks performed:
    1. Any task with ``attempt_count > 3``.
    2. Any stage in run_state with retries > 2.
    3. More than 2 tasks ``"in_progress"`` simultaneously.
    4. Circular dependency hint — a blocked task whose blocker is also
       blocked and depends back on the original task.

    Args:
        plan_ledger: Parsed plan-ledger dict, or ``None``.
        run_state: Parsed run-state dict, or ``None``.

    Returns:
        A list of human-readable warning strings.  An empty list means
        no anomalies were detected.
    """
    warnings: list[str] = []

    # --- Graceful handling of None inputs ---
    tasks: list[dict[str, Any]] = []
    if plan_ledger is not None:
        tasks = plan_ledger.get("tasks") or []

    # --- Check 1: excessive attempt count ---
    for task in tasks:
        attempt_count = task.get("attempt_count", 0)
        if attempt_count > 3:
            task_id = task.get("id", "unknown")
            warnings.append(
                f"Task {task_id} has been attempted {attempt_count} times"
            )

    # --- Check 2: run-state stage retries ---
    if run_state is not None:
        retries = run_state.get("retries") or {}
        for stage, count in retries.items():
            if isinstance(count, int) and count > 2:
                warnings.append(f"Stage {stage} retried {count} times")

    # --- Check 3: too many tasks in progress ---
    in_progress_count = sum(
        1 for t in tasks if t.get("status") == "in_progress"
    )
    if in_progress_count > 2:
        warnings.append(
            f"{in_progress_count} tasks in progress simultaneously"
        )

    # --- Check 4: circular dependency hint ---
    # Build lookup: task_id -> task dict
    task_map: dict[str, dict[str, Any]] = {}
    for task in tasks:
        tid = task.get("id", "")
        if tid:
            task_map[tid] = task

    for task in tasks:
        task_id = task.get("id", "")
        status = task.get("status", "")
        if status != "blocked":
            continue

        deps = task.get("depends_on") or []
        for dep_id in deps:
            dep_task = task_map.get(dep_id)
            if dep_task is None:
                continue
            if dep_task.get("status") != "blocked":
                continue
            # The dependency is also blocked — check if it depends back.
            dep_deps = dep_task.get("depends_on") or []
            if task_id in dep_deps:
                warnings.append(
                    f"Circular dependency suspected between {task_id} and {dep_id}"
                )

    return warnings


def load_progress_report(task_dir: Path) -> dict[str, Any]:
    """Load plan-ledger and run-state from *task_dir* and return a combined report.

    Reads ``plan-ledger.json`` and ``run-state.json`` from *task_dir*, computes
    progress metrics and anomaly warnings, and returns everything in a single
    dict.

    Args:
        task_dir: Directory containing the plan-ledger and run-state files.

    Returns:
        A dict with keys ``"progress"`` (output of :func:`calculate_progress`)
        and ``"warnings"`` (output of :func:`detect_progress_anomaly`).
    """
    task_dir = Path(task_dir)

    # --- Load plan-ledger ---
    plan_ledger_path = task_dir / "plan-ledger.json"
    plan_ledger: dict[str, Any] | None = None
    if plan_ledger_path.is_file():
        try:
            plan_ledger = json.loads(plan_ledger_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            plan_ledger = None

    # --- Load run-state ---
    run_state_path = task_dir / "run-state.json"
    run_state: dict[str, Any] | None = None
    if run_state_path.is_file():
        try:
            run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            run_state = None

    progress = calculate_progress(plan_ledger)
    warnings = detect_progress_anomaly(plan_ledger, run_state)

    return {
        "progress": progress,
        "warnings": warnings,
    }
