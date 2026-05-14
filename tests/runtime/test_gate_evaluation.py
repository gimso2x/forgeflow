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


def test_record_completed_gate_appends_stage_gate_once(artifact_factory) -> None:
    run_state = artifact_factory("run-state", completed_gates=[])

    record_completed_gate(run_state, "plan", stage_gate_map={"plan": "plan_approved"})
    record_completed_gate(run_state, "plan", stage_gate_map={"plan": "plan_approved"})

    assert run_state["completed_gates"] == ["plan_approved"]


def test_record_completed_gate_skips_stage_without_gate(artifact_factory) -> None:
    run_state = artifact_factory("run-state", completed_gates=[])

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


def _policy_requiring_brief() -> RuntimePolicy:
    return RuntimePolicy(
        workflow_stages=["plan"],
        stage_requirements={},
        stage_gate_map={"plan": "clarification_complete"},
        gate_requirements={"clarification_complete": ["brief"]},
        gate_reviews={},
        routes={},
        finalize_flags=[],
        review_order=[],
    )


def test_clarification_gate_rejects_brief_without_explicit_specialist_skip_decisions(tmp_path, artifact_factory, write_json) -> None:
    brief = artifact_factory(
        "brief",
        task_id="task-1",
        objective="small docs change",
        in_scope=["docs"],
        acceptance_criteria=["docs updated"],
        required_specialists=[],
    )
    # Ensure optional fields that should be missing are actually missing if factory provides defaults
    brief.pop("skipped_specialists", None)
    brief.pop("skip_rationale", None)

    write_json(tmp_path / "brief.json", brief)

    with pytest.raises(RuntimeViolation, match="must explicitly require or skip every specialist"):
        enforce_stage_gate(tmp_path, _policy_requiring_brief(), "plan", canonical_task_id="task-1")


def test_clarification_gate_accepts_explicit_specialist_skips_with_rationale(tmp_path, artifact_factory, write_json) -> None:
    brief = artifact_factory(
        "brief",
        task_id="task-1",
        objective="small docs change",
        in_scope=["docs"],
        acceptance_criteria=["docs updated"],
        required_specialists=[],
        skipped_specialists=["security-review", "ux-review", "perf-review", "frontend-execute", "backend-execute", "infra-execute"],
        skip_rationale="Docs-only task; no specialist domain execution needed.",
    )
    write_json(tmp_path / "brief.json", brief)

    enforce_stage_gate(tmp_path, _policy_requiring_brief(), "plan", canonical_task_id="task-1")


def test_clarification_gate_rejects_conflicting_specialist_decisions(tmp_path, artifact_factory, write_json) -> None:
    brief = artifact_factory(
        "brief",
        task_id="task-1",
        objective="small docs change",
        in_scope=["docs"],
        acceptance_criteria=["docs updated"],
        required_specialists=["security-review"],
        skipped_specialists=["security-review", "ux-review", "perf-review", "frontend-execute", "backend-execute", "infra-execute"],
        skip_rationale="Docs-only task; no specialist domain execution needed.",
    )
    write_json(tmp_path / "brief.json", brief)

    with pytest.raises(RuntimeViolation, match="cannot both require and skip specialists: security-review"):
        enforce_stage_gate(tmp_path, _policy_requiring_brief(), "plan", canonical_task_id="task-1")


def test_clarification_gate_rejects_unknown_specialists(tmp_path, artifact_factory, write_json) -> None:
    brief = artifact_factory(
        "brief",
        task_id="task-1",
        objective="small docs change",
        in_scope=["docs"],
        acceptance_criteria=["docs updated"],
        required_specialists=["unknown-review"],
        skipped_specialists=["security-review", "ux-review", "perf-review", "frontend-execute", "backend-execute", "infra-execute"],
        skip_rationale="Docs-only task; no specialist domain execution needed.",
    )
    write_json(tmp_path / "brief.json", brief)

    with pytest.raises(RuntimeViolation, match="failed schema validation: required_specialists/0"):
        enforce_stage_gate(tmp_path, _policy_requiring_brief(), "plan", canonical_task_id="task-1")
