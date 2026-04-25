from __future__ import annotations

from pathlib import Path

from forgeflow_runtime.artifact_validation import artifact_path, load_validated_artifact
from forgeflow_runtime.errors import RuntimeViolation


def canonical_task_id(task_dir: Path) -> str:
    """Resolve the canonical task_id from task artifacts.

    brief.json is the preferred source of truth when present. If both brief.json
    and run-state.json exist, they must agree before either value is trusted.
    """
    brief_payload: dict | None = None
    run_state_payload: dict | None = None

    brief_path = artifact_path(task_dir, "brief")
    if brief_path.exists():
        brief_payload = load_validated_artifact(task_dir, "brief")
    run_state_path = artifact_path(task_dir, "run-state")
    if run_state_path.exists():
        run_state_payload = load_validated_artifact(task_dir, "run-state")

    if brief_payload is not None and run_state_payload is not None:
        brief_task_id = brief_payload["task_id"]
        run_state_task_id = run_state_payload["task_id"]
        if brief_task_id != run_state_task_id:
            raise RuntimeViolation(
                f"run-state.json task_id {run_state_task_id} does not match canonical task_id {brief_task_id}"
            )
        return brief_task_id
    if brief_payload is not None:
        return brief_payload["task_id"]
    if run_state_payload is not None:
        return run_state_payload["task_id"]
    raise RuntimeViolation("task directory must contain brief.json or run-state.json")


def task_id(task_dir: Path) -> str:
    return canonical_task_id(task_dir)
