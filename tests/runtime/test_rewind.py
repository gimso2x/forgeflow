import json
from pathlib import Path

from jsonschema import Draft202012Validator

from forgeflow_runtime.orchestrator import load_runtime_policy, run_route, step_back


ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))


def _assert_schema_valid(name: str, payload: dict) -> None:
    errors = sorted(Draft202012Validator(_load_schema(name)).iter_errors(payload), key=lambda err: list(err.path))
    assert not errors, [f"{list(err.path)}: {err.message}" for err in errors]


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


def _write_medium_plan_artifacts(task_dir: Path, *, route_name: str = "medium") -> None:
    _write_json(
        task_dir / "plan.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "steps": [
                {
                    "id": "step-1",
                    "objective": "update workflow docs",
                    "dependencies": [],
                    "expected_output": "workflow docs reflect medium route behavior",
                    "verification": "pytest tests/runtime/test_rewind.py -q",
                    "rollback_note": "remove incomplete workflow edits if validation fails",
                }
            ],
        },
    )
    _write_json(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": route_name,
            "completed_stages": [],
            "completed_gates": [],
            "retries": {},
            "current_task_id": "task-1",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "update workflow docs",
                    "depends_on": [],
                    "files": ["docs/workflow.md"],
                    "parallel_safe": False,
                    "status": "in_progress",
                    "required_gates": ["machine", "validator"],
                    "evidence_refs": [],
                    "attempt_count": 0,
                }
            ],
        },
    )


def test_step_back_rewinds_to_previous_stage(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    state = step_back(task_dir=task_dir, policy=policy, route_name="small", current_stage="quality-review")

    assert state["current_stage"] == "execute"
    assert state["status"] == "in_progress"
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    _assert_schema_valid("checkpoint", checkpoint)
    assert checkpoint["route"] == "small"
    assert checkpoint["current_stage"] == "execute"
    assert checkpoint["next_action"] == "Resume at quality-review after reloading canonical artifacts."


def test_step_back_rewinds_plan_ledger_progress_for_medium_route(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir)
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "quality-review",
            "status": "in_progress",
            "completed_gates": ["clarification_complete"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "task-1",
            "spec_review_approved": False,
            "quality_review_approved": False,
        },
    )
    _write_json(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "completed_stages": ["clarify", "plan", "execute"],
            "completed_gates": ["clarification_complete", "plan_executable", "execution_evidenced"],
            "retries": {},
            "current_task_id": "task-1",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "update workflow docs",
                    "depends_on": [],
                    "files": ["docs/workflow.md"],
                    "parallel_safe": False,
                    "status": "in_progress",
                    "required_gates": ["machine", "validator"],
                    "evidence_refs": [
                        "run-state.json#gate:plan_executable",
                        "run-state.json#gate:execution_evidenced",
                    ],
                    "attempt_count": 0,
                }
            ],
        },
    )
    _write_json(
        task_dir / "checkpoint.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_stage": "quality-review",
            "current_task_id": "task-1",
            "plan_ref": "plan.json",
            "plan_ledger_ref": "plan-ledger.json",
            "run_state_ref": "run-state.json",
            "latest_review_ref": "review-report.json",
            "next_action": "Resume at finalize after review approval.",
            "open_blockers": [],
            "updated_at": "2026-04-22T00:00:00Z",
        },
    )
    _write_json(
        task_dir / "session-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "medium",
            "current_stage": "quality-review",
            "current_task_id": "task-1",
            "plan_ref": "plan.json",
            "plan_ledger_ref": "plan-ledger.json",
            "run_state_ref": "run-state.json",
            "latest_checkpoint_ref": "checkpoint.json",
            "latest_review_ref": "review-report.json",
            "next_action": "Resume at finalize after review approval.",
            "updated_at": "2026-04-22T00:00:00Z",
        },
    )
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

    state = step_back(task_dir=task_dir, policy=policy, route_name="medium", current_stage="quality-review")

    assert state["current_stage"] == "execute"
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    assert persisted_plan_ledger["completed_stages"] == ["clarify", "plan"]
    assert persisted_plan_ledger["completed_gates"] == ["clarification_complete", "plan_executable"]
    assert persisted_plan_ledger["tasks"][0]["evidence_refs"] == ["run-state.json#gate:plan_executable"]

    result = run_route(task_dir=task_dir, policy=policy, route_name="medium")

    assert result["current_stage"] == "finalize"
    decision_log = json.loads((task_dir / "decision-log.json").read_text(encoding="utf-8"))
    decisions = [entry["decision"] for entry in decision_log["entries"]]
    assert "step back: quality-review -> execute" in decisions
    assert decisions[-4:] == [
        "route resumed: medium from execute",
        "stage entered: execute",
        "stage entered: quality-review",
        "stage entered: finalize",
    ]


def test_step_back_large_route_preserves_spec_evidence_and_clears_quality_flag(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir, route_name="large_high_risk")
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "long-run",
            "status": "in_progress",
            "completed_gates": ["clarification_complete"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "task-1",
            "spec_review_approved": True,
            "quality_review_approved": True,
        },
    )
    _write_json(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "route": "large_high_risk",
            "completed_stages": ["clarify", "plan", "execute", "spec-review", "quality-review", "finalize"],
            "completed_gates": [
                "clarification_complete",
                "plan_executable",
                "execution_evidenced",
                "spec_review_passed",
                "quality_review_passed",
                "ready_to_finalize",
            ],
            "retries": {},
            "current_task_id": "task-1",
            "last_review_verdict": "approved",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "update workflow docs",
                    "depends_on": [],
                    "files": ["docs/workflow.md"],
                    "parallel_safe": False,
                    "status": "in_progress",
                    "required_gates": ["machine", "validator"],
                    "evidence_refs": [
                        "run-state.json#gate:plan_executable",
                        "run-state.json#gate:execution_evidenced",
                        "review-report-spec.json#verdict:approved",
                        "review-report-quality.json#verdict:approved",
                        "run-state.json#gate:quality_review_passed",
                        "run-state.json#gate:ready_to_finalize",
                        "eval-record.json#verdict:approved",
                    ],
                    "attempt_count": 1,
                }
            ],
        },
    )

    state = step_back(task_dir=task_dir, policy=policy, route_name="large_high_risk", current_stage="long-run")

    assert state["current_stage"] == "finalize"
    assert state["spec_review_approved"] is True
    assert state["quality_review_approved"] is False
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    assert "review-report-spec.json#verdict:approved" in persisted_plan_ledger["tasks"][0]["evidence_refs"]
    assert "review-report-quality.json#verdict:approved" in persisted_plan_ledger["tasks"][0]["evidence_refs"]
    assert "eval-record.json#verdict:approved" not in persisted_plan_ledger["tasks"][0]["evidence_refs"]
