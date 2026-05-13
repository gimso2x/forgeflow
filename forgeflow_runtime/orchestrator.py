from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from forgeflow_runtime.artifact_validation import (
    REPO_ROOT,
    SCHEMA_BY_ARTIFACT,
    artifact_path as _artifact_path,
    artifact_variants as _artifact_variants,
    assert_task_id_matches as _assert_task_id_matches,
    coerce_legacy_artifact_payload as _coerce_legacy_artifact_payload,
    has_artifact as _has_artifact,
    load_json as _load_json,
    load_validated_artifact as _load_validated_artifact,
    missing_artifacts as _missing_artifacts,
    schema_name_for_artifact as _schema_name_for_artifact,
    schema_validator as _schema_validator,
    validate_artifact_payload as _validate_artifact_payload,
    write_json as _write_json,
    write_validated_artifact as _write_validated_artifact,
)
from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.gate_evaluation import enforce_stage_gate as _enforce_stage_gate
from forgeflow_runtime.gate_evaluation import record_completed_gate, required_finalize_flags
from forgeflow_runtime.plan_ledger import (
    canonical_current_task_id as _canonical_current_task_id,
    current_plan_task as _current_plan_task,
    finalize_plan_ledger_task as _finalize_plan_ledger_task,
    plan_ledger_progress as _plan_ledger_progress,
    rewind_plan_ledger_progress as _rewind_plan_ledger_progress,
    sync_plan_ledger_gate as _sync_plan_ledger_gate,
    sync_plan_ledger_retry as _sync_plan_ledger_retry,
    sync_plan_ledger_review as _sync_plan_ledger_review,
)
from forgeflow_runtime.operator_routing import role_for_stage
from forgeflow_runtime.policy_loader import RuntimePolicy, load_runtime_policy
from forgeflow_runtime.resume_validation import resume_start_index
from forgeflow_runtime.route_execution import build_route_result, route_entry_decision, route_iteration_stages, stage_completion_status
from forgeflow_runtime.stage_transition import next_stage_for_transition
from forgeflow_runtime.task_identity import canonical_task_id as _canonical_task_id
from forgeflow_runtime.task_identity import task_id as _task_id
from forgeflow_runtime.workflow_engine import resolve_route as _workflow_resolve_route
from forgeflow_runtime.workflow_engine import workflow_from_runtime_policy as _workflow_from_runtime_policy
from forgeflow_runtime.workflow_override import resolve_project_workflow as _resolve_project_workflow

from forgeflow_runtime.execute_context import build_execute_context as _build_execute_context, format_execute_prompt as _format_execute_prompt
from forgeflow_runtime.progress_tracker import calculate_progress as _calculate_progress, detect_progress_anomaly as _detect_progress_anomaly
from forgeflow_runtime.stuck_detector import detect_stuck as _detect_stuck, should_escalate as _should_escalate, format_stuck_report as _format_stuck_report
from forgeflow_runtime.worktree import (
    create_worktree as _create_worktree,
    create_worker_worktree as _create_worker_worktree,
    detect_path_conflicts as _detect_path_conflicts,
    is_repo_clean as _is_repo_clean,
    merge_worker_worktree as _merge_worker_worktree,
    remove_worktree as _remove_worktree,
)


@dataclass(frozen=True)
class TransitionResult:
    next_stage: str
    execution: dict[str, Any] | None = None


def _stub_execution_warning() -> str:
    return "STUB EXECUTION: no real CLI adapter ran; pass --real for live execution or --assert-real to fail fast."


def _execution_payload(*, stage: str, role: str, adapter: str, result: Any, use_real: bool = False) -> dict[str, Any]:
    execution_mode = "real" if use_real else "stub"
    payload = {
        "stage": stage,
        "role": role,
        "adapter": adapter,
        "execution_mode": execution_mode,
        "status": result.status,
        "artifacts_produced": result.artifacts_produced,
        "token_usage": result.token_usage,
    }
    if execution_mode == "stub":
        payload["warning"] = _stub_execution_warning()
    if result.error:
        payload["error"] = result.error
    return payload


def _load_plan_ledger(task_dir: Path, *, canonical_task_id: str) -> dict[str, Any] | None:
    path = _artifact_path(task_dir, "plan-ledger")
    if not path.exists():
        return None
    payload = _load_validated_artifact(task_dir, "plan-ledger", expected_task_id=canonical_task_id)
    current_task_id = payload.get("current_task_id")
    if current_task_id is not None and not any(task.get("id") == current_task_id for task in payload.get("tasks", [])):
        raise RuntimeViolation(f"plan-ledger.json current_task_id {current_task_id} is not present in tasks[]")
    return payload


def _require_plan_ledger_for_route(task_dir: Path, route_name: str, *, canonical_task_id: str) -> dict[str, Any] | None:
    if route_name == "small":
        return None
    payload = _load_plan_ledger(task_dir, canonical_task_id=canonical_task_id)
    if payload is None:
        raise RuntimeViolation(f"{route_name} route requires plan-ledger.json")
    ledger_route = payload.get("route")
    if ledger_route != route_name:
        raise RuntimeViolation(f"plan-ledger.json route {ledger_route} does not match requested route {route_name}")
    return payload





def _reset_review_flags(run_state: dict[str, Any]) -> None:
    run_state["spec_review_approved"] = False
    run_state["quality_review_approved"] = False



def _clear_rewind_review_flags(run_state: dict[str, Any], *, removed_stages: list[str]) -> None:
    if "spec-review" in removed_stages:
        run_state["spec_review_approved"] = False
    if any(stage_name in {"quality-review", "long-run"} for stage_name in removed_stages):
        run_state["quality_review_approved"] = False



def _write_plan_ledger_if_present(task_dir: Path, plan_ledger: dict[str, Any] | None) -> None:
    if plan_ledger is not None:
        _write_validated_artifact(task_dir, "plan-ledger", plan_ledger)


def _load_checkpoint(task_dir: Path, *, canonical_task_id: str) -> dict[str, Any] | None:
    path = _artifact_path(task_dir, "checkpoint")
    if not path.exists():
        return None
    return _load_validated_artifact(task_dir, "checkpoint", expected_task_id=canonical_task_id)


def _load_session_state(task_dir: Path, *, canonical_task_id: str) -> dict[str, Any] | None:
    path = _artifact_path(task_dir, "session-state")
    if not path.exists():
        return None
    return _load_validated_artifact(task_dir, "session-state", expected_task_id=canonical_task_id)


def _validate_review_semantics(payload: dict[str, Any], *, source_name: str) -> None:
    verdict = payload.get("verdict")
    open_blockers = payload.get("open_blockers", [])
    if open_blockers is None:
        open_blockers = []
    if verdict == "approved" and open_blockers:
        raise RuntimeViolation(f"approved {source_name} cannot declare open_blockers")
    if verdict == "approved" and payload.get("safe_for_next_stage") is False:
        raise RuntimeViolation(f"approved {source_name} cannot set safe_for_next_stage=false")


def _expected_plan_ledger_ref(*, route_name: str, plan_ledger: dict[str, Any] | None) -> str:
    if route_name == "small" or plan_ledger is None:
        return "run-state.json"
    return "plan-ledger.json"


def _validate_session_state(
    task_dir: Path,
    session_state: dict[str, Any],
    *,
    route_name: str,
    run_state: dict[str, Any],
    plan_ledger: dict[str, Any] | None,
) -> None:
    for field_name in ["plan_ref", "plan_ledger_ref", "run_state_ref", "latest_checkpoint_ref"]:
        ref = session_state.get(field_name)
        if not isinstance(ref, str) or not ref:
            raise RuntimeViolation(f"session-state.json {field_name} is required")
        resolved = _artifact_ref_path(
            task_dir,
            ref,
            source_name="session-state.json",
            field_name=field_name,
        )
        if not resolved.exists():
            raise RuntimeViolation(f"session-state.json {field_name} {ref} does not exist")
    if session_state.get("latest_checkpoint_ref") != "checkpoint.json":
        raise RuntimeViolation(
            f"session-state.json latest_checkpoint_ref {session_state.get('latest_checkpoint_ref')} must point to checkpoint.json"
        )
    if session_state.get("run_state_ref") != "run-state.json":
        raise RuntimeViolation(
            f"session-state.json run_state_ref {session_state.get('run_state_ref')} must point to run-state.json"
        )
    if session_state.get("route") != route_name:
        raise RuntimeViolation(
            f"session-state.json route {session_state.get('route')} does not match canonical route {route_name}"
        )
    if session_state.get("current_stage") != run_state.get("current_stage"):
        raise RuntimeViolation(
            f"session-state.json current_stage {session_state.get('current_stage')} does not match run-state current_stage {run_state.get('current_stage')}"
        )
    expected_plan_ledger_ref = _expected_plan_ledger_ref(route_name=route_name, plan_ledger=plan_ledger)
    if session_state.get("plan_ledger_ref") != expected_plan_ledger_ref:
        raise RuntimeViolation(
            f"session-state.json plan_ledger_ref {session_state.get('plan_ledger_ref')} must point to {expected_plan_ledger_ref} for route {route_name}"
        )
    latest_review_ref = session_state.get("latest_review_ref")
    if latest_review_ref is not None:
        if not isinstance(latest_review_ref, str) or not latest_review_ref:
            raise RuntimeViolation("session-state.json latest_review_ref must be a non-empty string when present")
        resolved = _artifact_ref_path(
            task_dir,
            latest_review_ref,
            source_name="session-state.json",
            field_name="latest_review_ref",
        )
        if not resolved.exists():
            raise RuntimeViolation(f"session-state.json latest_review_ref {latest_review_ref} does not exist")
        canonical_latest_review_ref = _latest_review_ref(task_dir)
        if latest_review_ref != canonical_latest_review_ref:
            raise RuntimeViolation(
                f"session-state.json latest_review_ref {latest_review_ref} does not match canonical latest review {canonical_latest_review_ref}"
            )


def _artifact_ref_path(task_dir: Path, ref: str, *, source_name: str, field_name: str) -> Path:
    ref_path = Path(ref)
    if ref_path.is_absolute():
        raise RuntimeViolation(f"{source_name} {field_name} {ref} must be task-relative")
    resolved = (task_dir / ref_path).resolve()
    task_root = task_dir.resolve()
    if task_root not in {resolved, *resolved.parents}:
        raise RuntimeViolation(f"{source_name} {field_name} {ref} escapes task directory")
    return resolved


def _checkpoint_ref_path(task_dir: Path, ref: str) -> Path:
    return _artifact_ref_path(task_dir, ref, source_name="checkpoint.json", field_name="ref")


def _validate_checkpoint(
    task_dir: Path,
    checkpoint: dict[str, Any],
    *,
    route_name: str,
    canonical_task_id: str,
    run_state: dict[str, Any],
    plan_ledger: dict[str, Any] | None,
) -> None:
    checkpoint_route = checkpoint.get("route")
    if checkpoint_route != route_name:
        raise RuntimeViolation(f"checkpoint.json route {checkpoint_route} does not match requested route {route_name}")
    checkpoint_stage = checkpoint.get("current_stage")
    run_state_stage = run_state.get("current_stage")
    if checkpoint_stage != run_state_stage:
        raise RuntimeViolation(
            f"checkpoint.json current_stage {checkpoint_stage} does not match run-state current_stage {run_state_stage}"
        )

    ref_map = {
        "plan_ref": checkpoint.get("plan_ref"),
        "plan_ledger_ref": checkpoint.get("plan_ledger_ref"),
        "run_state_ref": checkpoint.get("run_state_ref"),
        "latest_review_ref": checkpoint.get("latest_review_ref"),
    }
    for field_name, ref in ref_map.items():
        if not isinstance(ref, str) or not ref:
            continue
        resolved = _checkpoint_ref_path(task_dir, ref)
        if not resolved.exists():
            raise RuntimeViolation(f"checkpoint.json {field_name} {ref} does not exist")

    run_state_ref = checkpoint.get("run_state_ref")
    if run_state_ref != "run-state.json":
        raise RuntimeViolation(f"checkpoint.json run_state_ref {run_state_ref} must point to run-state.json")

    checkpoint_task_id = checkpoint.get("current_task_id")
    if plan_ledger is not None:
        ledger_task_id = plan_ledger.get("current_task_id")
        if checkpoint_task_id and checkpoint_task_id != ledger_task_id:
            raise RuntimeViolation(
                f"checkpoint.json current_task_id {checkpoint_task_id} does not match plan-ledger current_task_id {ledger_task_id}"
            )
    elif checkpoint_task_id and checkpoint_task_id != run_state.get("current_task_id"):
        raise RuntimeViolation(
            f"checkpoint.json current_task_id {checkpoint_task_id} does not match run-state current_task_id {run_state.get('current_task_id')}"
        )


