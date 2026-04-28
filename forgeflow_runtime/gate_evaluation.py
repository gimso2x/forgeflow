from __future__ import annotations


from pathlib import Path
from typing import Any

from forgeflow_runtime.artifact_validation import (
    artifact_path,
    artifact_variants,
    load_validated_artifact,
    missing_artifacts,
)
from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.evolution_observations import append_review_blocker_observation
from forgeflow_runtime.policy_loader import RuntimePolicy


_STAGE_GATE_EVIDENCE_ARTIFACTS = {
    "spec-review": "review-report-spec.json",
    "quality-review": "review-report.json",
    "long-run": "eval-record.json",
}


def gate_evidence_ref(stage_name: str, gate_name: str) -> str:
    prefix = _STAGE_GATE_EVIDENCE_ARTIFACTS.get(stage_name, "run-state.json")
    return f"{prefix}#gate:{gate_name}"


def required_finalize_flags(route: list[str], finalize_flags: list[str]) -> list[str]:
    required = list(finalize_flags)
    if "spec-review" not in route and "spec_review_approved" in required:
        required.remove("spec_review_approved")
    if "quality-review" not in route and "quality_review_approved" in required:
        required.remove("quality_review_approved")
    return required


def record_completed_gate(run_state: dict[str, Any], stage_name: str, *, stage_gate_map: dict[str, str]) -> None:
    gate_name = stage_gate_map.get(stage_name)
    if gate_name and gate_name not in run_state["completed_gates"]:
        run_state["completed_gates"].append(gate_name)


def matching_review_payload(
    task_dir: Path,
    expected_review_type: str,
    expected_verdict: str,
    *,
    canonical_task_id: str,
) -> dict[str, Any] | None:
    for artifact_name in ["review-report", "review-report-spec", "review-report-quality"]:
        review_path = artifact_path(task_dir, artifact_name)
        if not review_path.exists():
            continue
        payload = load_validated_artifact(task_dir, artifact_name, expected_task_id=canonical_task_id)
        _validate_review_semantics(payload, source_name=review_path.name)
        if payload.get("review_type") == expected_review_type and payload.get("verdict") == expected_verdict:
            return payload
    return None


def enforce_stage_gate(task_dir: Path, policy: RuntimePolicy, stage_name: str, *, canonical_task_id: str) -> None:
    gate_name = policy.stage_gate_map.get(stage_name)
    if gate_name is None:
        return

    missing_gate_artifacts = missing_artifacts(task_dir, policy.gate_requirements.get(gate_name, []))
    if missing_gate_artifacts:
        raise RuntimeViolation(
            f"{stage_name} requires artifacts satisfying gate {gate_name}: {', '.join(missing_gate_artifacts)}"
        )

    for required_artifact in policy.gate_requirements.get(gate_name, []):
        for variant in artifact_variants(required_artifact):
            variant_path = artifact_path(task_dir, variant)
            if variant_path.exists():
                load_validated_artifact(task_dir, variant, expected_task_id=canonical_task_id)

    gate_review = policy.gate_reviews.get(gate_name, {})
    expected_review_type = gate_review.get("review_type")
    expected_verdict = gate_review.get("verdict")
    if expected_review_type and expected_verdict and matching_review_payload(
        task_dir,
        expected_review_type,
        expected_verdict,
        canonical_task_id=canonical_task_id,
    ) is None:
        _append_review_gate_observation(
            task_dir,
            stage_name=stage_name,
            gate_name=gate_name,
            expected_review_type=expected_review_type,
            expected_verdict=expected_verdict,
            canonical_task_id=canonical_task_id,
        )
        raise RuntimeViolation(
            f"{stage_name} requires approved {expected_review_type} review-report artifact"
        )


def _append_review_gate_observation(
    task_dir: Path,
    *,
    stage_name: str,
    gate_name: str | None,
    expected_review_type: str,
    expected_verdict: str,
    canonical_task_id: str,
) -> None:
    reason = f"{stage_name} requires {expected_verdict} {expected_review_type} review-report artifact"
    for artifact_name in ["review-report", "review-report-spec", "review-report-quality"]:
        review_path = artifact_path(task_dir, artifact_name)
        if not review_path.exists():
            continue
        try:
            payload = load_validated_artifact(task_dir, artifact_name, expected_task_id=canonical_task_id)
        except Exception:
            continue
        if payload.get("review_type") != expected_review_type:
            continue
        append_review_blocker_observation(
            task_dir,
            task_id=canonical_task_id,
            stage=stage_name,
            gate=gate_name,
            review_payload=payload,
            artifact_refs=[review_path.name],
            reason=reason,
        )
        return


def _validate_review_semantics(payload: dict[str, Any], *, source_name: str) -> None:
    verdict = payload.get("verdict")
    open_blockers = payload.get("open_blockers", [])
    if open_blockers is None:
        open_blockers = []
    if verdict == "approved" and open_blockers:
        raise RuntimeViolation(f"approved {source_name} cannot declare open_blockers")
    if verdict == "approved" and payload.get("safe_for_next_stage") is False:
        raise RuntimeViolation(f"approved {source_name} cannot set safe_for_next_stage=false")
