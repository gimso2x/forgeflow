from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from forgeflow_runtime.policy_loader import RuntimePolicy, load_runtime_policy


class RuntimeViolation(Exception):
    """Raised when a requested stage transition violates runtime policy."""


@dataclass(frozen=True)
class TransitionResult:
    next_stage: str
    execution: dict[str, Any] | None = None


SCHEMA_BY_ARTIFACT = {
    "brief": "brief",
    "plan": "plan",
    "plan-ledger": "plan-ledger",
    "decision-log": "decision-log",
    "run-state": "run-state",
    "review-report": "review-report",
    "review-report-spec": "review-report",
    "review-report-quality": "review-report",
    "eval-record": "eval-record",
    "checkpoint": "checkpoint",
    "session-state": "session-state",
}

REPO_ROOT = Path(__file__).resolve().parents[1]


def _artifact_path(task_dir: Path, artifact_name: str) -> Path:
    return task_dir / f"{artifact_name}.json"


def _artifact_variants(artifact_name: str) -> list[str]:
    if artifact_name == "review-report":
        return ["review-report", "review-report-spec", "review-report-quality"]
    return [artifact_name]


def _has_artifact(task_dir: Path, artifact_name: str) -> bool:
    return any(_artifact_path(task_dir, variant).exists() for variant in _artifact_variants(artifact_name))


def _missing_artifacts(task_dir: Path, artifact_names: list[str]) -> list[str]:
    return [name for name in artifact_names if not _has_artifact(task_dir, name)]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _schema_validator(schema_name: str) -> Draft202012Validator:
    schema_path = REPO_ROOT / "schemas" / f"{schema_name}.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _schema_name_for_artifact(artifact_name: str) -> str | None:
    return SCHEMA_BY_ARTIFACT.get(artifact_name)


def _validate_artifact_payload(*, artifact_name: str, payload: dict[str, Any], source_name: str) -> None:
    schema_name = _schema_name_for_artifact(artifact_name)
    if schema_name is None:
        return
    errors = sorted(_schema_validator(schema_name).iter_errors(payload), key=lambda err: list(err.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, err.path)) or '<root>'}: {err.message}" for err in errors[:3]
        )
        raise RuntimeViolation(f"{source_name} failed schema validation: {details}")


