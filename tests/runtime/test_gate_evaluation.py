from forgeflow_runtime.gate_evaluation import required_finalize_flags


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
