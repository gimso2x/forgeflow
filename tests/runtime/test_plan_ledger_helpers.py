from __future__ import annotations

import pytest

from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.plan_ledger import (
    canonical_current_task_id,
    current_plan_task,
    finalize_plan_ledger_task,
    rewind_plan_ledger_progress,
    sync_plan_ledger_gate,
    sync_plan_ledger_review,
    sync_plan_ledger_retry,
)


def _ledger() -> dict:
    return {
        "current_task_id": "task-1",
        "tasks": [
            {
                "id": "task-1",
                "status": "todo",
                "attempt_count": 0,
                "evidence_refs": [],
            }
        ],
        "completed_stages": [],
        "completed_gates": [],
        "retries": {},
    }


def test_current_plan_task_rejects_missing_current_task() -> None:
    with pytest.raises(RuntimeViolation, match="current_task_id task-missing is not present"):
        current_plan_task({"current_task_id": "task-missing", "tasks": [{"id": "task-1"}]})


def test_canonical_current_task_id_prefers_plan_ledger_current_task() -> None:
    assert canonical_current_task_id({"current_task_id": "run-state-task"}, {"current_task_id": "ledger-task"}) == "ledger-task"


def test_sync_plan_ledger_gate_records_stage_gate_and_evidence_once() -> None:
    ledger = _ledger()

    sync_plan_ledger_gate(ledger, stage_name="plan", gate_name="plan_executable")
    sync_plan_ledger_gate(ledger, stage_name="plan", gate_name="plan_executable")

    assert ledger["completed_stages"] == ["plan"]
    assert ledger["completed_gates"] == ["plan_executable"]
    assert ledger["tasks"][0]["status"] == "in_progress"
    assert ledger["tasks"][0]["evidence_refs"] == ["run-state.json#gate:plan_executable"]


def test_sync_plan_ledger_retry_increments_task_and_stage_retry_counts() -> None:
    ledger = _ledger()

    sync_plan_ledger_retry(ledger, stage_name="execute")
    sync_plan_ledger_retry(ledger, stage_name="execute")

    assert ledger["tasks"][0]["attempt_count"] == 2
    assert ledger["retries"] == {"execute": 2}


def test_sync_plan_ledger_review_records_latest_verdict_and_evidence() -> None:
    ledger = _ledger()

    sync_plan_ledger_review(ledger, review_artifact="review-report.json", verdict="approved")

    assert ledger["last_review_verdict"] == "approved"
    assert ledger["tasks"][0]["evidence_refs"] == ["review-report.json#verdict:approved"]


def test_finalize_plan_ledger_task_marks_current_task_done_with_attempt() -> None:
    ledger = _ledger()

    finalize_plan_ledger_task(ledger)

    assert ledger["tasks"][0]["status"] == "done"
    assert ledger["tasks"][0]["attempt_count"] == 1


def test_rewind_plan_ledger_progress_removes_future_stage_gate_and_review_evidence() -> None:
    ledger = _ledger()
    ledger.update(
        {
            "completed_stages": ["clarify", "execute", "quality-review"],
            "completed_gates": ["clarification_complete", "execution_evidenced", "quality_review_passed"],
            "last_review_verdict": "approved",
        }
    )
    ledger["tasks"][0]["evidence_refs"] = [
        "run-state.json#gate:execution_evidenced",
        "review-report.json#verdict:approved",
    ]

    rewind_plan_ledger_progress(
        ledger,
        route=["clarify", "execute", "quality-review", "finalize"],
        resume_stage="execute",
        stage_gate_map={
            "clarify": "clarification_complete",
            "execute": "execution_evidenced",
            "quality-review": "quality_review_passed",
            "finalize": "ready_to_finalize",
        },
    )

    assert ledger["completed_stages"] == ["clarify"]
    assert ledger["completed_gates"] == ["clarification_complete"]
    assert ledger["tasks"][0]["status"] == "in_progress"
    assert ledger["tasks"][0]["evidence_refs"] == []
    assert "last_review_verdict" not in ledger