def _coerce_legacy_artifact_payload(artifact_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if artifact_name != "decision-log":
        return payload

    entries = payload.get("entries")
    if not isinstance(entries, list):
        return payload

    migrated_entries: list[dict[str, Any]] = []
    migrated = False
    base = datetime(1970, 1, 1, tzinfo=UTC)
    for entry in entries:
        if not isinstance(entry, dict):
            return payload
        timestamp = entry.get("timestamp")
        if isinstance(timestamp, str) and timestamp.startswith("seq-"):
            suffix = timestamp[4:]
            if not suffix.isdigit():
                return payload
            sequence = int(suffix)
            normalized = (base + timedelta(seconds=sequence)).strftime("%Y-%m-%dT%H:%M:%SZ")
            migrated_entries.append({**entry, "timestamp": normalized})
            migrated = True
        else:
            migrated_entries.append(entry)

    if not migrated:
        return payload
    return {**payload, "entries": migrated_entries}


def _assert_task_id_matches(path: Path, payload: dict[str, Any], expected_task_id: str | None) -> None:
    if expected_task_id is None:
        return
    artifact_task_id = payload.get("task_id")
    if artifact_task_id != expected_task_id:
        raise RuntimeViolation(
            f"{path.name} task_id {artifact_task_id} does not match canonical task_id {expected_task_id}"
        )



def _load_validated_artifact(
    task_dir: Path,
    artifact_name: str,
    *,
    expected_task_id: str | None = None,
) -> dict[str, Any]:
    path = _artifact_path(task_dir, artifact_name)
    payload = _load_json(path)
    try:
        _validate_artifact_payload(artifact_name=artifact_name, payload=payload, source_name=path.name)
        _assert_task_id_matches(path, payload, expected_task_id)
        return payload
    except RuntimeViolation:
        coerced_payload = _coerce_legacy_artifact_payload(artifact_name, payload)
        if coerced_payload == payload:
            raise
        _validate_artifact_payload(artifact_name=artifact_name, payload=coerced_payload, source_name=path.name)
        _assert_task_id_matches(path, coerced_payload, expected_task_id)
        _write_json(path, coerced_payload)
        return coerced_payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_validated_artifact(task_dir: Path, artifact_name: str, payload: dict[str, Any]) -> None:
    _validate_artifact_payload(
        artifact_name=artifact_name,
        payload=payload,
        source_name=_artifact_path(task_dir, artifact_name).name,
    )
    _write_json(_artifact_path(task_dir, artifact_name), payload)


def _canonical_task_id(task_dir: Path) -> str:
    brief_payload: dict[str, Any] | None = None
    run_state_payload: dict[str, Any] | None = None

    brief_path = _artifact_path(task_dir, "brief")
    if brief_path.exists():
        brief_payload = _load_validated_artifact(task_dir, "brief")
    run_state_path = _artifact_path(task_dir, "run-state")
    if run_state_path.exists():
        run_state_payload = _load_validated_artifact(task_dir, "run-state")

    if brief_payload is not None and run_state_payload is not None:
        brief_task_id = brief_payload["task_id"]
        run_state_task_id = run_state_payload["task_id"]
        if brief_task_id != run_state_task_id:
            raise RuntimeViolation(
                f"run-state.json task_id {run_state_task_id} does not match canonical task_id {brief_task_id}"
            )
        return brief_task_id
    if brief_payload is not None:
        return brief_payload["task_id"]
    if run_state_payload is not None:
        return run_state_payload["task_id"]
    raise RuntimeViolation("task directory must contain brief.json or run-state.json")



def _task_id(task_dir: Path) -> str:
    return _canonical_task_id(task_dir)


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


def _current_plan_task(plan_ledger: dict[str, Any] | None) -> dict[str, Any] | None:
    if plan_ledger is None:
        return None
    current_task_id = plan_ledger.get("current_task_id")
    if not current_task_id:
        return None
    for task in plan_ledger.get("tasks", []):
        if task.get("id") == current_task_id:
            return task
    raise RuntimeViolation(f"plan-ledger.json current_task_id {current_task_id} is not present in tasks[]")


def _append_evidence_ref(task: dict[str, Any], evidence_ref: str) -> None:
    evidence_refs = task.setdefault("evidence_refs", [])
    if evidence_ref not in evidence_refs:
        evidence_refs.append(evidence_ref)


def _gate_evidence_ref(stage_name: str, gate_name: str) -> str:
    prefix = "run-state.json" if stage_name not in {"spec-review", "quality-review", "long-run"} else {
        "spec-review": "review-report-spec.json",
        "quality-review": "review-report.json",
        "long-run": "eval-record.json",
    }[stage_name]
    return f"{prefix}#gate:{gate_name}"


def _sync_plan_ledger_gate(plan_ledger: dict[str, Any] | None, *, stage_name: str, gate_name: str | None) -> None:
    task = _current_plan_task(plan_ledger)
    if task is None or gate_name is None:
        return
    task["status"] = "in_progress"
    _append_evidence_ref(task, _gate_evidence_ref(stage_name, gate_name))


def _sync_plan_ledger_retry(plan_ledger: dict[str, Any] | None) -> None:
    task = _current_plan_task(plan_ledger)
    if task is None:
        return
    task["status"] = "in_progress"
    task["attempt_count"] = int(task.get("attempt_count", 0)) + 1


def _sync_plan_ledger_review(plan_ledger: dict[str, Any] | None, *, review_artifact: str | None, verdict: str | None) -> None:
    if plan_ledger is None or verdict is None:
        return
    plan_ledger["last_review_verdict"] = verdict
    task = _current_plan_task(plan_ledger)
    if task is None or review_artifact is None:
        return
    _append_evidence_ref(task, f"{review_artifact}#verdict:{verdict}")


def _finalize_plan_ledger_task(plan_ledger: dict[str, Any] | None) -> None:
    task = _current_plan_task(plan_ledger)
    if task is None:
        return
    task["status"] = "done"
    task["attempt_count"] = max(1, int(task.get("attempt_count", 0)))


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


def _checkpoint_ref_path(task_dir: Path, ref: str) -> Path:
    ref_path = Path(ref)
    if ref_path.is_absolute():
        raise RuntimeViolation(f"checkpoint.json ref {ref} must be task-relative")
    resolved = (task_dir / ref_path).resolve()
    task_root = task_dir.resolve()
    if task_root not in {resolved, *resolved.parents}:
        raise RuntimeViolation(f"checkpoint.json ref {ref} escapes task directory")
    return resolved


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
    current_task_id = run_state.get("current_task_id") or (plan_ledger or {}).get("current_task_id")
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
    current_task_id = run_state.get("current_task_id") or (plan_ledger or {}).get("current_task_id")
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
    current_task_id = run_state.get("current_task_id") or (plan_ledger or {}).get("current_task_id")
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
    current_task_id = run_state.get("current_task_id") or (plan_ledger or {}).get("current_task_id")
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
    for artifact_name in ["review-report", "review-report-spec", "review-report-quality"]:
        review_path = _artifact_path(task_dir, artifact_name)
        if not review_path.exists():
            continue
        review = _load_validated_artifact(task_dir, artifact_name, expected_task_id=canonical_task_id)
        if review.get("review_type") == "spec" and review.get("verdict") == "approved":
            run_state["spec_review_approved"] = True
        if review.get("review_type") == "quality" and review.get("verdict") == "approved":
            run_state["quality_review_approved"] = True


def _required_finalize_flags(policy: RuntimePolicy, route_name: str) -> list[str]:
    route = _resolve_route(policy, route_name)
    required = list(policy.finalize_flags)
    if "spec-review" not in route and "spec_review_approved" in required:
        required.remove("spec_review_approved")
    if "quality-review" not in route and "quality_review_approved" in required:
        required.remove("quality_review_approved")
    return required


def _record_gate(run_state: dict[str, Any], stage_name: str, *, stage_gate_map: dict[str, str]) -> None:
    gate_name = stage_gate_map.get(stage_name)
    if gate_name and gate_name not in run_state["completed_gates"]:
        run_state["completed_gates"].append(gate_name)


def _expected_gates_before_stage(route: list[str], stage_name: str, *, stage_gate_map: dict[str, str]) -> list[str]:
    stage_index = route.index(stage_name)
    gates: list[str] = []
    for prior_stage in route[:stage_index]:
        gate_name = stage_gate_map.get(prior_stage)
        if gate_name is not None:
            gates.append(gate_name)
    return gates


def _resume_start_index(run_state: dict[str, Any], route: list[str], *, stage_gate_map: dict[str, str]) -> int:
    current_stage = run_state.get("current_stage")
    status = run_state.get("status")
    completed_gates = run_state.get("completed_gates", [])

    if current_stage not in route:
        raise RuntimeViolation(f"run-state checkpoint stage {current_stage} is not part of route")
    if not isinstance(completed_gates, list):
        raise RuntimeViolation("run-state checkpoint completed_gates must be a list")

    current_index = route.index(current_stage)
    expected_prefix = _expected_gates_before_stage(route, current_stage, stage_gate_map=stage_gate_map)
    missing_prefix = [gate for gate in expected_prefix if gate not in completed_gates]
    if missing_prefix:
        raise RuntimeViolation(
            f"run-state checkpoint is missing completed gates before {current_stage}: {', '.join(missing_prefix)}"
        )

    current_gate = stage_gate_map.get(current_stage)
    allowed_gates = set(expected_prefix)
    if current_gate:
        allowed_gates.add(current_gate)
    unexpected_gates = [
        gate for gate in completed_gates if gate in stage_gate_map.values() and gate not in allowed_gates
    ]
    if unexpected_gates:
        raise RuntimeViolation(
            f"run-state checkpoint has out-of-sequence completed gates at {current_stage}: {', '.join(unexpected_gates)}"
        )

    if status == "completed":
        terminal_stage = route[-1]
        if current_stage != terminal_stage:
            raise RuntimeViolation(
                f"completed run-state checkpoint must already be at terminal stage {terminal_stage}"
            )
        terminal_gate = stage_gate_map.get(terminal_stage)
        if terminal_gate and terminal_gate not in completed_gates:
            raise RuntimeViolation(
                f"completed run-state checkpoint is missing terminal gate {terminal_gate}"
            )
        return len(route)

    if current_gate and current_gate in completed_gates:
        current_index += 1

    if status in {"in_progress", "blocked", "not_started"}:
        return current_index
    raise RuntimeViolation(f"run-state checkpoint has unsupported status: {status}")


def _matching_review_payload(
    task_dir: Path,
    expected_review_type: str,
    expected_verdict: str,
    *,
    canonical_task_id: str,
) -> dict[str, Any] | None:
    for artifact_name in ["review-report", "review-report-spec", "review-report-quality"]:
        review_path = _artifact_path(task_dir, artifact_name)
        if not review_path.exists():
            continue
        payload = _load_validated_artifact(task_dir, artifact_name, expected_task_id=canonical_task_id)
        if payload.get("review_type") == expected_review_type and payload.get("verdict") == expected_verdict:
            return payload
    return None


def _enforce_stage_gate(task_dir: Path, policy: RuntimePolicy, stage_name: str, *, canonical_task_id: str) -> None:
    gate_name = policy.stage_gate_map.get(stage_name)
    if gate_name is None:
        return

    missing_gate_artifacts = _missing_artifacts(task_dir, policy.gate_requirements.get(gate_name, []))
    if missing_gate_artifacts:
        raise RuntimeViolation(
            f"{stage_name} requires artifacts satisfying gate {gate_name}: {', '.join(missing_gate_artifacts)}"
        )

    for required_artifact in policy.gate_requirements.get(gate_name, []):
        for variant in _artifact_variants(required_artifact):
            variant_path = _artifact_path(task_dir, variant)
            if variant_path.exists():
                _load_validated_artifact(task_dir, variant, expected_task_id=canonical_task_id)

    gate_review = policy.gate_reviews.get(gate_name, {})
    expected_review_type = gate_review.get("review_type")
    expected_verdict = gate_review.get("verdict")
    if expected_review_type and expected_verdict and _matching_review_payload(
        task_dir,
        expected_review_type,
        expected_verdict,
        canonical_task_id=canonical_task_id,
    ) is None:
        raise RuntimeViolation(
            f"{stage_name} requires approved {expected_review_type} review-report artifact"
        )


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
    for field_name in ["plan_ref", "plan_ledger_ref", "run_state_ref", "latest_checkpoint_ref"]:
        ref = session_state.get(field_name)
        if not isinstance(ref, str) or not ref:
            raise RuntimeViolation(f"session-state.json {field_name} is required")
        resolved = _checkpoint_ref_path(task_dir, ref)
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
    if session_state.get("route") != inferred_route:
        raise RuntimeViolation(
            f"session-state.json route {session_state.get('route')} does not match canonical route {inferred_route}"
        )
    if session_state.get("current_stage") != run_state.get("current_stage"):
        raise RuntimeViolation(
            f"session-state.json current_stage {session_state.get('current_stage')} does not match run-state current_stage {run_state.get('current_stage')}"
        )
    return {
        "task_id": canonical_task_id,
        "route": inferred_route,
        "current_stage": run_state["current_stage"],
        "current_task_id": run_state.get("current_task_id", ""),
        "next_action": checkpoint["next_action"],
        "latest_checkpoint_ref": session_state["latest_checkpoint_ref"],
        "run_state_ref": session_state["run_state_ref"],
    }


def status_summary(task_dir: Path, policy: RuntimePolicy, route_name: str | None = None) -> dict[str, Any]:
    resumed = resume_task(task_dir=task_dir, policy=policy, route_name=route_name)
    canonical_task_id = resumed["task_id"]
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
    if checkpoint is None:
        raise RuntimeViolation("status requires checkpoint.json")
    route = _resolve_route(policy, resumed["route"])
    current_index = route.index(run_state["current_stage"])
    required_gates = [
        policy.stage_gate_map[stage_name]
        for stage_name in route[current_index:]
        if stage_name in policy.stage_gate_map and policy.stage_gate_map[stage_name] not in run_state.get("completed_gates", [])
    ]
    return {
        "task_id": canonical_task_id,
        "route": resumed["route"],
        "current_stage": run_state["current_stage"],
        "current_task_id": run_state.get("current_task_id", ""),
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
) -> TransitionResult:
    route = _resolve_route(policy, route_name)
    canonical_task_id = _canonical_task_id(task_dir)
    plan_ledger = _load_plan_ledger(task_dir, canonical_task_id=canonical_task_id)
    run_state_path = _artifact_path(task_dir, "run-state")
    run_state = _load_validated_artifact(task_dir, "run-state", expected_task_id=canonical_task_id) if run_state_path.exists() else None
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
    session_state = _load_session_state(task_dir, canonical_task_id=canonical_task_id)
    if current_stage not in route:
        raise RuntimeViolation(f"stage {current_stage} is not part of route {route_name}")

    current_index = route.index(current_stage)
    if current_index + 1 >= len(route):
        raise RuntimeViolation(f"stage {current_stage} has no next stage in route {route_name}")

    next_stage = route[current_index + 1]
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

    if next_stage == "finalize":
        required_flags = _required_finalize_flags(policy, route_name)
        missing_flags = [flag for flag in required_flags if not run_state.get(flag, False)]
        if missing_flags:
            raise RuntimeViolation(
                f"finalize requires run-state approval flags: {', '.join(missing_flags)}"
            )

    _sync_plan_ledger_gate(plan_ledger, stage_name=current_stage, gate_name=policy.stage_gate_map.get(current_stage))
    run_state["current_stage"] = next_stage
    run_state["status"] = "in_progress"
    if plan_ledger is not None and plan_ledger.get("current_task_id"):
        run_state["current_task_id"] = plan_ledger["current_task_id"]
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

    return TransitionResult(next_stage=next_stage)


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
    start_index = _resume_start_index(run_state, route, stage_gate_map=policy.stage_gate_map)

    if start_index >= len(route):
        _append_decision(
            decision_log,
            actor="orchestrator",
            category="routing",
            decision=f"route already complete: {route_name}",
            rationale="validated checkpoint already reached route terminal stage",
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

    if start_index == 0:
        _append_decision(
            decision_log,
            actor="orchestrator",
            category="routing",
            decision=f"route selected: {route_name}",
            rationale="canonical complexity route applied",
        )
    else:
        _append_decision(
            decision_log,
            actor="orchestrator",
            category="routing",
            decision=f"route resumed: {route_name} from {resume_from_stage}",
            rationale="validated checkpoint state reused instead of replaying prior stages",
        )

    for stage_name in route[start_index:]:
        missing_artifacts = _missing_artifacts(task_dir, policy.stage_requirements.get(stage_name, []))
        if missing_artifacts:
            raise RuntimeViolation(
                f"missing required artifacts for {stage_name}: {', '.join(missing_artifacts)}"
            )

        run_state["current_stage"] = stage_name
        run_state["status"] = "in_progress"
        _sync_review_flags(task_dir, run_state, canonical_task_id=canonical_task_id)
        _enforce_stage_gate(task_dir, policy, stage_name, canonical_task_id=canonical_task_id)
        _record_gate(run_state, stage_name, stage_gate_map=policy.stage_gate_map)
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
            run_state["status"] = "completed"
            run_state["final_status"] = "success"
            _finalize_plan_ledger_task(plan_ledger)

        if stage_name == "long-run":
            run_state["status"] = "completed"
            run_state["final_status"] = run_state.get("final_status", "success")
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

    return run_state


def retry_stage(task_dir: Path, stage_name: str, max_retries: int = 2) -> dict[str, Any]:
    canonical_task_id = _canonical_task_id(task_dir)
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    decision_log = _ensure_decision_log(task_dir, canonical_task_id=canonical_task_id)
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
    session_state = _load_session_state(task_dir, canonical_task_id=canonical_task_id)
    plan_ledger = _load_plan_ledger(task_dir, canonical_task_id=canonical_task_id)
    if plan_ledger is not None and plan_ledger.get("current_task_id"):
        run_state["current_task_id"] = plan_ledger["current_task_id"]
    current = int(run_state["retries"].get(stage_name, 0))
    if current >= max_retries:
        raise RuntimeViolation(f"retry budget exceeded for {stage_name}: {current}/{max_retries}")

    run_state["retries"][stage_name] = current + 1
    run_state["current_stage"] = stage_name
    run_state["status"] = "in_progress"
    _sync_plan_ledger_retry(plan_ledger)
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
    return run_state


def step_back(task_dir: Path, policy: RuntimePolicy, route_name: str, current_stage: str) -> dict[str, Any]:
    route = _resolve_route(policy, route_name)
    if current_stage not in route:
        raise RuntimeViolation(f"stage {current_stage} is not part of route {route_name}")
    index = route.index(current_stage)
    if index == 0:
        raise RuntimeViolation(f"cannot step back before first stage of route {route_name}")

    previous_stage = route[index - 1]
    canonical_task_id = _canonical_task_id(task_dir)
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    decision_log = _ensure_decision_log(task_dir, canonical_task_id=canonical_task_id)
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
    session_state = _load_session_state(task_dir, canonical_task_id=canonical_task_id)
    plan_ledger = _load_plan_ledger(task_dir, canonical_task_id=canonical_task_id)
    if plan_ledger is not None and plan_ledger.get("current_task_id"):
        run_state["current_task_id"] = plan_ledger["current_task_id"]
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