def _latest_review_ref(task_dir: Path) -> str | None:
    for artifact_name in ["review-report-quality", "review-report-spec", "review-report"]:
        if _artifact_path(task_dir, artifact_name).exists():
            return f"{artifact_name}.json"
    return None


def _latest_review_verdict(task_dir: Path, *, canonical_task_id: str) -> str | None:
    latest_review_ref = _latest_review_ref(task_dir)
    if latest_review_ref is None:
        return None
    artifact_name = latest_review_ref.removesuffix(".json")
    review = _load_validated_artifact(task_dir, artifact_name, expected_task_id=canonical_task_id)
    _validate_review_semantics(review, source_name=latest_review_ref)
    verdict = review.get("verdict")
    return verdict if isinstance(verdict, str) and verdict else None


def _default_checkpoint(*, task_dir: Path, route_name: str, run_state: dict[str, Any], plan_ledger: dict[str, Any] | None) -> dict[str, Any]:
    checkpoint = {
        "schema_version": "0.2",
        "task_id": run_state["task_id"],
        "route": route_name,
        "current_stage": run_state["current_stage"],
        "plan_ref": "plan.json" if _artifact_path(task_dir, "plan").exists() else "brief.json",
        "plan_ledger_ref": "plan-ledger.json" if plan_ledger is not None else "run-state.json",
        "run_state_ref": "run-state.json",
        "next_action": "Resume from the current stage after reloading canonical artifacts.",
        "open_blockers": [],
        "updated_at": datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    current_task_id = _canonical_current_task_id(run_state, plan_ledger)
    if current_task_id:
        checkpoint["current_task_id"] = current_task_id
    latest_review_ref = _latest_review_ref(task_dir)
    if latest_review_ref is not None:
        checkpoint["latest_review_ref"] = latest_review_ref
    return checkpoint


def _checkpoint_next_action(stage_name: str, route: list[str]) -> str:
    if stage_name == route[-1]:
        return "Route complete. Review final artifacts and hand off results."
    next_index = route.index(stage_name) + 1
    return f"Resume at {route[next_index]} after reloading canonical artifacts."


def _sync_checkpoint(
    task_dir: Path,
    *,
    route_name: str,
    route: list[str],
    run_state: dict[str, Any],
    plan_ledger: dict[str, Any] | None,
    checkpoint: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(checkpoint) if checkpoint is not None else _default_checkpoint(
        task_dir=task_dir,
        route_name=route_name,
        run_state=run_state,
        plan_ledger=plan_ledger,
    )
    payload["schema_version"] = "0.2"
    payload["task_id"] = run_state["task_id"]
    payload["route"] = route_name
    payload["current_stage"] = run_state["current_stage"]
    payload["plan_ref"] = "plan.json" if _artifact_path(task_dir, "plan").exists() else payload.get("plan_ref", "brief.json")
    payload["plan_ledger_ref"] = "plan-ledger.json" if plan_ledger is not None else payload.get("plan_ledger_ref", "run-state.json")
    payload["run_state_ref"] = "run-state.json"
    current_task_id = _canonical_current_task_id(run_state, plan_ledger)
    if current_task_id:
        payload["current_task_id"] = current_task_id
    else:
        payload.pop("current_task_id", None)
    latest_review_ref = _latest_review_ref(task_dir)
    if latest_review_ref is not None:
        payload["latest_review_ref"] = latest_review_ref
    else:
        payload.pop("latest_review_ref", None)
    payload["next_action"] = _checkpoint_next_action(run_state["current_stage"], route)
    payload["open_blockers"] = [] if run_state.get("status") == "completed" else list(payload.get("open_blockers", []))
    payload["updated_at"] = datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_validated_artifact(task_dir, "checkpoint", payload)
    return payload


def _default_session_state(
    *,
    task_dir: Path,
    route_name: str,
    run_state: dict[str, Any],
    checkpoint: dict[str, Any],
    plan_ledger: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "0.2",
        "task_id": run_state["task_id"],
        "route": route_name,
        "current_stage": run_state["current_stage"],
        "plan_ref": "plan.json" if _artifact_path(task_dir, "plan").exists() else "brief.json",
        "plan_ledger_ref": "plan-ledger.json" if plan_ledger is not None else "run-state.json",
        "run_state_ref": "run-state.json",
        "latest_checkpoint_ref": "checkpoint.json",
        "next_action": checkpoint["next_action"],
        "updated_at": checkpoint["updated_at"],
    }
    current_task_id = _canonical_current_task_id(run_state, plan_ledger)
    if current_task_id is not None:
        payload["current_task_id"] = current_task_id
    latest_review_ref = checkpoint.get("latest_review_ref")
    if latest_review_ref is not None:
        payload["latest_review_ref"] = latest_review_ref
    return payload


def _sync_session_state(
    task_dir: Path,
    *,
    route_name: str,
    run_state: dict[str, Any],
    checkpoint: dict[str, Any],
    plan_ledger: dict[str, Any] | None,
    session_state: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(session_state) if session_state is not None else _default_session_state(
        task_dir=task_dir,
        route_name=route_name,
        run_state=run_state,
        checkpoint=checkpoint,
        plan_ledger=plan_ledger,
    )
    payload["schema_version"] = "0.2"
    payload["task_id"] = run_state["task_id"]
    payload["route"] = route_name
    payload["current_stage"] = run_state["current_stage"]
    payload["plan_ref"] = "plan.json" if _artifact_path(task_dir, "plan").exists() else "brief.json"
    payload["plan_ledger_ref"] = "plan-ledger.json" if plan_ledger is not None else "run-state.json"
    payload["run_state_ref"] = "run-state.json"
    payload["latest_checkpoint_ref"] = "checkpoint.json"
    payload["next_action"] = checkpoint["next_action"]
    payload["updated_at"] = checkpoint["updated_at"]
    current_task_id = _canonical_current_task_id(run_state, plan_ledger)
    if current_task_id is not None:
        payload["current_task_id"] = current_task_id
    else:
        payload.pop("current_task_id", None)
    latest_review_ref = checkpoint.get("latest_review_ref")
    if latest_review_ref is not None:
        payload["latest_review_ref"] = latest_review_ref
    else:
        payload.pop("latest_review_ref", None)
    _write_validated_artifact(task_dir, "session-state", payload)
    return payload


def _infer_route_for_recovery(
    *,
    checkpoint: dict[str, Any] | None,
    plan_ledger: dict[str, Any] | None,
    fallback_route: str,
) -> str:
    ledger_route = plan_ledger.get("route") if plan_ledger is not None else None
    checkpoint_route = checkpoint.get("route") if checkpoint is not None else None

    if isinstance(ledger_route, str) and ledger_route:
        if isinstance(checkpoint_route, str) and checkpoint_route and checkpoint_route != ledger_route:
            raise RuntimeViolation(
                f"checkpoint.json route {checkpoint_route} does not match canonical route {ledger_route}"
            )
        return ledger_route

    if isinstance(checkpoint_route, str) and checkpoint_route:
        return checkpoint_route
    return fallback_route


def _assert_stage_in_route(*, route_name: str, route: list[str], stage_name: str) -> None:
    if stage_name not in route:
        raise RuntimeViolation(f"recovery route {route_name} does not include current stage {stage_name}")


def _default_run_state(task_dir: Path) -> dict[str, Any]:
    return {
        "schema_version": "0.2",
        "task_id": _task_id(task_dir),
        "current_stage": "clarify",
        "status": "not_started",
        "completed_gates": [],
        "failed_gates": [],
        "retries": {},
        "evidence_refs": [],
        "current_task_id": "",
        "spec_review_approved": False,
        "quality_review_approved": False,
    }

def _ensure_run_state(task_dir: Path, *, canonical_task_id: str | None = None) -> dict[str, Any]:
    path = _artifact_path(task_dir, "run-state")
    if path.exists():
        return _load_validated_artifact(task_dir, "run-state", expected_task_id=canonical_task_id)
    run_state = _default_run_state(task_dir)
    _write_validated_artifact(task_dir, "run-state", run_state)
    return run_state



def _ensure_decision_log(task_dir: Path, *, canonical_task_id: str | None = None) -> dict[str, Any]:
    path = _artifact_path(task_dir, "decision-log")
    if path.exists():
        return _load_validated_artifact(task_dir, "decision-log", expected_task_id=canonical_task_id)
    decision_log = {
        "schema_version": "0.2",
        "task_id": _task_id(task_dir),
        "entries": [],
    }
    _write_validated_artifact(task_dir, "decision-log", decision_log)
    return decision_log


def _append_decision(decision_log: dict[str, Any], *, actor: str, category: str, decision: str, rationale: str) -> None:
    decision_log["entries"].append(
        {
            "timestamp": datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "actor": actor,
            "category": category,
            "decision": decision,
            "rationale": rationale,
            "affected_artifacts": ["run-state", "decision-log"],
        }
    )


def _sync_review_flags(task_dir: Path, run_state: dict[str, Any], *, canonical_task_id: str) -> None:
    _reset_review_flags(run_state)
    for artifact_name in ["review-report", "review-report-spec", "review-report-quality"]:
        review_path = _artifact_path(task_dir, artifact_name)
        if not review_path.exists():
            continue
        review = _load_validated_artifact(task_dir, artifact_name, expected_task_id=canonical_task_id)
        _validate_review_semantics(review, source_name=review_path.name)
        if review.get("review_type") == "spec" and review.get("verdict") == "approved":
            run_state["spec_review_approved"] = True
        if review.get("review_type") == "quality" and review.get("verdict") == "approved":
            run_state["quality_review_approved"] = True


def _required_finalize_flags(policy: RuntimePolicy, route_name: str) -> list[str]:
    route = _resolve_route(policy, route_name)
    return required_finalize_flags(route, list(policy.finalize_flags))


def _record_gate(
    run_state: dict[str, Any],
    stage_name: str,
    *,
    stage_gate_map: dict[str, str],
    plan_ledger: dict[str, Any] | None = None,
) -> None:
    if plan_ledger is None:
        record_completed_gate(run_state, stage_name, stage_gate_map=stage_gate_map)



def _bootstrap_brief(task_id: str, route_name: str) -> dict[str, Any]:
    risk_level = "low" if route_name == "small" else "medium" if route_name == "medium" else "high"
    return {
        "schema_version": "0.2",
        "task_id": task_id,
        "objective": f"Bootstrap {route_name} task for ForgeFlow orchestration.",
        "in_scope": ["artifact-first workflow execution"],
        "out_of_scope": ["provider-specific integration"],
        "constraints": ["local runtime scaffold only"],
        "acceptance_criteria": ["route artifacts are initialized and resumable"],
        "risk_level": risk_level,
    }


def _bootstrap_plan(task_id: str, route_name: str) -> dict[str, Any]:
    return {
        "schema_version": "0.2",
        "task_id": task_id,
        "steps": [
            {
                "id": "step-1",
                "objective": f"Prepare {route_name} route artifacts",
                "dependencies": [],
                "expected_output": "brief, run-state, session-state, and route-owned artifacts exist",
                "verification": "python3 scripts/run_orchestrator.py status --task-dir <task-dir> --route <route>",
                "rollback_note": "remove bootstrapped task directory if initialization is invalid",
                "fulfills": ["route artifacts are initialized and resumable"],
            }
        ],
        "verify_plan": [
            {
                "target": "route artifacts are initialized and resumable",
                "type": "sub_req",
                "gates": ["python3 scripts/run_orchestrator.py status --task-dir <task-dir> --route <route>"],
            }
        ],
    }


def _slugify_file_stem(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "task"


def _analyze_objective_domain(objective: str) -> dict[str, Any]:
    """Extract domain signals from the objective for richer draft generation."""
    text = objective.lower()
    domains: list[str] = []
    tech_stack: list[str] = []
    change_type = "feature"

    _DOMAIN_SIGNALS: dict[str, list[str]] = {
        "api": ["api", "endpoint", "rest", "graphql", "http", "webhook", "rpc"],
        "frontend": ["ui", "component", "page", "layout", "css", "style", "responsive", "form", "modal", "dashboard", "navigation"],
        "backend": ["service", "handler", "controller", "middleware", "queue", "worker", "cron", "scheduler"],
        "data": ["database", "schema", "migration", "query", "orm", "model", "seed", "etl", "pipeline", "mysql", "postgres", "sqlite"],
        "auth": ["auth", "login", "session", "token", "oauth", "permission", "role", "access control"],
        "infra": ["deploy", "ci", "cd", "docker", "container", "kubernetes", "terraform", "config", "env"],
        "testing": ["test", "spec", "coverage", "mock", "stub", "fixture", "regression"],
        "security": ["security", "vulnerability", "cve", "sanitize", "encrypt", "hash", "xss", "csrf"],
    }
    for domain, tokens in _DOMAIN_SIGNALS.items():
        if any(t in text for t in tokens):
            domains.append(domain)

    _TECH_SIGNALS: dict[str, list[str]] = {
        "python": ["python", "pytest", "django", "flask", "fastapi", "celery"],
        "javascript": ["javascript", "js", "typescript", "ts", "node", "react", "vue", "next", "svelte"],
        "sql": ["sql", "postgres", "mysql", "sqlite", "database"],
        "go": ["go ", "golang"],
        "rust": ["rust", "cargo"],
    }
    for tech, tokens in _TECH_SIGNALS.items():
        if any(t in text for t in tokens):
            tech_stack.append(tech)

    if any(t in text for t in ["bug", "fix", "regression", "broken", "crash", "error", "failure"]):
        change_type = "bugfix"
    elif any(t in text for t in ["refactor", "restructure", "reorganize", "rename", "move", "split"]):
        change_type = "refactor"
    elif any(t in text for t in ["migration", "upgrade", "port", "migrate"]):
        change_type = "migration"
    elif any(t in text for t in ["security", "vulnerability", "cve", "patch"]):
        change_type = "security"
    elif any(t in text for t in ["test", "spec", "coverage"]):
        change_type = "testing"

    if not domains:
        domains = ["general"]

    return {
        "domains": domains,
        "tech_stack": tech_stack or ["unspecified"],
        "change_type": change_type,
    }


_DOMAIN_CONSIDERATIONS: dict[str, str] = {
    "api": "- API changes need backward compatibility check. Document endpoint contracts (method, path, request/response shapes).\n- Version endpoints if breaking changes are possible.\n- Add integration tests for new or modified endpoints.",
    "frontend": "- Component changes need visual verification. Screenshot evidence for layout changes.\n- Check responsive behavior if layout is affected.\n- Verify accessibility for interactive elements.",
    "backend": "- Service changes need unit tests at the handler/service boundary.\n- Check error handling paths, not just happy path.\n- Verify idempotency for any write operations.",
    "data": "- Schema changes need migration scripts. Test up and down migrations.\n- Check for data loss scenarios.\n- Verify ORM model alignment with migration.",
    "auth": "- Auth changes need security review. Test both authenticated and unauthenticated access.\n- Verify session/token lifecycle.\n- Check for privilege escalation paths.",
    "infra": "- Infrastructure changes need rollback plan. Document rollback steps.\n- Test in isolated environment first.\n- Verify environment variable handling.",
    "testing": "- Test changes should not alter production behavior. Verify test isolation.\n- Check for flaky test patterns (timing, order dependence).\n- Ensure new tests cover edge cases, not just happy path.",
    "security": "- Security fixes need verification that the vulnerability is actually resolved.\n- Check for similar vulnerabilities in adjacent code.\n- Do not introduce new attack vectors in the fix.",
    "general": "- Confirm scope with stakeholders before implementation.\n- Identify affected modules and potential side effects.\n- Plan verification strategy before starting implementation.",
}

_CHANGE_TYPE_CONSIDERATIONS: dict[str, str] = {
    "bugfix": "- Root cause analysis before fix. Reproduce reliably first.\n- Minimal fix — do not refactor adjacent code while fixing.\n- Add regression test that would have caught the original bug.",
    "refactor": "- Behavior must be preserved. All existing tests must pass without modification.\n- Refactor in small, reviewable steps.\n- No functional changes — if behavior changes, it is not a refactor.",
    "migration": "- Migration must be reversible. Test rollback.\n- Check for data integrity before and after.\n- Plan downtime or migration window if applicable.",
    "security": "- Security patches take priority over feature work.\n- Coordinate disclosure timeline.\n- Verify the fix does not break existing functionality.",
    "testing": "- New tests should fail before the feature exists and pass after.\n- Measure coverage delta.\n- Do not skip assertions to make tests pass.",
}


def _domain_considerations(domains: list[str], change_type: str) -> str:
    """Generate domain- and change-type-specific considerations for the PRD."""
    lines: list[str] = []
    for domain in domains:
        if domain in _DOMAIN_CONSIDERATIONS:
            lines.append(_DOMAIN_CONSIDERATIONS[domain])
    if change_type in _CHANGE_TYPE_CONSIDERATIONS:
        lines.append(_CHANGE_TYPE_CONSIDERATIONS[change_type])
    if not lines:
        lines.append("- Confirm scope before implementation. Identify affected modules and verification strategy.")
    return "\n".join(lines)


_QA_CHECKLISTS: dict[str, str] = {
    "api": "- [ ] API contract verified (method, path, request/response)\n- [ ] Error responses match documented status codes\n- [ ] Backward compatibility confirmed for existing clients",
    "frontend": "- [ ] Visual regression check (screenshot before/after if layout changed)\n- [ ] Responsive behavior verified\n- [ ] Accessibility check for interactive elements",
    "backend": "- [ ] Unit tests at service boundary pass\n- [ ] Error handling paths tested, not just happy path\n- [ ] Idempotency verified for write operations",
    "data": "- [ ] Migration up and down tested\n- [ ] Data integrity verified after migration\n- [ ] ORM model matches new schema",
    "auth": "- [ ] Authenticated and unauthenticated access tested\n- [ ] Session/token lifecycle verified\n- [ ] No privilege escalation paths introduced",
    "infra": "- [ ] Rollback procedure documented and tested\n- [ ] Environment variable handling verified\n- [ ] Deployment succeeds in isolated environment",
    "testing": "- [ ] New tests are isolated (no order/timing dependence)\n- [ ] Edge cases covered, not just happy path\n- [ ] Tests fail before feature and pass after",
    "security": "- [ ] Original vulnerability verified as resolved\n- [ ] Adjacent code checked for similar vulnerabilities\n- [ ] No new attack vectors introduced",
    "general": "- [ ] Scope matches PRD acceptance criteria\n- [ ] Side effects on adjacent modules checked\n- [ ] Verification commands documented",
}

_QA_CHANGE_CHECKLISTS: dict[str, str] = {
    "bugfix": "- [ ] Bug reproduced before fix\n- [ ] Fix is minimal (no unrelated changes)\n- [ ] Regression test added that catches the original bug",
    "refactor": "- [ ] All existing tests pass without modification\n- [ ] No behavioral changes introduced\n- [ ] Refactored code is simpler or clearer than before",
    "migration": "- [ ] Migration reversible (rollback tested)\n- [ ] Data integrity verified before and after\n- [ ] Downtime plan documented if applicable",
    "security": "- [ ] Vulnerability confirmed fixed\n- [ ] No functionality broken by the fix\n- [ ] Disclosure timeline coordinated",
    "testing": "- [ ] Coverage delta measured and positive\n- [ ] No assertions skipped to make tests pass\n- [ ] Test data properly managed and isolated",
}


def _qa_checklist(domains: list[str], change_type: str) -> str:
    """Generate domain- and change-type-specific QA checklist items."""
    lines: list[str] = []
    for domain in domains:
        if domain in _QA_CHECKLISTS:
            lines.append(_QA_CHECKLISTS[domain])
    if change_type in _QA_CHANGE_CHECKLISTS:
        lines.append(_QA_CHANGE_CHECKLISTS[change_type])
    if not lines:
        lines.append("- [ ] Behavior matches PRD acceptance criteria")
    return "\n".join(lines)


_ARCH_CONSIDERATIONS: dict[str, str] = {
    "api": "- API changes may require coordinated client updates. Consider versioning strategy.\n- Document endpoint contracts before implementation.\n- Plan for backward compatibility or deprecation timeline.",
    "frontend": "- Component architecture should follow existing patterns in the codebase.\n- State management changes need careful review for side effects.\n- Consider code-splitting impact for new pages/features.",
    "backend": "- Service boundaries should remain clear. Avoid cross-cutting concerns.\n- Queue/async work needs idempotency and retry strategy.\n- Plan for observability: logging, metrics, tracing.",
    "data": "- Schema changes are hard to reverse in production. Plan migrations carefully.\n- Consider indexing strategy for new query patterns.\n- Data integrity constraints should be enforced at the DB level when possible.",
    "auth": "- Auth changes affect all users. Plan for gradual rollout.\n- Token/session storage changes need performance testing.\n- Consider audit logging for auth events.",
    "infra": "- Infrastructure changes should be reproducible (IaC).\n- Plan for rollback: blue-green, canary, or feature flags.\n- Monitor for deployment failures and have alerting in place.",
    "security": "- Security architecture should follow least-privilege principle.\n- Plan for security testing (SAST, DAST, dependency scanning).\n- Document threat model for the changed components.",
    "testing": "- Test architecture should support the team pattern selected above.\n- Consider test pyramid balance for the affected domains.\n- Plan for test data management and isolation.",
    "general": "- Confirm the team pattern above matches the actual complexity of the work.\n- If the work is simpler than expected, the plan stage can reduce the pattern.",
}


def _architecture_considerations(domains: list[str], pattern: str) -> str:
    """Generate architecture considerations based on detected domains."""
    lines: list[str] = []
    for domain in domains:
        if domain in _ARCH_CONSIDERATIONS:
            lines.append(_ARCH_CONSIDERATIONS[domain])
    if not lines:
        lines.append("- Confirm the team pattern above matches the actual complexity of the work.")
    return "\n".join(lines)


def _slugify_objective(objective: str) -> str:
    """Generate a task-id slug from the objective string."""
    import re
    # take first ~6 meaningful words
    words = re.sub(r"[^a-z0-9\s-]", "", objective.lower()).split()
    stop = {"a", "an", "the", "to", "for", "in", "on", "of", "and", "or", "is",
            "it", "with", "from", "by", "that", "this", "be", "are", "was", "were"}
    meaningful = [w for w in words if w not in stop][:6]
    slug = "-".join(meaningful) if meaningful else "task"
    return slug[:64]


_HIGH_RISK_SIGNALS = frozenset({
    "migration", "refactor", "rewrite", "migrate", "database", "schema",
    "breaking", "security", "auth", "authentication", "authorization",
    "payment", "billing", "production", "deploy", "rollback",
})
_LOW_RISK_SIGNALS = frozenset({
    "typo", "rename", "format", "whitespace", "comment", "docs",
    "readme", "lint", "style", "cosmetic", "label", "color",
})


def _estimate_risk(objective: str) -> str:
    """Estimate risk level from objective keywords."""
    text = objective.lower()
    if any(s in text for s in _HIGH_RISK_SIGNALS):
        return "high"
    if any(s in text for s in _LOW_RISK_SIGNALS):
        return "low"
    return "medium"


def _detect_project_type(task_dir: Path) -> dict[str, Any]:
    """Detect project type by scanning ancestor directories for file-system signals."""
    _PROJECT_MARKERS: dict[str, dict[str, list[str]]] = {
        "nextjs": {
            "files": ["next.config.js", "next.config.mjs", "next.config.ts"],
            "dirs": ["app", "src/app"],
            "extras": ["package.json"],
        },
        "react": {
            "files": [],
            "dirs": ["src/components", "src/pages", "src/App.tsx", "src/App.jsx"],
            "extras": ["package.json"],
        },
        "fastapi": {
            "files": [],
            "dirs": [],
            "extras": ["requirements.txt", "pyproject.toml"],
            "content_patterns": ["from fastapi", "import fastapi"],
        },
        "django": {
            "files": ["manage.py"],
            "dirs": [],
            "extras": ["requirements.txt"],
        },
        "flask": {
            "files": [],
            "dirs": [],
            "extras": ["requirements.txt"],
            "content_patterns": ["from flask", "import flask"],
        },
        "python-cli": {
            "files": ["setup.py", "setup.cfg", "pyproject.toml"],
            "dirs": [],
            "extras": [],
        },
        "express": {
            "files": [],
            "dirs": [],
            "extras": ["package.json"],
            "content_patterns": ["from \"express\"", "require(\"express\")"],
        },
        "go-service": {
            "files": ["go.mod"],
            "dirs": [],
            "extras": [],
        },
        "rust-project": {
            "files": ["Cargo.toml"],
            "dirs": [],
            "extras": [],
        },
    }

    # Walk up from task_dir looking for project root signals
    scan_dir = task_dir
    project_root: Path | None = None
    detected: list[str] = []
    package_json_data: dict | None = None

    for _ in range(8):  # max 8 levels up
        if scan_dir == scan_dir.parent:
            break
        # Check for project markers at this level
        if (scan_dir / "package.json").exists():
            project_root = scan_dir
            try:
                raw = (scan_dir / "package.json").read_text(encoding="utf-8")
                package_json_data = __import__("json").loads(raw)
            except (OSError, ValueError):
                package_json_data = {}
            break
        if (scan_dir / "pyproject.toml").exists() or (scan_dir / "requirements.txt").exists():
            project_root = scan_dir
            break
        if (scan_dir / "go.mod").exists() or (scan_dir / "Cargo.toml").exists():
            project_root = scan_dir
            break
        if (scan_dir / "manage.py").exists():
            project_root = scan_dir
            break
        scan_dir = scan_dir.parent

    if project_root is None:
        return {"project_type": "unknown", "project_root": None, "framework": None, "language": None}

    # Detect specific types
    for ptype, markers in _PROJECT_MARKERS.items():
        matched = False
        for fname in markers.get("files", []):
            if (project_root / fname).exists():
                matched = True
                break
        if not matched:
            for dname in markers.get("dirs", []):
                if (project_root / dname).exists():
                    matched = True
                    break
        if not matched:
            for extra in markers.get("extras", []):
                if not (project_root / extra).exists():
                    matched = False
                    break
                # Extra file exists, check content patterns if any
                cpats = markers.get("content_patterns", [])
                if cpats and extra:
                    try:
                        content = (project_root / extra).read_text(encoding="utf-8").lower()
                        if any(p.lower() in content for p in cpats):
                            matched = True
                            break
                    except OSError:
                        pass
                else:
                    matched = True
        if matched:
            detected.append(ptype)

    # Refine using package.json dependencies
    framework: str | None = None
    language: str | None = None

    if package_json_data:
        deps = {**package_json_data.get("dependencies", {}), **package_json_data.get("devDependencies", {})}
        if "next" in deps:
            detected = ["nextjs"]
            framework = "Next.js"
        elif "@tanstack/start" in deps or "vinxi" in deps:
            detected = ["tanstack-start"]
            framework = "TanStack Start"
        elif "react" in deps:
            detected = ["react"]
            framework = "React"
        if "typescript" in deps or (project_root / "tsconfig.json").exists():
            language = "TypeScript"
        else:
            language = "JavaScript"

    if (project_root / "pyproject.toml").exists():
        try:
            content = (project_root / "pyproject.toml").read_text(encoding="utf-8").lower()
            if "fastapi" in content and "fastapi" not in detected:
                detected.insert(0, "fastapi")
                framework = "FastAPI"
            elif "django" in content and "django" not in detected:
                detected.insert(0, "django")
                framework = "Django"
            elif "flask" in content and "flask" not in detected:
                detected.insert(0, "flask")
                framework = "Flask"
        except OSError:
            pass
        if language is None:
            language = "Python"

    if (project_root / "go.mod").exists():
        language = language or "Go"
        if "go-service" not in detected:
            detected.append("go-service")
    if (project_root / "Cargo.toml").exists():
        language = language or "Rust"
        if "rust-project" not in detected:
            detected.append("rust-project")

    # Set framework for marker-based detections (Django, etc.)
    _MARKER_FRAMEWORKS: dict[str, str] = {
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
        "nextjs": "Next.js",
        "tanstack-start": "TanStack Start",
        "react": "React",
        "express": "Express",
    }
    if framework is None:
        for dtype in detected:
            if dtype in _MARKER_FRAMEWORKS:
                framework = _MARKER_FRAMEWORKS[dtype]
                break
    if language is None and project_root is not None:
        # Infer language from project markers
        _LANG_MAP: dict[str, str] = {
            "nextjs": "JavaScript",
            "tanstack-start": "JavaScript",
            "react": "JavaScript",
            "express": "JavaScript",
            "fastapi": "Python",
            "django": "Python",
            "flask": "Python",
            "python-cli": "Python",
        }
        for dtype in detected:
            if dtype in _LANG_MAP:
                language = _LANG_MAP[dtype]
                break

    project_type = detected[0] if detected else "generic"
    return {
        "project_type": project_type,
        "project_root": str(project_root),
        "framework": framework,
        "language": language,
        "all_types": detected,
    }


def _project_type_considerations(project_info: dict[str, Any]) -> str:
    """Generate project-type-specific considerations for drafts."""
    ptype = project_info.get("project_type", "unknown")
    framework = project_info.get("framework")
    language = project_info.get("language")

    _PROJECT_NOTES: dict[str, str] = {
        "nextjs": (
            "- Next.js: prefer App Router patterns (app/ directory) over Pages Router.\n"
            "- Server Components by default; add 'use client' only when needed.\n"
            "- Use Next.js built-in data fetching (fetch with revalidate) over useEffect patterns.\n"
            "- Consider middleware for auth/routing logic.\n"
        ),
        "react": (
            "- React: functional components with hooks.\n"
            "- State management: prefer built-in useState/useReducer; add external lib only when justified.\n"
            "- Follow component composition over inheritance.\n"
        ),
        "tanstack-start": (
            "- TanStack Start: full-stack React framework built on Vinxi.\n"
            "- Use file-based routing under app/routes/.\n"
            "- Server Functions for data loading/mutations (createServerFn).\n"
            "- Prefer TanStack Router patterns over manual routing.\n"
        ),
        "fastapi": (
            "- FastAPI: use dependency injection for DB sessions, auth, and config.\n"
            "- Pydantic models for request/response validation.\n"
            "- APIRouter for endpoint grouping.\n"
            "- Use async handlers for I/O-bound, sync for CPU-bound.\n"
        ),
        "django": (
            "- Django: follow MTV pattern (Model-Template-View).\n"
            "- Use Django ORM; avoid raw SQL unless necessary.\n"
            "- Migrations should be reversible.\n"
            "- Use Django forms for validation.\n"
        ),
        "flask": (
            "- Flask: use Blueprints for route organization.\n"
            "- Application factory pattern for testability.\n"
            "- Prefer Flask-SQLAlchemy for database access.\n"
        ),
        "express": (
            "- Express: use middleware chain for cross-cutting concerns.\n"
            "- Router modules for endpoint grouping.\n"
            "- Error handling middleware as last in the chain.\n"
        ),
        "go-service": (
            "- Go: follow standard project layout.\n"
            "- Interface-based design for testability.\n"
            "- Use context.Context for cancellation/timeouts.\n"
            "- Prefer stdlib HTTP handler patterns.\n"
        ),
        "rust-project": (
            "- Rust: leverage the type system for correctness.\n"
            "- Prefer Result<T, E> over unwrap() in library code.\n"
            "- Use cargo clippy and cargo test as quality gates.\n"
        ),
    }

    lines: list[str] = []
    if ptype in _PROJECT_NOTES:
        lines.append(_PROJECT_NOTES[ptype])
    if framework and framework.lower() != ptype:
        for key, note in _PROJECT_NOTES.items():
            if key in framework.lower():
                lines.append(note)
                break
    if not lines:
        if language:
            lines.append(f"- Detected language: {language}. Follow {language} best practices and conventions.")
        else:
            lines.append("- No specific project framework detected. Follow general best practices for the detected tech stack.")
    return "\n".join(lines)


def _select_team_architecture(objective: str, risk_level: str) -> dict[str, Any]:
    text = objective.lower()
    if risk_level == "high" or any(token in text for token in ["migration", "refactor", "architecture", "security"]):
        pattern = "fan-out/fan-in + producer-reviewer"
        rationale = "High-risk or architecture-heavy work benefits from parallel discovery followed by independent review."
    elif any(token in text for token in ["bug", "fix", "qa", "test", "regression"]):
        pattern = "pipeline + producer-reviewer"
        rationale = "Debugging work should flow from reproduction to minimal fix to regression review."
    else:
        pattern = "producer-reviewer + pipeline"
        rationale = "Default ForgeFlow work needs a useful draft, then review, then staged execution."
    return {"pattern": pattern, "rationale": rationale}


def _write_new_text(path: Path, content: str, *, allow_existing: bool = False) -> None:
    if path.exists() and not allow_existing:
        raise RuntimeViolation(f"init refuses to overwrite existing generated draft: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _init_markdown_drafts(*, task_dir: Path, project_root: Path, task_id: str, objective: str, risk_level: str, route_name: str) -> list[str]:
    architecture = _select_team_architecture(objective, risk_level)
    domain_info = _analyze_objective_domain(objective)
    project_info = _detect_project_type(project_root)
    pattern = architecture["pattern"]
    rationale = architecture["rationale"]
    domains = domain_info["domains"]
    tech_stack = domain_info["tech_stack"]
    change_type = domain_info["change_type"]
    project_type = project_info["project_type"]
    project_framework = project_info.get("framework") or project_type
    project_language = project_info.get("language") or "unspecified"
    project_notes = _project_type_considerations(project_info)
    feature_slug = _slugify_file_stem(objective)[:48]
    domain_list = ", ".join(domains)
    tech_list = ", ".join(tech_stack)
    drafts = {
        "docs/PRD.md": f"""# PRD — {task_id}

## Objective
{objective}

## Domain Analysis
- **Domains**: {domain_list}
- **Tech Stack**: {tech_list}
- **Change Type**: {change_type}

## Scope
- In scope: {objective}
- Out of scope: unrelated platform rebuilds, database workflow engines, and adapter-specific global config writes.

## Acceptance Criteria
- The task has schema-valid ForgeFlow artifacts.
- The generated drafts are specific enough to guide clarify, plan, qa, review, and finalize stages.
- Evidence is recorded before review approval.

## Domain-Specific Considerations
{_domain_considerations(domains, change_type)}

## Project Context
- **Project Type**: {project_type}
- **Framework**: {project_framework}
- **Language**: {project_language}

## Project-Specific Guidelines
{project_notes}
""",
        "docs/ARCHITECTURE.md": f"""# Architecture Draft — {task_id}

## Selected Team Architecture
Pattern: {pattern}

Rationale: {rationale}

## Domain Context
- **Domains**: {domain_list}
- **Change Type**: {change_type}
- **Risk Level**: {risk_level}

## Project Context
- **Project Type**: {project_type}
- **Framework**: {project_framework}
- **Language**: {project_language}

## Project-Specific Architectural Guidelines
{project_notes}

## Roles
- Planner: decomposes the objective into verifiable tasks and dependencies.
- Implementer: changes the target files against the task document, not chat vibes.
- QA: reproduces failures, verifies fixes, and records regression checks.
- Reviewer: checks evidence, spec gaps, structural risk, and test coverage.

## Flow
1. Clarify scope and assumptions.
2. Plan task breakdown and verification strategy.
3. Execute the next actionable task.
4. QA with reproducible evidence.
5. Review before finalization.

## Architecture Considerations
{_architecture_considerations(domains, pattern)}
""",
        "docs/QA.md": f"""# QA Draft — {task_id}

## Domain Context
- **Domains**: {domain_list}
- **Change Type**: {change_type}

## Verification Strategy
- Start with the narrowest command that proves the changed behavior.
- Add regression checks for every bug or contract gap found during execution.
- Record command, exit code, and relevant output in review evidence.

## Domain-Specific QA Checklist
{_qa_checklist(domains, change_type)}

## Project-Specific QA Notes
- **Project Type**: {project_type}
- **Framework**: {project_framework}
{project_notes}

## Watchpoints
- Empty template output is not enough; generated drafts must mention the actual objective.
- Review must not approve without concrete evidence.
- Keep Claude/Codex adapter details project-local.
""",
        "docs/DECISIONS.md": f"""# Decisions — {task_id}

## ADR-001: Init creates usable drafts
Decision: ForgeFlow init creates task-local PRD, architecture, QA, agent, skill, and pointer drafts.

Reason: A blank scaffold forces the next agent to rediscover intent. A draft makes the handoff executable.

Consequence: Init remains bounded: it drafts the workflow, but does not auto-run clarify/plan/execute.
""",
        "tasks/init-summary.md": f"""# Init Summary — {task_id}

Objective: {objective}
Risk: {risk_level}
Route: {route_name}
Selected architecture: {pattern}

## Generated Drafts
- docs/PRD.md
- docs/ARCHITECTURE.md
- docs/QA.md
- docs/DECISIONS.md
- tasks/feature/{feature_slug}.md
- tasks/qa/{feature_slug}.md
- .claude/agents/*.md
- .claude/skills/*/SKILL.md
- CLAUDE.md

## Next Command
Run status, then execute clarify when ready. Do not skip evidence collection.
""",
        f"tasks/feature/{feature_slug}.md": f"""# Feature Task — {objective}

## Source of Truth
- `brief.json`
- `docs/PRD.md`
- `docs/ARCHITECTURE.md`

## Breakdown
1. Confirm scope and assumptions.
2. Identify target files.
3. Implement the smallest coherent slice.
4. Run focused verification.
5. Record evidence for review.
""",
        f"tasks/qa/{feature_slug}.md": f"""# QA Task — {objective}

## Reproduction
- Capture the command or manual steps that show the current behavior.

## Fix Verification
- Run focused tests first.
- Run broader validation if runtime, schemas, adapters, or generated outputs changed.

## Regression Checklist
- Objective-specific behavior verified.
- No unrelated generated drift.
- Review evidence includes real command output.
""",
        # Agents and skills are now resolved dynamically via harness_profiles
        # based on project type and objective analysis (harness-100 style).
        # The old fixed pipeline (planner/implementer/qa/reviewer) is gone.
    }

    # --- Resolve domain-specific agents and skills ---
    from forgeflow_runtime.harness_profiles import resolve_profile

    profile = resolve_profile(
        objective=objective,
        task_id=task_id,
        route=route_name,
        project_info=project_info,
    )

    # Merge profile agents/skills/CLAUDE.md into drafts
    drafts.update(profile["agents"])
    drafts.update(profile["skills"])
    drafts["CLAUDE.md"] = profile["claude_md"]

    created: list[str] = []
    for relative, content in drafts.items():
        if relative.startswith(".claude/"):
            target = project_root / relative
            # agents/skills are shared across tasks — skip if already present
            if target.exists():
                continue
        else:
            target = task_dir / relative
        _write_new_text(target, content)
        created.append(relative)
    return created


def _bootstrap_plan_ledger(task_id: str, route_name: str) -> dict[str, Any]:
    return {
        "schema_version": "0.2",
        "task_id": task_id,
        "route": route_name,
        "completed_stages": [],
        "completed_gates": [],
        "retries": {},
        "current_task_id": "task-1",
        "tasks": [
            {
                "id": "task-1",
                "title": f"bootstrap {route_name} operator workflow",
                "depends_on": [],
                "files": ["brief.json", "run-state.json", "session-state.json"],
                "parallel_safe": False,
                "status": "in_progress",
                "required_gates": ["validator"],
                "evidence_refs": [],
                "attempt_count": 0,
            }
        ],
    }


def _initial_run_state(task_id: str, route: list[str], plan_ledger: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "0.2",
        "task_id": task_id,
        "current_stage": route[0],
        "status": "not_started",
        "completed_gates": [],
        "failed_gates": [],
        "retries": {},
        "evidence_refs": [],
        "current_task_id": (plan_ledger or {}).get("current_task_id", ""),
        "spec_review_approved": False,
        "quality_review_approved": False,
    }


def init_task(
    task_dir: Path,
    policy: RuntimePolicy,
    *,
    objective: str | None = None,
    task_id: str | None = None,
    risk_level: str | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    task_id = task_id or _slugify_objective(objective or task_dir.name)
    objective = objective or f"Bootstrap {task_id}"
    risk_level = risk_level or _estimate_risk(objective)
    if risk_level not in {"low", "medium", "high"}:
        raise RuntimeViolation(f"unknown risk level: {risk_level}")
    route_name = {"low": "small", "medium": "medium", "high": "high"}[risk_level]
    route = _resolve_route(policy, route_name)
    # project_root defaults to 3 levels up from .forgeflow/tasks/<id>/
    if project_root is None:
        project_root = task_dir.parent.parent.parent.resolve()
    if task_dir.exists():
        existing_artifacts = [path.name for path in task_dir.iterdir()]
        if existing_artifacts:
            raise RuntimeViolation("init refuses to overwrite existing task artifacts")
    task_dir.mkdir(parents=True, exist_ok=True)
    created_artifacts: list[str] = []

    brief_payload = {
        "schema_version": "0.2",
        "task_id": task_id,
        "objective": objective,
        "in_scope": [],
        "out_of_scope": [],
        "constraints": [],
        "acceptance_criteria": [],
        "risk_level": risk_level,
        "route": route_name,
    }
    _write_validated_artifact(task_dir, "brief", brief_payload)
    created_artifacts.append("brief.json")

    run_state = _initial_run_state(task_id, route)
    _write_validated_artifact(task_dir, "run-state", run_state)
    created_artifacts.append("run-state.json")

    checkpoint = _sync_checkpoint(
        task_dir,
        route_name=route_name,
        route=route,
        run_state=run_state,
        plan_ledger=None,
        checkpoint=None,
    )
    created_artifacts.append("checkpoint.json")
    _sync_session_state(
        task_dir,
        route_name=route_name,
        run_state=run_state,
        checkpoint=checkpoint,
        plan_ledger=None,
        session_state=None,
    )
    created_artifacts.append("session-state.json")

    return {
        "task_id": task_id,
        "task_dir": str(task_dir),
        "route": route_name,
        "risk_level": risk_level,
        "created": created_artifacts,
        "next_action": "run clarify to analyze and generate drafts",
    }


def clarify_task(
    task_dir: Path,
    policy: RuntimePolicy,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Analyze the objective, generate markdown drafts, and advance past the clarify stage."""
    brief = _load_validated_artifact(task_dir, "brief")
    objective = brief["objective"]
    task_id = brief["task_id"]
    risk_level = brief.get("risk_level", "medium")
    route_name = brief.get("route", "small")

    if project_root is None:
        project_root = task_dir.parent.parent.parent.resolve()

    # 1. Domain analysis + architecture selection
    domain_info = _analyze_objective_domain(objective)
    _detect_project_type(project_root)
    architecture = _select_team_architecture(objective, risk_level)

    # 2. Generate markdown drafts (docs/, tasks/, agents, skills)
    created_drafts = _init_markdown_drafts(
        task_dir=task_dir,
        project_root=project_root,
        task_id=task_id,
        objective=objective,
        risk_level=risk_level,
        route_name=route_name,
    )

    # 3. Enrich brief with domain analysis results
    brief["in_scope"] = [objective]
    brief["out_of_scope"] = []
    brief["constraints"] = ["initialized from operator CLI"]
    brief["acceptance_criteria"] = ["task artifacts are initialized and schema-valid"]
    _write_validated_artifact(task_dir, "brief", brief)

    # 4. Advance stage: clarify → next
    route = _resolve_route(policy, route_name)
    run_state = _load_validated_artifact(task_dir, "run-state", expected_task_id=task_id)
    advance_result: TransitionResult | None = None
    try:
        advance_result = advance_to_next_stage(
            task_dir, policy, route_name, run_state["current_stage"],
        )
    except RuntimeViolation:
        pass  # single-stage routes may not advance

    # 5. Re-sync checkpoint and session-state
    run_state = _load_validated_artifact(task_dir, "run-state", expected_task_id=task_id)
    plan_ledger = _load_plan_ledger(task_dir, canonical_task_id=task_id)
    checkpoint = _sync_checkpoint(
        task_dir,
        route_name=route_name,
        route=route,
        run_state=run_state,
        plan_ledger=plan_ledger,
        checkpoint=None,
    )
    _sync_session_state(
        task_dir,
        route_name=route_name,
        run_state=run_state,
        checkpoint=checkpoint,
        plan_ledger=plan_ledger,
        session_state=None,
    )

    next_stage = advance_result.next_stage if advance_result else run_state["current_stage"]
    return {
        "task_id": task_id,
        "route": route_name,
        "created_drafts": created_drafts,
        "selected_architecture": architecture["pattern"],
        "current_stage": next_stage,
        "next_action": f"stage advanced to {next_stage}; continue with execute or plan",
    }


def start_task(task_dir: Path, policy: RuntimePolicy, route_name: str) -> dict[str, Any]:
    route = _resolve_route(policy, route_name)
    if task_dir.exists():
        existing_artifacts = [path.name for path in task_dir.iterdir() if path.is_file()]
        if existing_artifacts:
            raise RuntimeViolation("start requires an empty task directory")
    task_dir.mkdir(parents=True, exist_ok=True)
    task_id = task_dir.name.replace("_", "-") or "task"
    created_artifacts: list[str] = []

    brief_payload = _bootstrap_brief(task_id, route_name)
    _write_validated_artifact(task_dir, "brief", brief_payload)
    created_artifacts.append("brief.json")

    if route_name != "small":
        plan_payload = _bootstrap_plan(task_id, route_name)
        _write_validated_artifact(task_dir, "plan", plan_payload)
        created_artifacts.append("plan.json")
        plan_ledger = _bootstrap_plan_ledger(task_id, route_name)
        _write_validated_artifact(task_dir, "plan-ledger", plan_ledger)
        created_artifacts.append("plan-ledger.json")
    else:
        plan_ledger = None

    run_state = {
        "schema_version": "0.2",
        "task_id": task_id,
        "current_stage": route[0],
        "status": "not_started",
        "completed_gates": [],
        "failed_gates": [],
        "retries": {},
        "evidence_refs": [],
        "current_task_id": (plan_ledger or {}).get("current_task_id", ""),
        "spec_review_approved": False,
        "quality_review_approved": False,
    }
    _write_validated_artifact(task_dir, "run-state", run_state)
    created_artifacts.append("run-state.json")

    decision_log = {
        "schema_version": "0.2",
        "task_id": task_id,
        "entries": [],
    }
    _append_decision(
        decision_log,
        actor="orchestrator",
        category="routing",
        decision=f"task bootstrapped: {route_name}",
        rationale="operator initialized a new task directory",
    )
    _write_validated_artifact(task_dir, "decision-log", decision_log)
    created_artifacts.append("decision-log.json")

    checkpoint = _sync_checkpoint(
        task_dir,
        route_name=route_name,
        route=route,
        run_state=run_state,
        plan_ledger=plan_ledger,
        checkpoint=None,
    )
    created_artifacts.append("checkpoint.json")
    _sync_session_state(
        task_dir,
        route_name=route_name,
        run_state=run_state,
        checkpoint=checkpoint,
        plan_ledger=plan_ledger,
        session_state=None,
    )
    created_artifacts.append("session-state.json")

    return {
        "task_id": task_id,
        "task_dir": str(task_dir),
        "route": route_name,
        "current_stage": run_state["current_stage"],
        "created_artifacts": created_artifacts,
        "next_action": checkpoint["next_action"],
    }


def resume_task(task_dir: Path, policy: RuntimePolicy, route_name: str | None = None) -> dict[str, Any]:
    canonical_task_id = _canonical_task_id(task_dir)
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    plan_ledger = _load_plan_ledger(task_dir, canonical_task_id=canonical_task_id)
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
    session_state = _load_session_state(task_dir, canonical_task_id=canonical_task_id)
    if checkpoint is None:
        raise RuntimeViolation("resume requires checkpoint.json")
    if session_state is None:
        raise RuntimeViolation("resume requires session-state.json")
    inferred_route = _infer_route_for_recovery(checkpoint=checkpoint, plan_ledger=plan_ledger, fallback_route=route_name or "small")
    if route_name is not None and route_name != inferred_route:
        raise RuntimeViolation(f"session-state route {inferred_route} does not match requested route {route_name}")
    _validate_checkpoint(
        task_dir,
        checkpoint,
        route_name=inferred_route,
        canonical_task_id=canonical_task_id,
        run_state=run_state,
        plan_ledger=plan_ledger,
    )
    _validate_session_state(
        task_dir,
        session_state,
        route_name=inferred_route,
        run_state=run_state,
        plan_ledger=plan_ledger,
    )
    return {
        "task_id": canonical_task_id,
        "route": inferred_route,
        "current_stage": run_state["current_stage"],
        "current_task_id": _canonical_current_task_id(run_state, plan_ledger),
        "next_action": checkpoint["next_action"],
        "latest_checkpoint_ref": session_state["latest_checkpoint_ref"],
        "run_state_ref": session_state["run_state_ref"],
    }


def status_summary(task_dir: Path, policy: RuntimePolicy, route_name: str | None = None) -> dict[str, Any]:
    resumed = resume_task(task_dir=task_dir, policy=policy, route_name=route_name)
    canonical_task_id = resumed["task_id"]
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
    plan_ledger = _load_plan_ledger(task_dir, canonical_task_id=canonical_task_id)
    if checkpoint is None:
        raise RuntimeViolation("status requires checkpoint.json")
    route = _resolve_route(policy, resumed["route"])
    current_index = route.index(run_state["current_stage"])
    completed_gates = (_plan_ledger_progress(plan_ledger) or run_state).get("completed_gates", [])
    required_gates = [
        policy.stage_gate_map[stage_name]
        for stage_name in route[current_index:]
        if stage_name in policy.stage_gate_map and policy.stage_gate_map[stage_name] not in completed_gates
    ]
    return {
        "task_id": canonical_task_id,
        "route": resumed["route"],
        "current_stage": run_state["current_stage"],
        "current_task_id": _canonical_current_task_id(run_state, plan_ledger),
        "open_blockers": checkpoint.get("open_blockers", []),
        "required_gates": required_gates,
        "latest_review_verdict": _latest_review_verdict(task_dir, canonical_task_id=canonical_task_id),
        "next_action": resumed["next_action"],
    }


def _project_root_for_task_dir(task_dir: Path) -> Path:
    resolved = task_dir.resolve()
    parts = resolved.parts
    if ".forgeflow" in parts:
        index = parts.index(".forgeflow")
        if index > 0:
            return Path(*parts[:index])
    return resolved.parent


def _workflow_for_task_dir(policy: RuntimePolicy, task_dir: Path):
    return _resolve_project_workflow(_project_root_for_task_dir(task_dir), policy)


def _resolve_route(policy: RuntimePolicy, route_name: str, *, workflow: Any | None = None) -> list[str]:
    route = policy.routes.get(route_name)
    if route is None:
        raise RuntimeViolation(f"unknown route: {route_name}")
    stages = [str(stage) for stage in route["stages"]]
    caller_supplied_workflow = workflow is not None
    resolved_workflow = workflow or _workflow_from_runtime_policy(policy)
    workflow_stages = [step.id for step in _workflow_resolve_route(resolved_workflow, route_name)]
    if not caller_supplied_workflow and workflow_stages != stages:
        raise RuntimeViolation(
            f"workflow route {route_name} conflicts with runtime policy route: "
            f"workflow={workflow_stages} policy={stages}"
        )
    return workflow_stages


def advance_to_next_stage(
    task_dir: Path,
    policy: RuntimePolicy,
    route_name: str,
    current_stage: str,
    *,
    execute_immediately: bool = False,
    adapter_target: str = "claude",
    role: str | None = None,
    artifacts_to_stream: list[str] | None = None,
    use_real: bool = False,
    collector: Any | None = None,
) -> TransitionResult:
    workflow = _workflow_for_task_dir(policy, task_dir)
    route = _resolve_route(policy, route_name, workflow=workflow)
    canonical_task_id = _canonical_task_id(task_dir)
    plan_ledger = _require_plan_ledger_for_route(task_dir, route_name, canonical_task_id=canonical_task_id)
    run_state_path = _artifact_path(task_dir, "run-state")
    run_state = _load_validated_artifact(task_dir, "run-state", expected_task_id=canonical_task_id) if run_state_path.exists() else None
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
    session_state = _load_session_state(task_dir, canonical_task_id=canonical_task_id)
    if current_stage not in route:
        raise RuntimeViolation(f"stage {current_stage} is not part of route {route_name}")
    if run_state is not None and run_state.get("current_stage") != current_stage:
        raise RuntimeViolation(
            f"requested current_stage {current_stage} does not match persisted run-state stage {run_state.get('current_stage')}"
        )

    next_stage = next_stage_for_transition(
        route,
        current_stage,
        route_name=route_name,
        workflow=workflow,
        violation_factory=RuntimeViolation,
    )
    missing_artifacts = _missing_artifacts(task_dir, policy.stage_requirements.get(next_stage, []))
    if missing_artifacts:
        raise RuntimeViolation(
            f"missing required artifacts for {next_stage}: {', '.join(missing_artifacts)}"
        )

    for required_artifact in policy.stage_requirements.get(next_stage, []):
        for variant in _artifact_variants(required_artifact):
            variant_path = _artifact_path(task_dir, variant)
            if variant_path.exists():
                _load_validated_artifact(task_dir, variant, expected_task_id=canonical_task_id)

    if run_state is None:
        run_state = _default_run_state(task_dir)

    if checkpoint is not None:
        _validate_checkpoint(
            task_dir,
            checkpoint,
            route_name=route_name,
            canonical_task_id=canonical_task_id,
            run_state=run_state,
            plan_ledger=plan_ledger,
        )

    if next_stage == "finalize":
        required_flags = _required_finalize_flags(policy, route_name)
        missing_flags = [flag for flag in required_flags if not run_state.get(flag, False)]
        if missing_flags:
            raise RuntimeViolation(
                f"finalize requires run-state approval flags: {', '.join(missing_flags)}"
            )
        _merge_completed_parallel_workers(task_dir, run_state)

    staged_run_state = dict(run_state)
    _sync_plan_ledger_gate(plan_ledger, stage_name=current_stage, gate_name=policy.stage_gate_map.get(current_stage))
    staged_run_state["current_stage"] = next_stage
    staged_run_state["status"] = "in_progress"
    if plan_ledger is not None and plan_ledger.get("current_task_id"):
        staged_run_state["current_task_id"] = plan_ledger["current_task_id"]

    execution_payload: dict[str, Any] | None = None
    if execute_immediately:
        from forgeflow_runtime.engine import execute_parallel_workers, execute_stage

        execution_role = role or role_for_stage(next_stage, workflow=workflow, violation_factory=RuntimeViolation)
        workers = staged_run_state.get("workers") if next_stage == "execute" else None
        if isinstance(workers, list) and len(workers) > 1:
            worker_results = execute_parallel_workers(
                task_dir=task_dir,
                task_id=staged_run_state.get("task_id", canonical_task_id),
                route=route_name,
                adapter_target=adapter_target,
                workers=workers,
                use_real=use_real,
            )
            failures = [item for item in worker_results if item["result"].status != "success"]
            if failures:
                reason = "; ".join(
                    f"{item['plan_task_id']}: {item['result'].error or item['result'].status}"
                    for item in failures
                )
                raise RuntimeViolation(f"automatic parallel worker execution failed for {next_stage}: {reason}")
            staged_run_state["workers"] = workers
            execution_payload = {
                "stage": next_stage,
                "role": "worker",
                "adapter": adapter_target,
                "status": "success",
                "use_real": use_real,
                "worker_count": len(worker_results),
                "workers": [item["plan_task_id"] for item in worker_results],
            }
        else:
            result = execute_stage(
                task_dir=task_dir,
                task_id=staged_run_state.get("task_id", canonical_task_id),
                stage=next_stage,
                route=route_name,
                role=execution_role,
                adapter_target=adapter_target,
                artifacts_to_stream=artifacts_to_stream,
                use_real=use_real,
                collector=collector,
            )
            if result.status != "success":
                reason = result.error or f"stage execution returned status={result.status}"
                raise RuntimeViolation(f"automatic execution failed for {next_stage}: {reason}")
            if result.raw_output:
                (task_dir / f"{next_stage}-output.md").write_text(result.raw_output, encoding="utf-8")
            execution_payload = _execution_payload(
                stage=next_stage,
                role=execution_role,
                adapter=adapter_target,
                result=result,
                use_real=use_real,
            )

    run_state = staged_run_state
    _write_validated_artifact(task_dir, "run-state", run_state)
    _write_plan_ledger_if_present(task_dir, plan_ledger)
    checkpoint = _sync_checkpoint(
        task_dir,
        route_name=route_name,
        route=route,
        run_state=run_state,
        plan_ledger=plan_ledger,
        checkpoint=checkpoint,
    )
    _sync_session_state(
        task_dir,
        route_name=route_name,
        run_state=run_state,
        checkpoint=checkpoint,
        plan_ledger=plan_ledger,
        session_state=session_state,
    )

    return TransitionResult(next_stage=next_stage, execution=execution_payload)


def _write_profile_artifact(task_dir: Path, profile: Any) -> None:
    """Write a PipelineProfile as a JSON artifact (no schema validation required)."""
    import dataclasses

    payload = {
        "pipeline_id": profile.pipeline_id,
        "route": profile.route,
        "total_duration_s": profile.total_duration_s,
        "total_cost_usd": profile.total_cost_usd,
        "total_input_tokens": profile.total_input_tokens,
        "total_output_tokens": profile.total_output_tokens,
        "started_at": profile.started_at,
        "finished_at": profile.finished_at,
        "stages": [dataclasses.asdict(s) for s in profile.stages],
    }
    out_path = _artifact_path(task_dir, "pipeline-profile")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, payload)


def _sync_parallel_worktree_plan(
    plan_ledger: dict[str, Any] | None,
    run_state: dict[str, Any],
    decision_log: dict[str, Any],
) -> dict[str, Any] | None:
    """Evaluate whether plan tasks can safely fan out into worker worktrees."""
    if plan_ledger is None:
        return None

    tasks = plan_ledger.get("tasks") or []
    result = _detect_path_conflicts(tasks)
    summary = {
        "parallel_safe": result["parallel_safe"],
        "conflicts": result["conflicts"],
        "worker_count": len(tasks),
    }
    plan_ledger["parallel_execution"] = summary
    run_state["parallel_execution"] = summary

    if summary["parallel_safe"]:
        _append_decision(
            decision_log,
            actor="orchestrator",
            category="execution",
            decision="worker worktrees are safe to create in parallel",
            rationale=f"{summary['worker_count']} plan task(s) have no owned-path conflicts",
        )
    else:
        conflict_bits = [
            f"{conflict['reason']}:{conflict['path']} -> {', '.join(conflict['task_ids'])}"
            for conflict in summary["conflicts"]
        ]
        _append_decision(
            decision_log,
            actor="orchestrator",
            category="execution",
            decision="parallel worker worktrees blocked by path conflicts",
            rationale="; ".join(conflict_bits) or "plan tasks are not parallel safe",
        )

    return summary


def _merge_completed_parallel_workers(task_dir: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    workers = run_state.get("workers")
    if not isinstance(workers, list) or not workers:
        return []
    repo_root = _find_git_root(task_dir)
    if repo_root is None:
        raise RuntimeViolation("parallel worker merge requires a git repository")

    # H7: Only merge completed workers; skip others.
    completed = [(i, w) for i, w in enumerate(workers) if w.get("status") == "completed"]
    if not completed:
        return []

    merge_results: list[dict[str, Any]] = []
    for merge_idx, (orig_idx, worker) in enumerate(completed):
        # C3: After first merge the repo is dirty — skip require_clean for subsequent.
        result = _merge_worker_worktree(
            repo_path=repo_root,
            task_dir=task_dir,
            worker=worker,
            approved=bool(run_state.get("quality_review_approved")),
            require_clean=(merge_idx == 0),
        )
        merge_results.append(result)

    # Record merge results back, including skipped workers
    run_state["workers"] = workers
    run_state["worker_merge_results"] = merge_results

    failures = [item for item in merge_results if item.get("status") != "merged"]
    if failures:
        reason = "; ".join(
            f"{item.get('plan_task_id')}: {item.get('reason') or item.get('status')}"
            for item in failures
        )
        raise RuntimeViolation(f"parallel worker merge blocked: {reason}")
    return merge_results


def _brief_use_worktree(task_dir: Path) -> bool | None:
    brief_path = task_dir / "brief.json"
    if not brief_path.exists():
        return None
    try:
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    value = brief.get("use_worktree")
    return value if isinstance(value, bool) else None


def _allocate_parallel_worker_worktrees(
    task_dir: Path,
    plan_ledger: dict[str, Any] | None,
    run_state: dict[str, Any],
    decision_log: dict[str, Any],
) -> list[dict[str, Any]]:
    """Create worker-scoped worktrees for a parallel-safe execute plan."""
    if plan_ledger is None:
        return []
    summary = run_state.get("parallel_execution") or plan_ledger.get("parallel_execution") or {}
    if not summary.get("parallel_safe"):
        return []
    if _brief_use_worktree(task_dir) is not True:
        return []

    tasks = plan_ledger.get("tasks") or []
    if len(tasks) < 2:
        return []

    repo_root = _find_git_root(task_dir)
    if repo_root is None:
        _append_decision(
            decision_log,
            actor="execute-intelligence",
            category="execute-context",
            decision="parallel worker worktrees skipped — not a git repo",
            rationale="no .git directory found; proceeding without worker worktrees",
        )
        return []

    task_id = str(run_state.get("task_id") or plan_ledger.get("task_id") or task_dir.name)
    workers: list[dict[str, Any]] = []
    allocated_indices: list[int] = []  # H4: track for rollback on partial failure
    try:
        for plan_idx, plan_task in enumerate(tasks):
            plan_task_id = str(plan_task.get("id", "")).strip().replace("/", "-").replace("\\", "-")
            worker_dir = task_dir / "workers" / plan_task_id
            existing_state = worker_dir / "worker-state.json"
            if existing_state.exists():
                try:
                    state_data = json.loads(existing_state.read_text(encoding="utf-8"))
                    workers.append(state_data)
                    continue
                except json.JSONDecodeError:
                    # H6: Corrupt state — back up and re-create
                    backup = existing_state.with_suffix(".corrupt")
                    existing_state.replace(backup)
                except OSError:
                    pass
            worker = _create_worker_worktree(
                task_dir=task_dir,
                repo_path=repo_root,
                task_id=task_id,
                plan_task=plan_task,
            )
            workers.append(worker)
            allocated_indices.append(plan_idx)
    except Exception:
        # H4: Roll back newly-created worktrees on partial allocation failure
        for idx in allocated_indices:
            w = workers[idx] if idx < len(workers) else None
            if w and isinstance(w.get("worktree"), dict):
                wt_path = w["worktree"].get("path")
                if wt_path:
                    try:
                        from forgeflow_runtime.worktree import remove_worktree
                        remove_worktree(str(repo_root), wt_path)
                    except Exception:
                        pass
        raise

    run_state["workers"] = workers
    _append_decision(
        decision_log,
        actor="orchestrator",
        category="execution",
        decision="parallel worker worktrees allocated",
        rationale=f"created or reused {len(workers)} worker artifact set(s) under {task_dir / 'workers'}",
    )
    return workers


def _maybe_create_worktree(
    task_dir: Path,
    run_state: dict[str, Any],
    decision_log: dict[str, Any],
) -> dict | None:
    """Optionally create a git worktree for isolated execution.

    Reads ``use_worktree`` from brief.json.  When the key is missing (null),
    the function records an *action-required* decision entry so the calling
    agent can prompt the user, and returns ``None`` without creating anything.
    When the key is explicitly ``false``, creation is skipped silently.
    When ``true`` (or when brief.json does not exist), proceeds with creation.

    Returns a worktree info dict on success, None otherwise (non-fatal).
    """
    # --- Check brief.json for user preference ---
    brief_path = task_dir / "brief.json"
    if brief_path.exists():
        try:
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            brief = {}
    else:
        brief = {}

    use_worktree = brief.get("use_worktree")
    if use_worktree is None:
        # Key absent — ask the user via decision-log action-required entry
        _append_decision(
            decision_log,
            actor="execute-intelligence",
            category="execute-context",
            decision="worktree preference not set — ask user",
            rationale=(
                "brief.json has no 'use_worktree' field. "
                "Ask the user whether to isolate execution in a git worktree, "
                "then write 'use_worktree': true/false to brief.json and re-run execute."
            ),
        )
        return None
    if not use_worktree:
        # Explicit user preference: execute on the main tree without adding
        # noise to decision-log stage ordering.
        return None

    # --- Proceed with worktree creation ---
    repo_root = _find_git_root(task_dir)
    if repo_root is None:
        _append_decision(
            decision_log,
            actor="execute-intelligence",
            category="execute-context",
            decision="worktree skipped — not a git repo",
            rationale="no .git directory found; proceeding on main tree",
        )
        return None

    task_id = run_state.get("task_id", "unknown")
    branch = f"ff-exec-{task_id}"

    try:
        session = _create_worktree(str(repo_root), branch)
        wt_info = {
            "path": session.worktree_path,
            "branch": session.branch,
            "base_commit": session.base_commit,
            "active": True,
        }
        run_state["worktree"] = wt_info
        _append_decision(
            decision_log,
            actor="execute-intelligence",
            category="execute-context",
            decision="worktree created for isolated execution",
            rationale=f"detached worktree at {session.worktree_path} (base: {session.base_commit[:8]})",
        )
        return wt_info
    except Exception as exc:
        # Non-fatal: worktree creation failure should not block execution
        _append_decision(
            decision_log,
            actor="execute-intelligence",
            category="execute-context",
            decision="worktree creation skipped",
            rationale=f"could not create worktree: {exc}; proceeding on main tree",
        )
        return None


def _cleanup_worktree(
    task_dir: Path,
    wt_info: dict,
    run_state: dict[str, Any],
    decision_log: dict[str, Any],
) -> None:
    """Remove the worktree after execute stage completes."""
    repo_root = _find_git_root(task_dir)
    if repo_root is None:
        return

    wt_path = wt_info.get("path", "")
    if not wt_path:
        run_state.setdefault("worktree", {})
        run_state["worktree"]["active"] = False
        return

    try:
        success = _remove_worktree(str(repo_root), wt_path)
        status = "removed" if success else "remove failed (manual cleanup needed)"
    except Exception as exc:
        status = f"remove failed: {exc}"

    run_state.setdefault("worktree", {})
    run_state["worktree"]["active"] = False
    _append_decision(
        decision_log,
        actor="execute-intelligence",
        category="execute-context",
        decision=f"worktree {status}",
        rationale=f"worktree at {wt_path}: {status}",
    )


def _find_git_root(start: Path) -> Path | None:
    """Walk up from *start* to find a directory containing .git/."""
    current = start.resolve()
    for _ in range(10):  # safety bound
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def run_route(task_dir: Path, policy: RuntimePolicy, route_name: str) -> dict[str, Any]:
    from forgeflow_runtime.profiling import ProfilingCollector

    workflow = _workflow_for_task_dir(policy, task_dir)
    route = _resolve_route(policy, route_name, workflow=workflow)
    canonical_task_id = _canonical_task_id(task_dir)
    plan_ledger = _require_plan_ledger_for_route(task_dir, route_name, canonical_task_id=canonical_task_id)
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    decision_log = _ensure_decision_log(task_dir, canonical_task_id=canonical_task_id)
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
    session_state = _load_session_state(task_dir, canonical_task_id=canonical_task_id)
    collector = ProfilingCollector(pipeline_id=canonical_task_id, route=route_name)
    if plan_ledger is not None and plan_ledger.get("current_task_id"):
        run_state["current_task_id"] = plan_ledger["current_task_id"]
    if checkpoint is not None:
        _validate_checkpoint(
            task_dir,
            checkpoint,
            route_name=route_name,
            canonical_task_id=canonical_task_id,
            run_state=run_state,
            plan_ledger=plan_ledger,
        )
    resume_from_stage = run_state.get("current_stage")
    start_index = resume_start_index(
        run_state,
        route,
        stage_gate_map=policy.stage_gate_map,
        violation_factory=RuntimeViolation,
        plan_ledger=plan_ledger,
    )

    route_entry = route_entry_decision(
        route_name=route_name,
        start_index=start_index,
        resume_from_stage=resume_from_stage,
        route_length=len(route),
    )

    if route_entry.already_complete:
        _append_decision(
            decision_log,
            actor="orchestrator",
            category="routing",
            decision=route_entry.decision,
            rationale=route_entry.rationale,
        )
        _write_validated_artifact(task_dir, "decision-log", decision_log)
        _write_validated_artifact(task_dir, "run-state", run_state)
        checkpoint = _sync_checkpoint(
            task_dir,
            route_name=route_name,
            route=route,
            run_state=run_state,
            plan_ledger=plan_ledger,
            checkpoint=checkpoint,
        )
        _sync_session_state(
            task_dir,
            route_name=route_name,
            run_state=run_state,
            checkpoint=checkpoint,
            plan_ledger=plan_ledger,
            session_state=session_state,
        )
        profile = collector.build()
        _write_profile_artifact(task_dir, profile)
        return build_route_result(run_state, _plan_ledger_progress(plan_ledger))

    _append_decision(
        decision_log,
        actor="orchestrator",
        category="routing",
        decision=route_entry.decision,
        rationale=route_entry.rationale,
    )

    for stage_name in route_iteration_stages(route, start_index):
        # Profiling: start stage timer
        collector._start_stage(stage_name, model="orchestrator")

        missing_artifacts = _missing_artifacts(task_dir, policy.stage_requirements.get(stage_name, []))
        if missing_artifacts:
            raise RuntimeViolation(
                f"missing required artifacts for {stage_name}: {', '.join(missing_artifacts)}"
            )

        run_state["current_stage"] = stage_name
        run_state["status"] = "in_progress"
        _sync_review_flags(task_dir, run_state, canonical_task_id=canonical_task_id)
        _enforce_stage_gate(task_dir, policy, stage_name, canonical_task_id=canonical_task_id)
        _record_gate(run_state, stage_name, stage_gate_map=policy.stage_gate_map, plan_ledger=plan_ledger)
        _sync_plan_ledger_gate(plan_ledger, stage_name=stage_name, gate_name=policy.stage_gate_map.get(stage_name))

        if stage_name == "execute" and not _artifact_path(task_dir, "decision-log").exists():
            raise RuntimeViolation("execute requires decision-log.json to exist")

        # --- Optional git worktree isolation for execute stage ---
        _active_worktree: dict | None = None
        if stage_name == "execute":
            _sync_parallel_worktree_plan(plan_ledger, run_state, decision_log)
            _parallel_workers = _allocate_parallel_worker_worktrees(task_dir, plan_ledger, run_state, decision_log)
            if not _parallel_workers:
                _active_worktree = _maybe_create_worktree(task_dir, run_state, decision_log)

        # --- Execute Intelligence: inject task context + progress + stuck detection ---
        if stage_name == "execute":
            # Build and log execute context for the current task
            exe_ctx = _build_execute_context(task_dir)
            if exe_ctx.get("current_task") is not None:
                _append_decision(
                    decision_log,
                    actor="execute-intelligence",
                    category="execute-context",
                    decision=f"task context: {exe_ctx.get('task_index', '?')} — {exe_ctx.get('current_task', {}).get('title', '?')}",
                    rationale=_format_execute_prompt(exe_ctx),
                )

            # Progress tracking
            progress = _calculate_progress(plan_ledger)
            run_state["progress"] = progress

            # Anomaly detection
            anomaly_warnings = _detect_progress_anomaly(plan_ledger, run_state)
            if anomaly_warnings:
                _append_decision(
                    decision_log,
                    actor="progress-tracker",
                    category="anomaly-warning",
                    decision="progress anomaly detected",
                    rationale="; ".join(anomaly_warnings),
                )

            # Stuck detection
            stuck_signals = _detect_stuck(task_dir)
            if stuck_signals:
                stuck_report = _format_stuck_report(stuck_signals)
                _append_decision(
                    decision_log,
                    actor="stuck-detector",
                    category="stuck-signal",
                    decision=f"stuck detected ({len(stuck_signals)} signals)",
                    rationale=stuck_report,
                )
                if _should_escalate(stuck_signals):
                    run_state["status"] = "blocked"
                    _append_decision(
                        decision_log,
                        actor="stuck-detector",
                        category="escalation",
                        decision="execution blocked due to stuck signals",
                        rationale="Critical stuck signal detected. Agent should reconsider approach or ask for guidance.",
                    )

        if stage_name in {"spec-review", "quality-review"}:
            review_artifact = _latest_review_ref(task_dir)
            review_verdict = _latest_review_verdict(task_dir, canonical_task_id=canonical_task_id)
            _sync_plan_ledger_review(plan_ledger, review_artifact=review_artifact, verdict=review_verdict)

        if stage_name == "finalize":
            required_flags = _required_finalize_flags(policy, route_name)
            missing_flags = [flag for flag in required_flags if not run_state.get(flag, False)]
            if missing_flags:
                raise RuntimeViolation(
                    f"finalize requires run-state approval flags: {', '.join(missing_flags)}"
                )

        status, final_status = stage_completion_status(
            stage_name,
            existing_final_status=run_state.get("final_status"),
        )
        run_state["status"] = status
        if final_status is not None:
            run_state["final_status"] = final_status
        if stage_name in {"finalize", "long-run"}:
            _finalize_plan_ledger_task(plan_ledger)

        _append_decision(
            decision_log,
            actor="orchestrator",
            category="stage-transition",
            decision=f"stage entered: {stage_name}",
            rationale=f"route {route_name} progressed to {stage_name}",
        )
        _write_validated_artifact(task_dir, "run-state", run_state)
        _write_validated_artifact(task_dir, "decision-log", decision_log)
        _write_plan_ledger_if_present(task_dir, plan_ledger)

        # --- Worktree cleanup after execute stage ---
        if stage_name == "execute" and _active_worktree is not None:
            _cleanup_worktree(task_dir, _active_worktree, run_state, decision_log)

        # Profiling: record completed stage
        from forgeflow_runtime.executor import RunTaskResult
        stage_status = run_state.get("status", "unknown")
        collector.record_stage(
            RunTaskResult(
                status=stage_status,
                token_usage={"input": 0, "output": 0},
                error=None,
            )
        )

        checkpoint = _sync_checkpoint(
            task_dir,
            route_name=route_name,
            route=route,
            run_state=run_state,
            plan_ledger=plan_ledger,
            checkpoint=checkpoint,
        )
        session_state = _sync_session_state(
            task_dir,
            route_name=route_name,
            run_state=run_state,
            checkpoint=checkpoint,
            plan_ledger=plan_ledger,
            session_state=session_state,
        )

    # Save profiling profile as artifact
    profile = collector.build()
    _write_profile_artifact(task_dir, profile)

    return build_route_result(run_state, _plan_ledger_progress(plan_ledger))


def retry_stage(task_dir: Path, stage_name: str, max_retries: int = 2) -> dict[str, Any]:
    canonical_task_id = _canonical_task_id(task_dir)
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    decision_log = _ensure_decision_log(task_dir, canonical_task_id=canonical_task_id)
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
    session_state = _load_session_state(task_dir, canonical_task_id=canonical_task_id)
    plan_ledger = _load_plan_ledger(task_dir, canonical_task_id=canonical_task_id)
    if plan_ledger is not None and plan_ledger.get("current_task_id"):
        run_state["current_task_id"] = plan_ledger["current_task_id"]
    retries_source = (_plan_ledger_progress(plan_ledger) or run_state)["retries"]
    current = int(retries_source.get(stage_name, 0))
    if current >= max_retries:
        raise RuntimeViolation(f"retry budget exceeded for {stage_name}: {current}/{max_retries}")

    if plan_ledger is None:
        run_state["retries"][stage_name] = current + 1
    else:
        _sync_plan_ledger_retry(plan_ledger, stage_name=stage_name)
    run_state["current_stage"] = stage_name
    run_state["status"] = "in_progress"
    _append_decision(
        decision_log,
        actor="orchestrator",
        category="recovery",
        decision=f"retry requested: {stage_name}",
        rationale=f"bounded retry {current + 1}/{max_retries}",
    )
    _write_validated_artifact(task_dir, "run-state", run_state)
    _write_validated_artifact(task_dir, "decision-log", decision_log)
    _write_plan_ledger_if_present(task_dir, plan_ledger)
    recovery_route = _infer_route_for_recovery(checkpoint=checkpoint, plan_ledger=plan_ledger, fallback_route="small")
    recovery_route_stages = _resolve_route(load_runtime_policy(REPO_ROOT), recovery_route)
    _assert_stage_in_route(route_name=recovery_route, route=recovery_route_stages, stage_name=run_state["current_stage"])
    checkpoint = _sync_checkpoint(
        task_dir,
        route_name=recovery_route,
        route=recovery_route_stages,
        run_state=run_state,
        plan_ledger=plan_ledger,
        checkpoint=checkpoint,
    )
    _sync_session_state(
        task_dir,
        route_name=recovery_route,
        run_state=run_state,
        checkpoint=checkpoint,
        plan_ledger=plan_ledger,
        session_state=session_state,
    )
    result = dict(run_state)
    result["retries"] = dict((_plan_ledger_progress(plan_ledger) or run_state)["retries"])
    return result


def step_back(task_dir: Path, policy: RuntimePolicy, route_name: str, current_stage: str) -> dict[str, Any]:
    route = _resolve_route(policy, route_name)
    if current_stage not in route:
        raise RuntimeViolation(f"stage {current_stage} is not part of route {route_name}")
    index = route.index(current_stage)
    if index == 0:
        raise RuntimeViolation(f"cannot step back before first stage of route {route_name}")

    previous_stage = route[index - 1]
    removed_stages = route[index:]
    canonical_task_id = _canonical_task_id(task_dir)
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    decision_log = _ensure_decision_log(task_dir, canonical_task_id=canonical_task_id)
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
    session_state = _load_session_state(task_dir, canonical_task_id=canonical_task_id)
    plan_ledger = _load_plan_ledger(task_dir, canonical_task_id=canonical_task_id)
    if plan_ledger is not None and plan_ledger.get("current_task_id"):
        run_state["current_task_id"] = plan_ledger["current_task_id"]
    _rewind_plan_ledger_progress(
        plan_ledger,
        route=route,
        resume_stage=previous_stage,
        stage_gate_map=policy.stage_gate_map,
    )
    _clear_rewind_review_flags(run_state, removed_stages=removed_stages)
    run_state["current_stage"] = previous_stage
    run_state["status"] = "in_progress"
    _append_decision(
        decision_log,
        actor="orchestrator",
        category="recovery",
        decision=f"step back: {current_stage} -> {previous_stage}",
        rationale="operator requested previous safe stage",
    )
    _write_validated_artifact(task_dir, "run-state", run_state)
    _write_validated_artifact(task_dir, "decision-log", decision_log)
    _write_plan_ledger_if_present(task_dir, plan_ledger)
    checkpoint = _sync_checkpoint(
        task_dir,
        route_name=route_name,
        route=route,
        run_state=run_state,
        plan_ledger=plan_ledger,
        checkpoint=checkpoint,
    )
    _sync_session_state(
        task_dir,
        route_name=route_name,
        run_state=run_state,
        checkpoint=checkpoint,
        plan_ledger=plan_ledger,
        session_state=session_state,
    )
    return run_state


def escalate_route(task_dir: Path, from_route: str) -> dict[str, Any]:
    if from_route not in {"small", "medium", "high"}:
        raise RuntimeViolation(f"unknown route for escalation: {from_route}")
    canonical_task_id = _canonical_task_id(task_dir)
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    decision_log = _ensure_decision_log(task_dir, canonical_task_id=canonical_task_id)
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
    session_state = _load_session_state(task_dir, canonical_task_id=canonical_task_id)
    plan_ledger = _load_plan_ledger(task_dir, canonical_task_id=canonical_task_id)
    if plan_ledger is not None and plan_ledger.get("current_task_id"):
        run_state["current_task_id"] = plan_ledger["current_task_id"]
    run_state["current_stage"] = "clarify"
    run_state["status"] = "blocked"
    _append_decision(
        decision_log,
        actor="orchestrator",
        category="routing",
        decision=f"route escalated: {from_route} -> high",
        rationale="risk or recovery pressure exceeded original route",
    )
    _write_validated_artifact(task_dir, "run-state", run_state)
    _write_validated_artifact(task_dir, "decision-log", decision_log)
    checkpoint = _sync_checkpoint(
        task_dir,
        route_name="high",
        route=_resolve_route(load_runtime_policy(REPO_ROOT), "high"),
        run_state=run_state,
        plan_ledger=plan_ledger,
        checkpoint=checkpoint,
    )
    _sync_session_state(
        task_dir,
        route_name="high",
        run_state=run_state,
        checkpoint=checkpoint,
        plan_ledger=plan_ledger,
        session_state=session_state,
    )
    return run_state
