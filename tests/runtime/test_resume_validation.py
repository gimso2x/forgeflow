import pytest

from forgeflow_runtime.resume_validation import (
    expected_gates_before_stage,
    plan_ledger_progress,
    resume_start_index,
)


ROUTE = ["clarify", "plan", "execute", "finalize"]
STAGE_GATE_MAP = {
    "clarify": "clarification_complete",
    "plan": "plan_approved",
    "execute": "execution_complete",
    "finalize": "final_review_complete",
}


class ResumeViolation(Exception):
    pass


def test_plan_ledger_progress_initializes_resume_lists() -> None:
    plan_ledger: dict = {}

    assert plan_ledger_progress(plan_ledger) == {
        "completed_stages": [],
        "completed_gates": [],
        "retries": {},
    }


def test_expected_gates_before_stage_returns_route_prefix_gates() -> None:
    assert expected_gates_before_stage(ROUTE, "execute", stage_gate_map=STAGE_GATE_MAP) == [
        "clarification_complete",
        "plan_approved",
    ]


def test_resume_start_index_advances_when_current_stage_gate_is_complete() -> None:
    run_state = {
        "current_stage": "plan",
        "status": "in_progress",
        "completed_stages": ["clarify", "plan"],
        "completed_gates": ["clarification_complete", "plan_approved"],
    }

    assert (
        resume_start_index(
            run_state,
            ROUTE,
            stage_gate_map=STAGE_GATE_MAP,
            violation_factory=ResumeViolation,
        )
        == 2
    )


def test_resume_start_index_rejects_future_completed_gates() -> None:
    run_state = {
        "current_stage": "plan",
        "status": "in_progress",
        "completed_stages": ["clarify", "plan"],
        "completed_gates": ["clarification_complete", "execution_complete"],
    }

    with pytest.raises(ResumeViolation, match="out-of-sequence completed gates"):
        resume_start_index(
            run_state,
            ROUTE,
            stage_gate_map=STAGE_GATE_MAP,
            violation_factory=ResumeViolation,
        )


def test_resume_start_index_rejects_non_terminal_completed_checkpoint() -> None:
    run_state = {
        "current_stage": "execute",
        "status": "completed",
        "completed_stages": ["clarify", "plan", "execute"],
        "completed_gates": ["clarification_complete", "plan_approved", "execution_complete"],
    }

    with pytest.raises(ResumeViolation, match="must already be at terminal stage finalize"):
        resume_start_index(
            run_state,
            ROUTE,
            stage_gate_map=STAGE_GATE_MAP,
            violation_factory=ResumeViolation,
        )
