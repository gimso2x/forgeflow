import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from forgeflow_runtime.orchestrator import (
    RuntimeViolation,
    advance_to_next_stage,
    escalate_route,
    load_runtime_policy,
    resume_task,
    retry_stage,
    run_route,
    status_summary,
)
from forgeflow_runtime.generator import GenerationError


ROOT = Path(__file__).resolve().parents[1]


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


def test_advance_blocks_missing_entry_artifacts(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir, route_name="large_high_risk")
    (task_dir / "run-state.json").unlink()

    with pytest.raises(RuntimeViolation, match="missing required artifacts for spec-review: run-state"):
        advance_to_next_stage(task_dir=task_dir, policy=policy, route_name="large_high_risk", current_stage="execute")


def test_run_route_requires_plan_ledger_for_medium_route(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
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
                    "verification": "pytest tests/test_runtime_orchestrator.py -q",
                    "rollback_note": "remove incomplete workflow edits if validation fails",
                }
            ],
        },
    )

    with pytest.raises(RuntimeViolation, match="medium route requires plan-ledger.json"):
        run_route(task_dir=task_dir, policy=policy, route_name="medium")


def test_advance_requires_plan_ledger_for_medium_route(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
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
                    "verification": "pytest tests/test_runtime_orchestrator.py -q",
                    "rollback_note": "remove incomplete workflow edits if validation fails",
                }
            ],
        },
    )
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    run_state["current_stage"] = "plan"
    _write_json(task_dir / "run-state.json", run_state)

    with pytest.raises(RuntimeViolation, match="medium route requires plan-ledger.json"):
        advance_to_next_stage(task_dir=task_dir, policy=policy, route_name="medium", current_stage="plan")


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
                    "verification": "pytest tests/test_runtime_orchestrator.py -q",
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


def test_run_route_syncs_current_task_from_plan_ledger(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir)
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

    result = run_route(task_dir=task_dir, policy=policy, route_name="medium")

    assert result["current_stage"] == "finalize"
    assert result["current_task_id"] == "task-1"
    persisted_run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert persisted_run_state["current_task_id"] == "task-1"
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    assert persisted_plan_ledger["tasks"][0]["status"] == "done"
    assert persisted_plan_ledger["tasks"][0]["attempt_count"] == 1
    assert persisted_plan_ledger["completed_stages"] == ["clarify", "plan", "execute", "quality-review", "finalize"]
    assert persisted_plan_ledger["completed_gates"] == [
        "clarification_complete",
        "plan_executable",
        "execution_evidenced",
        "quality_review_passed",
        "ready_to_finalize",
    ]
    assert "run-state.json#gate:plan_executable" in persisted_plan_ledger["tasks"][0]["evidence_refs"]
    assert "review-report.json#verdict:approved" in persisted_plan_ledger["tasks"][0]["evidence_refs"]
    assert persisted_plan_ledger["last_review_verdict"] == "approved"
    assert persisted_run_state["completed_gates"] == ["clarification_complete"]


def test_retry_stage_updates_plan_ledger_attempts(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir)

    result = retry_stage(task_dir=task_dir, stage_name="execute", max_retries=2)

    assert result["retries"]["execute"] == 1
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    persisted_run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert persisted_plan_ledger["tasks"][0]["attempt_count"] == 1
    assert persisted_plan_ledger["tasks"][0]["status"] == "in_progress"
    assert persisted_plan_ledger["retries"] == {"execute": 1}
    assert persisted_run_state["retries"] == {}


def test_advance_updates_plan_ledger_gate_evidence(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir)
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    run_state["current_stage"] = "plan"
    _write_json(task_dir / "run-state.json", run_state)

    result = advance_to_next_stage(task_dir=task_dir, policy=policy, route_name="medium", current_stage="plan")

    assert result.next_stage == "execute"
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    persisted_run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert persisted_plan_ledger["tasks"][0]["status"] == "in_progress"
    assert persisted_plan_ledger["completed_stages"] == ["plan"]
    assert persisted_plan_ledger["completed_gates"] == ["plan_executable"]
    assert "run-state.json#gate:plan_executable" in persisted_plan_ledger["tasks"][0]["evidence_refs"]
    assert persisted_run_state["completed_gates"] == ["clarification_complete"]


