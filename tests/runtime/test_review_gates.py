import json
from pathlib import Path

import pytest

from forgeflow_runtime.orchestrator import RuntimeViolation, advance_to_next_stage, load_runtime_policy, run_route


ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_task_dir(tmp_path: Path) -> Path:
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    _write_json(
        task_dir / "brief.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "objective": "Run a small route",
            "in_scope": ["runtime"],
            "out_of_scope": [],
            "constraints": ["local only"],
            "acceptance_criteria": ["route works"],
            "risk_level": "low",
        },
    )
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "clarify",
            "status": "in_progress",
            "completed_gates": ["clarification_complete"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "",
            "spec_review_approved": False,
            "quality_review_approved": False,
        },
    )
    return task_dir


def test_finalize_blocks_missing_review_flags(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    run_state["current_stage"] = "quality-review"
    _write_json(task_dir / "run-state.json", run_state)
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["looks fine"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )

    with pytest.raises(RuntimeViolation, match="finalize requires run-state approval flags: quality_review_approved"):
        advance_to_next_stage(task_dir=task_dir, policy=policy, route_name="small", current_stage="quality-review")


def test_run_route_rejects_non_approved_quality_review(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "review_type": "quality",
            "verdict": "changes_requested",
            "findings": ["missing verification"],
            "next_action": "execute stage evidence를 보강",
        },
    )

    with pytest.raises(RuntimeViolation, match="quality-review requires approved quality review-report artifact"):
        run_route(task_dir=task_dir, policy=policy, route_name="small")


def test_run_route_rejects_approved_review_with_open_blockers(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["looks fine"],
            "approved_by": "quality-reviewer",
            "open_blockers": ["integration evidence missing"],
            "next_action": "finalize 가능",
        },
    )

    with pytest.raises(RuntimeViolation, match="review-report.json failed schema validation: open_blockers"):
        run_route(task_dir=task_dir, policy=policy, route_name="small")


def test_run_route_rejects_approved_quality_review_marked_unsafe(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["looks fine"],
            "approved_by": "quality-reviewer",
            "safe_for_next_stage": False,
            "next_action": "finalize 보류",
        },
    )

    with pytest.raises(RuntimeViolation, match="review-report.json failed schema validation: safe_for_next_stage"):
        run_route(task_dir=task_dir, policy=policy, route_name="small")


def test_run_route_rejects_approved_spec_review_marked_unsafe(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "review_type": "spec",
            "verdict": "approved",
            "findings": ["spec is approved but rollout is still unsafe"],
            "approved_by": "spec-reviewer",
            "safe_for_next_stage": False,
            "next_action": "quality-review 보류",
        },
    )

    with pytest.raises(RuntimeViolation, match="review-report.json failed schema validation: safe_for_next_stage"):
        run_route(task_dir=task_dir, policy=policy, route_name="small")
