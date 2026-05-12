"""Shared test helpers for runtime tests."""
from __future__ import annotations

import json
from pathlib import Path


def write_json_file(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def small_task_dir(tmp_path: Path, *, task_id: str = "task-001") -> Path:
    """Create a minimal small-route task dir (brief + run-state) for tests that
    need an existing task directory without going through init_task."""
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    write_json_file(
        task_dir / "brief.json",
        {
            "schema_version": "0.1",
            "task_id": task_id,
            "objective": "Run a small route",
            "in_scope": ["runtime"],
            "out_of_scope": [],
            "constraints": ["local only"],
            "acceptance_criteria": ["route works"],
            "risk_level": "low",
        },
    )
    write_json_file(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": task_id,
            "current_stage": "clarify",
            "status": "in_progress",
            "completed_gates": [],
            "failed_gates": [],
            "retries": {},
            "evidence_refs": [],
            "current_task_id": "",
            "spec_review_approved": False,
            "quality_review_approved": False,
        },
    )
    return task_dir


def medium_task_dir(tmp_path: Path, *, task_id: str = "task-001", route_name: str = "medium") -> Path:
    """Create a medium-route task dir with brief, run-state, plan, plan-ledger."""
    task_dir = small_task_dir(tmp_path, task_id=task_id)
    write_json_file(
        task_dir / "plan.json",
        {
            "schema_version": "0.1",
            "task_id": task_id,
            "steps": [
                {
                    "id": "step-1",
                    "objective": "do something",
                    "dependencies": [],
                    "expected_output": "done",
                    "verification": "pytest -q",
                    "rollback_note": "revert",
                    "fulfills": ["done"],
                }
            ],
            "verify_plan": [],
        },
    )
    write_json_file(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": task_id,
            "route": route_name,
            "completed_stages": [],
            "completed_gates": [],
            "retries": {},
            "current_task_id": "task-1",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "do something",
                    "depends_on": [],
                    "files": [],
                    "parallel_safe": False,
                    "status": "in_progress",
                    "required_gates": ["validator"],
                    "evidence_refs": [],
                    "attempt_count": 0,
                }
            ],
        },
    )
    return task_dir


def add_checkpoint_and_session(
    task_dir: Path,
    *,
    route_name: str,
    task_id: str = "task-001",
    current_stage: str = "clarify",
    plan_ledger: bool = False,
) -> None:
    """Add checkpoint.json and session-state.json for resume tests."""
    write_json_file(
        task_dir / "checkpoint.json",
        {
            "schema_version": "0.1",
            "task_id": task_id,
            "route": route_name,
            "current_stage": current_stage,
            "plan_ref": "plan.json" if plan_ledger else "brief.json",
            "plan_ledger_ref": "plan-ledger.json" if plan_ledger else "run-state.json",
            "run_state_ref": "run-state.json",
            "next_action": f"Resume at {current_stage}.",
            "open_blockers": [],
            "updated_at": "2026-01-01T00:00:00Z",
        },
    )
    write_json_file(
        task_dir / "session-state.json",
        {
            "schema_version": "0.1",
            "task_id": task_id,
            "route": route_name,
            "current_stage": current_stage,
            "plan_ref": "plan.json" if plan_ledger else "brief.json",
            "plan_ledger_ref": "plan-ledger.json" if plan_ledger else "run-state.json",
            "run_state_ref": "run-state.json",
            "latest_checkpoint_ref": "checkpoint.json",
            "next_action": f"Resume at {current_stage}.",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    )