def test_advance_can_execute_next_stage_immediately(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir)
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    run_state["current_stage"] = "plan"
    _write_json(task_dir / "run-state.json", run_state)

    result = advance_to_next_stage(
        task_dir=task_dir,
        policy=policy,
        route_name="medium",
        current_stage="plan",
        execute_immediately=True,
        adapter_target="codex",
    )

    assert result.next_stage == "execute"
    assert result.execution is not None
    assert result.execution["stage"] == "execute"
    assert result.execution["adapter"] == "codex"
    assert result.execution["status"] == "success"
    assert (task_dir / "execute-output.md").exists()
    assert "stub-codex-output" in (task_dir / "execute-output.md").read_text(encoding="utf-8")


def test_advance_execute_failure_keeps_previous_stage_state(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir)
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    run_state["current_stage"] = "plan"
    _write_json(task_dir / "run-state.json", run_state)

    with pytest.raises(GenerationError, match="unknown role: nonexistent-role"):
        advance_to_next_stage(
            task_dir=task_dir,
            policy=policy,
            route_name="medium",
            current_stage="plan",
            execute_immediately=True,
            role="nonexistent-role",
        )

    persisted_run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert persisted_run_state["current_stage"] == "plan"
    persisted_plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    assert persisted_plan_ledger["completed_stages"] == []
    assert not (task_dir / "execute-output.md").exists()



def test_run_route_rejects_medium_plan_ledger_out_of_order_completed_stages(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = _make_task_dir(tmp_path)
    _write_medium_plan_artifacts(task_dir, route_name="medium")
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    run_state["current_stage"] = "execute"
    _write_json(task_dir / "run-state.json", run_state)
    plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text(encoding="utf-8"))
    plan_ledger["completed_stages"] = ["clarify", "plan", "quality-review"]
    plan_ledger["completed_gates"] = ["clarification_complete", "plan_executable"]
    _write_json(task_dir / "plan-ledger.json", plan_ledger)
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

    with pytest.raises(RuntimeViolation, match="plan-ledger checkpoint has out-of-sequence completed stages at execute: quality-review"):
        run_route(task_dir=task_dir, policy=policy, route_name="medium")


def test_small_route_runs_end_to_end_and_updates_state(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
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

    result = run_route(task_dir=task_dir, policy=policy, route_name="small")

    assert result["current_stage"] == "finalize"
    assert result["status"] == "completed"
    assert result["final_status"] == "success"
    assert result["completed_gates"] == [
        "clarification_complete",
        "execution_evidenced",
        "quality_review_passed",
        "ready_to_finalize",
    ]
    _assert_schema_valid("run-state", result)

    decision_log = json.loads((task_dir / "decision-log.json").read_text(encoding="utf-8"))
    _assert_schema_valid("decision-log", decision_log)
    decisions = [entry["decision"] for entry in decision_log["entries"]]
    assert decisions == [
        "route selected: small",
        "stage entered: clarify",
        "stage entered: execute",
        "stage entered: quality-review",
        "stage entered: finalize",
    ]


def test_large_route_runs_end_to_end_and_collects_both_review_flags(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = tmp_path / "large-task"
    task_dir.mkdir()
    _write_json(
        task_dir / "brief.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-001",
            "objective": "Run a large route",
            "in_scope": ["runtime"],
            "out_of_scope": [],
            "constraints": ["local only"],
            "acceptance_criteria": ["large route works"],
            "risk_level": "high",
        },
    )
    _write_json(
        task_dir / "plan.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-001",
            "steps": [
                {
                    "id": "step-1",
                    "objective": "Run route",
                    "expected_output": "done",
                    "verification": "pytest",
                }
            ],
        },
    )
    _write_json(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-001",
            "route": "large_high_risk",
            "current_task_id": "task-1",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "Run route",
                    "depends_on": [],
                    "files": ["plan.json", "review-report-spec.json", "review-report-quality.json", "eval-record.json"],
                    "parallel_safe": False,
                    "status": "in_progress",
                    "required_gates": ["machine", "validator", "scenario"],
                    "evidence_refs": [],
                    "attempt_count": 0
                }
            ]
        },
    )
    _write_json(
        task_dir / "review-report-spec.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-001",
            "review_type": "spec",
            "verdict": "approved",
            "findings": ["spec ok"],
            "approved_by": "spec-reviewer",
            "next_action": "quality-review로 진행",
        },
    )
    _write_json(
        task_dir / "review-report-quality.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["quality ok"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )
    _write_json(
        task_dir / "eval-record.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-001",
            "outcome": "success",
            "what_worked": ["route worked"],
            "what_failed": [],
        },
    )

    result = run_route(task_dir=task_dir, policy=policy, route_name="large_high_risk")

    assert result["current_stage"] == "long-run"
    assert result["status"] == "completed"
    assert result["final_status"] == "success"
    assert result["spec_review_approved"] is True
    assert result["quality_review_approved"] is True
    assert result["completed_gates"] == [
        "clarification_complete",
        "plan_executable",
        "execution_evidenced",
        "spec_review_passed",
        "quality_review_passed",
        "ready_to_finalize",
        "worth_long_run_capture",
    ]


