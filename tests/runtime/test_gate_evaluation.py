from forgeflow_runtime.gate_evaluation import record_completed_gate, required_finalize_flags


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


def test_record_completed_gate_appends_stage_gate_once() -> None:
    run_state = {"completed_gates": []}

    record_completed_gate(run_state, "plan", stage_gate_map={"plan": "plan_approved"})
    record_completed_gate(run_state, "plan", stage_gate_map={"plan": "plan_approved"})

    assert run_state["completed_gates"] == ["plan_approved"]


def test_record_completed_gate_skips_stage_without_gate() -> None:
    run_state = {"completed_gates": []}

    record_completed_gate(run_state, "execute", stage_gate_map={"plan": "plan_approved"})

    assert run_state["completed_gates"] == []
