import pytest

from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.gate_evaluation import enforce_stage_gate, gate_evidence_ref, record_completed_gate, required_finalize_flags
from forgeflow_runtime.policy_loader import RuntimePolicy


def test_required_finalize_flags_drops_spec_review_for_routes_without_spec_review() -> None:
    assert required_finalize_flags(
        ["clarify", "plan", "execute", "quality-review", "finalize"],
        ["spec_review_approved", "quality_review_approved"],
    ) == ["quality_review_approved"]


def test_required_finalize_flags_drops_quality_review_for_routes_without_quality_review() -> None:
    assert required_finalize_flags(
        ["clarify", "plan", "execute", "finalize"],
        ["spec_review_approved", "quality_review_approved"],
    ) == []


def test_required_finalize_flags_preserves_policy_order() -> None:
    assert required_finalize_flags(
        ["clarify", "plan", "spec-review", "execute", "quality-review", "finalize"],
        ["quality_review_approved", "spec_review_approved", "custom_flag"],
    ) == ["quality_review_approved", "spec_review_approved", "custom_flag"]


def test_gate_evidence_ref_uses_stage_specific_review_artifacts() -> None:
    assert gate_evidence_ref("spec-review", "spec_review_approved") == "review-report-spec.json#gate:spec_review_approved"
    assert gate_evidence_ref("quality-review", "quality_review_approved") == "review-report.json#gate:quality_review_approved"
    assert gate_evidence_ref("long-run", "long_run_approved") == "eval-record.json#gate:long_run_approved"


def test_gate_evidence_ref_uses_run_state_for_regular_stages() -> None:
    assert gate_evidence_ref("plan", "plan_approved") == "run-state.json#gate:plan_approved"


def test_record_completed_gate_appends_stage_gate_once() -> None:
    run_state = {"completed_gates": []}

    record_completed_gate(run_state, "plan", stage_gate_map={"plan": "plan_approved"})
    record_completed_gate(run_state, "plan", stage_gate_map={"plan": "plan_approved"})

    assert run_state["completed_gates"] == ["plan_approved"]


def test_record_completed_gate_skips_stage_without_gate() -> None:
    run_state = {"completed_gates": []}

    record_completed_gate(run_state, "execute", stage_gate_map={"plan": "plan_approved"})

    assert run_state["completed_gates"] == []


def test_enforce_stage_gate_reports_missing_gate_artifacts(tmp_path) -> None:
    policy = RuntimePolicy(
        workflow_stages=["plan"],
        stage_requirements={},
        stage_gate_map={"plan": "plan_approved"},
        gate_requirements={"plan_approved": ["plan"]},
        gate_reviews={},
        routes={},
        finalize_flags=[],
        review_order=[],
    )

    with pytest.raises(RuntimeViolation, match="plan requires artifacts satisfying gate plan_approved: plan"):
        enforce_stage_gate(tmp_path, policy, "plan", canonical_task_id="task-1")