def test_large_route_rejects_missing_eval_record_before_long_run(tmp_path: Path) -> None:
    policy = load_runtime_policy(ROOT)
    task_dir = tmp_path / "large-task-missing-eval"
    task_dir.mkdir()
    _write_json(
        task_dir / "brief.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-002",
            "objective": "Run a large route",
            "in_scope": ["runtime"],
            "out_of_scope": [],
            "constraints": ["local only"],
            "acceptance_criteria": ["large route works"],
            "risk_level": "high",
        },
    )
    _write_json(
        task_dir / "plan.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-002",
            "steps": [
                {
                    "id": "step-1",
                    "objective": "Run route",
                    "expected_output": "done",
                    "verification": "pytest",
                }
            ],
        },
    )
    _write_json(
        task_dir / "plan-ledger.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-002",
            "route": "large_high_risk",
            "current_task_id": "task-1",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "Run route",
                    "depends_on": [],
                    "files": ["plan.json", "review-report-spec.json", "review-report-quality.json", "eval-record.json"],
                    "parallel_safe": False,
                    "status": "in_progress",
                    "required_gates": ["machine", "validator", "scenario"],
                    "evidence_refs": [],
                    "attempt_count": 0
                }
            ]
        },
    )
    _write_json(
        task_dir / "review-report-spec.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-002",
            "review_type": "spec",
            "verdict": "approved",
            "findings": ["spec ok"],
            "approved_by": "spec-reviewer",
            "next_action": "quality-review로 진행",
        },
    )
    _write_json(
        task_dir / "review-report-quality.json",
        {
            "schema_version": "0.1",
            "task_id": "task-large-002",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["quality ok"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )

    with pytest.raises(RuntimeViolation, match="long-run requires artifacts satisfying gate worth_long_run_capture: eval-record"):
        run_route(task_dir=task_dir, policy=policy, route_name="large_high_risk")



def test_escalate_route_switches_to_large_high_risk(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    state = escalate_route(task_dir=task_dir, from_route="small")

    assert state["status"] == "blocked"
    assert state["current_stage"] == "clarify"
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    _assert_schema_valid("checkpoint", checkpoint)
    assert checkpoint["route"] == "large_high_risk"
    assert checkpoint["current_stage"] == "clarify"
    assert checkpoint["next_action"] == "Resume at plan after reloading canonical artifacts."

    decision_log = json.loads((task_dir / "decision-log.json").read_text(encoding="utf-8"))
    assert decision_log["entries"][-1]["decision"] == "route escalated: small -> large_high_risk"
