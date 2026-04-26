from __future__ import annotations

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
from forgeflow_runtime.policy_loader import RuntimePolicy, load_runtime_policy
from forgeflow_runtime.resume_validation import resume_start_index
from forgeflow_runtime.route_execution import route_entry_decision, route_iteration_stages, stage_completion_status
from forgeflow_runtime.stage_transition import next_stage_for_transition
from forgeflow_runtime.task_identity import canonical_task_id as _canonical_task_id
from forgeflow_runtime.task_identity import task_id as _task_id


@dataclass(frozen=True)
class TransitionResult:
    next_stage: str
    execution: dict[str, Any] | None = None


def _execution_payload(*, stage: str, role: str, adapter: str, result: Any, use_real: bool = False) -> dict[str, Any]:
    payload = {
        "stage": stage,
        "role": role,
        "adapter": adapter,
        "execution_mode": "real" if use_real else "stub",
        "status": result.status,
        "artifacts_produced": result.artifacts_produced,
        "token_usage": result.token_usage,
    }
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
        "schema_version": "0.1",
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
    payload["schema_version"] = "0.1"
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
        "schema_version": "0.1",
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
    payload["schema_version"] = "0.1"
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
        "schema_version": "0.1",
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
        "schema_version": "0.1",
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
        "schema_version": "0.1",
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
        "schema_version": "0.1",
        "task_id": task_id,
        "steps": [
            {
                "id": "step-1",
                "objective": f"Prepare {route_name} route artifacts",
                "dependencies": [],
                "expected_output": "brief, run-state, session-state, and route-owned artifacts exist",
                "verification": "python3 scripts/run_orchestrator.py status --task-dir <task-dir> --route <route>",
                "rollback_note": "remove bootstrapped task directory if initialization is invalid",
            }
        ],
    }


def _bootstrap_plan_ledger(task_id: str, route_name: str) -> dict[str, Any]:
    return {
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
        "schema_version": "0.1",
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
    task_id: str,
    objective: str,
    risk_level: str,
) -> dict[str, Any]:
    if risk_level not in {"low", "medium", "high"}:
        raise RuntimeViolation(f"unknown risk level: {risk_level}")
    route_name = {"low": "small", "medium": "medium", "high": "large_high_risk"}[risk_level]
    route = _resolve_route(policy, route_name)
    if task_dir.exists():
        existing_artifacts = [path.name for path in task_dir.iterdir() if path.is_file()]
        if existing_artifacts:
            raise RuntimeViolation("init refuses to overwrite existing task artifacts")
    task_dir.mkdir(parents=True, exist_ok=True)

    brief_payload = {
        "schema_version": "0.1",
        "task_id": task_id,
        "objective": objective,
        "in_scope": [objective],
        "out_of_scope": [],
        "constraints": ["initialized from operator CLI"],
        "acceptance_criteria": ["task artifacts are initialized and schema-valid"],
        "risk_level": risk_level,
    }
    _write_validated_artifact(task_dir, "brief", brief_payload)

    run_state = _initial_run_state(task_id, route)
    _write_validated_artifact(task_dir, "run-state", run_state)

    checkpoint = _sync_checkpoint(
        task_dir,
        route_name=route_name,
        route=route,
        run_state=run_state,
        plan_ledger=None,
        checkpoint=None,
    )
    _sync_session_state(
        task_dir,
        route_name=route_name,
        run_state=run_state,
        checkpoint=checkpoint,
        plan_ledger=None,
        session_state=None,
    )

    return {
        "task_id": task_id,
        "task_dir": str(task_dir),
        "route": route_name,
        "created": ["brief.json", "run-state.json", "checkpoint.json", "session-state.json"],
        "next_action": "run status or execute the clarify stage",
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
        "schema_version": "0.1",
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
        "schema_version": "0.1",
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


def _resolve_route(policy: RuntimePolicy, route_name: str) -> list[str]:
    route = policy.routes.get(route_name)
    if route is None:
        raise RuntimeViolation(f"unknown route: {route_name}")
    return route["stages"]


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
) -> TransitionResult:
    route = _resolve_route(policy, route_name)
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

    next_stage = next_stage_for_transition(route, current_stage, route_name=route_name, violation_factory=RuntimeViolation)
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

    staged_run_state = dict(run_state)
    _sync_plan_ledger_gate(plan_ledger, stage_name=current_stage, gate_name=policy.stage_gate_map.get(current_stage))
    staged_run_state["current_stage"] = next_stage
    staged_run_state["status"] = "in_progress"
    if plan_ledger is not None and plan_ledger.get("current_task_id"):
        staged_run_state["current_task_id"] = plan_ledger["current_task_id"]

    execution_payload: dict[str, Any] | None = None
    if execute_immediately:
        from forgeflow_runtime.engine import execute_stage

        default_role_map = {
            "clarify": "coordinator",
            "plan": "planner",
            "execute": "worker",
            "spec-review": "spec-reviewer",
            "quality-review": "quality-reviewer",
            "finalize": "coordinator",
            "long-run": "worker",
        }
        execution_role = role or default_role_map.get(next_stage)
        if not execution_role:
            raise RuntimeViolation(f"no default role mapping for stage: {next_stage}")
        result = execute_stage(
            task_dir=task_dir,
            task_id=staged_run_state.get("task_id", canonical_task_id),
            stage=next_stage,
            route=route_name,
            role=execution_role,
            adapter_target=adapter_target,
            artifacts_to_stream=artifacts_to_stream,
            use_real=use_real,
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


def run_route(task_dir: Path, policy: RuntimePolicy, route_name: str) -> dict[str, Any]:
    route = _resolve_route(policy, route_name)
    canonical_task_id = _canonical_task_id(task_dir)
    plan_ledger = _require_plan_ledger_for_route(task_dir, route_name, canonical_task_id=canonical_task_id)
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    decision_log = _ensure_decision_log(task_dir, canonical_task_id=canonical_task_id)
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
    session_state = _load_session_state(task_dir, canonical_task_id=canonical_task_id)
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
        return run_state

    _append_decision(
        decision_log,
        actor="orchestrator",
        category="routing",
        decision=route_entry.decision,
        rationale=route_entry.rationale,
    )

    for stage_name in route_iteration_stages(route, start_index):
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

    result = dict(run_state)
    progress = _plan_ledger_progress(plan_ledger) or run_state
    result["completed_gates"] = list(progress.get("completed_gates", []))
    result["retries"] = dict(progress.get("retries", result.get("retries", {})))
    return result


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
    if from_route not in {"small", "medium", "large_high_risk"}:
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
        decision=f"route escalated: {from_route} -> large_high_risk",
        rationale="risk or recovery pressure exceeded original route",
    )
    _write_validated_artifact(task_dir, "run-state", run_state)
    _write_validated_artifact(task_dir, "decision-log", decision_log)
    checkpoint = _sync_checkpoint(
        task_dir,
        route_name="large_high_risk",
        route=_resolve_route(load_runtime_policy(REPO_ROOT), "large_high_risk"),
        run_state=run_state,
        plan_ledger=plan_ledger,
        checkpoint=checkpoint,
    )
    _sync_session_state(
        task_dir,
        route_name="large_high_risk",
        run_state=run_state,
        checkpoint=checkpoint,
        plan_ledger=plan_ledger,
        session_state=session_state,
    )
    return run_state
