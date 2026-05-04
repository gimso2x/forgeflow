"""Tests for forgeflow_runtime/orchestrator.py — public API + internal helpers."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.executor import RunTaskResult
from forgeflow_runtime.orchestrator import (
    TransitionResult,
    _artifact_ref_path,
    _execution_payload,
    _infer_route_for_recovery,
    _resolve_route,
    _validate_review_semantics,
    advance_to_next_stage,
    escalate_route,
    init_task,
    resume_task,
    retry_stage,
    start_task,
    status_summary,
    step_back,
)
from forgeflow_runtime.policy_loader import RuntimePolicy, load_runtime_policy

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def policy() -> RuntimePolicy:
    return load_runtime_policy(REPO_ROOT)


def _json_dump(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _small_task_dir(tmp_path: Path, *, task_id: str = "task-001") -> Path:
    """Create a minimal small-route task dir (brief + run-state) for tests that
    need an existing task directory without going through init_task."""
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    _json_dump(
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
    _json_dump(
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


def _medium_task_dir(tmp_path: Path, *, task_id: str = "task-001", route_name: str = "medium") -> Path:
    """Create a medium-route task dir with brief, run-state, plan, plan-ledger."""
    task_dir = _small_task_dir(tmp_path, task_id=task_id)
    _json_dump(
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
    _json_dump(
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


def _add_checkpoint_and_session(
    task_dir: Path,
    *,
    route_name: str,
    task_id: str = "task-001",
    current_stage: str = "clarify",
    plan_ledger: bool = False,
) -> None:
    """Add checkpoint.json and session-state.json for resume tests."""
    _json_dump(
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
    _json_dump(
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


# =========================================================================
# 1–5: init_task tests
# =========================================================================


class TestInitTask:
    def test_init_task_small_route(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "small-task"
        result = init_task(task_dir, policy, task_id="t-01", objective="do it", risk_level="low")

        assert result["route"] == "small"
        assert result["task_id"] == "t-01"
        for name in ["brief.json", "run-state.json", "checkpoint.json", "session-state.json"]:
            assert (task_dir / name).exists(), f"{name} missing"

        # verify brief
        brief = json.loads((task_dir / "brief.json").read_text())
        assert brief["task_id"] == "t-01"
        assert brief["risk_level"] == "low"

        # verify run-state current_stage is first stage of small route
        run_state = json.loads((task_dir / "run-state.json").read_text())
        small_stages = _resolve_route(policy, "small")
        assert run_state["current_stage"] == small_stages[0]

    def test_init_task_medium_route(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "medium-task"
        result = init_task(task_dir, policy, task_id="t-02", objective="medium scope", risk_level="medium")

        assert result["route"] == "medium"
        assert result["task_id"] == "t-02"
        for name in ["brief.json", "run-state.json", "checkpoint.json", "session-state.json"]:
            assert (task_dir / name).exists(), f"{name} missing"

        run_state = json.loads((task_dir / "run-state.json").read_text())
        medium_stages = _resolve_route(policy, "medium")
        assert run_state["current_stage"] == medium_stages[0]

    def test_init_task_rejects_existing_artifacts(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "task"
        task_dir.mkdir()
        (task_dir / "brief.json").write_text("{}")

        with pytest.raises(RuntimeViolation, match="init refuses to overwrite"):
            init_task(task_dir, policy, task_id="t-01", objective="x", risk_level="low")

    def test_init_task_invalid_risk_level(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "task"
        with pytest.raises(RuntimeViolation, match="unknown risk level"):
            init_task(task_dir, policy, task_id="t-01", objective="x", risk_level="critical")

    def test_init_task_creates_valid_checkpoint_and_session(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        """Verify checkpoint and session-state have correct route/stage refs."""
        task_dir = tmp_path / "small-task"
        init_task(task_dir, policy, task_id="t-chk", objective="x", risk_level="low")

        checkpoint = json.loads((task_dir / "checkpoint.json").read_text())
        session = json.loads((task_dir / "session-state.json").read_text())
        assert checkpoint["route"] == "small"
        assert session["route"] == "small"
        assert session["latest_checkpoint_ref"] == "checkpoint.json"
        assert session["run_state_ref"] == "run-state.json"


# =========================================================================
# 6–8: start_task tests
# =========================================================================


class TestStartTask:
    def test_start_task_small_route(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "my-task"
        result = start_task(task_dir, policy, "small")

        assert result["route"] == "small"
        assert "brief.json" in result["created_artifacts"]
        assert "run-state.json" in result["created_artifacts"]
        assert "checkpoint.json" in result["created_artifacts"]
        assert "session-state.json" in result["created_artifacts"]
        assert "decision-log.json" in result["created_artifacts"]
        # small route should NOT have plan/plan-ledger
        assert "plan.json" not in result["created_artifacts"]
        assert "plan-ledger.json" not in result["created_artifacts"]

        run_state = json.loads((task_dir / "run-state.json").read_text())
        small_stages = _resolve_route(policy, "small")
        assert run_state["current_stage"] == small_stages[0]

    def test_start_task_medium_route(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "med-task"
        result = start_task(task_dir, policy, "medium")

        assert result["route"] == "medium"
        assert "plan.json" in result["created_artifacts"]
        assert "plan-ledger.json" in result["created_artifacts"]

        plan_ledger = json.loads((task_dir / "plan-ledger.json").read_text())
        assert plan_ledger["route"] == "medium"

    def test_start_task_rejects_existing_files(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "task"
        task_dir.mkdir()
        (task_dir / "brief.json").write_text("{}")

        with pytest.raises(RuntimeViolation, match="start requires an empty"):
            start_task(task_dir, policy, "small")


# =========================================================================
# 9–11: resume_task tests
# =========================================================================


class TestResumeTask:
    def test_resume_task_basic(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        """resume_task succeeds after start_task on a small route."""
        task_dir = tmp_path / "resume-task"
        start_task(task_dir, policy, "small")

        result = resume_task(task_dir, policy, "small")

        assert result["route"] == "small"
        assert result["current_stage"] == _resolve_route(policy, "small")[0]
        assert "next_action" in result

    def test_resume_task_missing_checkpoint(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = _small_task_dir(tmp_path)
        # checkpoint is missing
        with pytest.raises(RuntimeViolation, match="resume requires checkpoint"):
            resume_task(task_dir, policy, "small")

    def test_resume_task_missing_session_state(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = _small_task_dir(tmp_path)
        _add_checkpoint_and_session(task_dir, route_name="small")
        # remove session-state
        (task_dir / "session-state.json").unlink()

        with pytest.raises(RuntimeViolation, match="resume requires session-state"):
            resume_task(task_dir, policy, "small")


# =========================================================================
# 12: status_summary
# =========================================================================


class TestStatusSummary:
    def test_status_summary_returns_expected_fields(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "status-task"
        start_task(task_dir, policy, "small")

        result = status_summary(task_dir, policy, "small")

        for field in ["task_id", "route", "current_stage", "current_task_id",
                      "open_blockers", "required_gates", "latest_review_verdict", "next_action"]:
            assert field in result, f"missing field: {field}"
        assert result["route"] == "small"
        assert isinstance(result["required_gates"], list)
        assert isinstance(result["open_blockers"], list)


# =========================================================================
# 13–14: step_back
# =========================================================================


class TestStepBack:
    def test_step_back_basic(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        """step_back moves to previous stage and clears review flags."""
        task_dir = tmp_path / "step-task"
        start_task(task_dir, policy, "small")
        small_stages = _resolve_route(policy, "small")
        # Advance to stage index 1 (execute for small route)
        result = advance_to_next_stage(
            task_dir, policy, "small", small_stages[0],
        )
        assert result.next_stage == small_stages[1]

        # Now set some review flags and step back
        run_state = json.loads((task_dir / "run-state.json").read_text())
        run_state["spec_review_approved"] = True
        run_state["quality_review_approved"] = True
        _json_dump(task_dir / "run-state.json", run_state)

        stepped = step_back(task_dir, policy, "small", small_stages[1])
        assert stepped["current_stage"] == small_stages[0]
        assert stepped["status"] == "in_progress"
        # quality_review should be cleared since quality-review was removed
        assert stepped["quality_review_approved"] is False

    def test_step_back_first_stage_raises(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "step-first"
        start_task(task_dir, policy, "small")
        small_stages = _resolve_route(policy, "small")

        with pytest.raises(RuntimeViolation, match="cannot step back before first stage"):
            step_back(task_dir, policy, "small", small_stages[0])


# =========================================================================
# 15–16: escalate_route
# =========================================================================


class TestEscalateRoute:
    def test_escalate_route_basic(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "esc-task"
        start_task(task_dir, policy, "small")

        result = escalate_route(task_dir, "small")

        assert result["current_stage"] == "clarify"
        assert result["status"] == "blocked"

    def test_escalate_route_invalid_from(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "esc-task"
        start_task(task_dir, policy, "small")

        with pytest.raises(RuntimeViolation, match="unknown route for escalation"):
            escalate_route(task_dir, "nonexistent")


# =========================================================================
# 17–18: retry_stage
# =========================================================================


class TestRetryStage:
    def test_retry_stage_basic(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "retry-task"
        start_task(task_dir, policy, "small")
        small_stages = _resolve_route(policy, "small")

        result = retry_stage(task_dir, small_stages[1], max_retries=2)

        assert result["retries"].get(small_stages[1]) == 1
        assert result["current_stage"] == small_stages[1]
        assert result["status"] == "in_progress"

    def test_retry_stage_exceeds_budget(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        task_dir = tmp_path / "retry-max-task"
        start_task(task_dir, policy, "small")
        small_stages = _resolve_route(policy, "small")

        # Exhaust retries
        retry_stage(task_dir, small_stages[1], max_retries=2)
        retry_stage(task_dir, small_stages[1], max_retries=2)

        with pytest.raises(RuntimeViolation, match="retry budget exceeded"):
            retry_stage(task_dir, small_stages[1], max_retries=2)


# =========================================================================
# 19–21: _infer_route_for_recovery
# =========================================================================


class TestInferRouteForRecovery:
    def test_uses_plan_ledger(self) -> None:
        plan_ledger = {"route": "medium"}
        checkpoint = {"route": "medium"}
        assert _infer_route_for_recovery(
            checkpoint=checkpoint, plan_ledger=plan_ledger, fallback_route="small"
        ) == "medium"

    def test_falls_back_to_checkpoint(self) -> None:
        plan_ledger = None
        checkpoint = {"route": "small"}
        assert _infer_route_for_recovery(
            checkpoint=checkpoint, plan_ledger=plan_ledger, fallback_route="medium"
        ) == "small"

    def test_conflict_raises(self) -> None:
        plan_ledger = {"route": "medium"}
        checkpoint = {"route": "small"}
        with pytest.raises(RuntimeViolation, match="does not match canonical route"):
            _infer_route_for_recovery(
                checkpoint=checkpoint, plan_ledger=plan_ledger, fallback_route="small"
            )


# =========================================================================
# 22: _execution_payload format
# =========================================================================


class TestExecutionPayload:
    def test_execution_payload_format(self) -> None:
        result = RunTaskResult(
            status="success",
            artifacts_produced=["plan.json"],
            token_usage={"prompt": 100, "completion": 50},
            raw_output="done",
            error=None,
        )
        payload = _execution_payload(
            stage="execute", role="coder", adapter="claude", result=result, use_real=True
        )
        assert payload["stage"] == "execute"
        assert payload["role"] == "coder"
        assert payload["adapter"] == "claude"
        assert payload["execution_mode"] == "real"
        assert payload["status"] == "success"
        assert payload["artifacts_produced"] == ["plan.json"]
        assert payload["token_usage"] == {"prompt": 100, "completion": 50}
        assert "error" not in payload

    def test_execution_payload_includes_error(self) -> None:
        result = RunTaskResult(
            status="failure",
            artifacts_produced=[],
            token_usage={},
            error="timeout",
        )
        payload = _execution_payload(
            stage="clarify", role="planner", adapter="codex", result=result
        )
        assert payload["error"] == "timeout"
        assert payload["execution_mode"] == "stub"


# =========================================================================
# 23–24: _artifact_ref_path
# =========================================================================


class TestArtifactRefPath:
    def test_validates_absolute(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeViolation, match="must be task-relative"):
            _artifact_ref_path(
                tmp_path, "/etc/passwd", source_name="test.json", field_name="ref"
            )

    def test_validates_escape(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeViolation, match="escapes task directory"):
            _artifact_ref_path(
                tmp_path, "../secrets/key.pem", source_name="test.json", field_name="ref"
            )


# =========================================================================
# 25–26: _validate_review_semantics
# =========================================================================


class TestValidateReviewSemantics:
    def test_approved_with_blockers_raises(self) -> None:
        payload = {"verdict": "approved", "open_blockers": ["gate-x-failed"]}
        with pytest.raises(RuntimeViolation, match="cannot declare open_blockers"):
            _validate_review_semantics(payload, source_name="review.json")

    def test_approved_with_safe_false_raises(self) -> None:
        payload = {"verdict": "approved", "safe_for_next_stage": False, "open_blockers": []}
        with pytest.raises(RuntimeViolation, match="cannot set safe_for_next_stage"):
            _validate_review_semantics(payload, source_name="review.json")

    def test_rejected_with_blockers_ok(self) -> None:
        """rejected verdict with open_blockers is fine."""
        payload = {"verdict": "rejected", "open_blockers": ["issue-1"]}
        _validate_review_semantics(payload, source_name="review.json")  # no error

    def test_approved_clean_ok(self) -> None:
        """approved with no blockers and safe=True is fine."""
        payload = {"verdict": "approved", "safe_for_next_stage": True, "open_blockers": []}
        _validate_review_semantics(payload, source_name="review.json")  # no error
