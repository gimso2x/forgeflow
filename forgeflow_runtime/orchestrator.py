from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class RuntimeViolation(Exception):
    """Raised when a requested stage transition violates runtime policy."""


@dataclass(frozen=True)
class RuntimePolicy:
    workflow_stages: list[str]
    stage_requirements: dict[str, list[str]]
    gate_requirements: dict[str, list[str]]
    gate_reviews: dict[str, dict[str, str]]
    routes: dict[str, list[str]]
    finalize_flags: list[str]


@dataclass(frozen=True)
class TransitionResult:
    next_stage: str


STAGE_GATE_MAP = {
    "clarify": "clarification_complete",
    "plan": "plan_executable",
    "execute": "execution_evidenced",
    "spec-review": "spec_review_passed",
    "quality-review": "quality_review_passed",
    "finalize": "ready_to_finalize",
    "long-run": "worth_long_run_capture",
}

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
}

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _parse_workflow_stages(path: Path) -> list[str]:
    stages: list[str] = []
    capture = False
    for raw in _load_yaml_lines(path):
        stripped = raw.strip()
        if stripped == "stages:":
            capture = True
            continue
        if capture:
            if stripped.startswith("- "):
                stages.append(stripped[2:].strip())
            elif stripped and not raw.startswith("  "):
                break
    return stages


def _parse_stage_requirements(path: Path) -> dict[str, list[str]]:
    requirements: dict[str, list[str]] = {}
    current_stage: str | None = None
    for raw in _load_yaml_lines(path):
        if raw.startswith("  ") and not raw.startswith("    ") and raw.strip().endswith(":"):
            current_stage = raw.strip()[:-1]
            requirements[current_stage] = []
            continue
        if current_stage and raw.startswith("    required_for_entry: ["):
            chunk = raw.strip()[len("required_for_entry: [") : -1]
            requirements[current_stage] = [item.strip() for item in chunk.split(",") if item.strip()]
    return requirements


def _parse_gate_requirements(path: Path) -> tuple[dict[str, list[str]], dict[str, dict[str, str]], list[str]]:
    requirements: dict[str, list[str]] = {}
    gate_reviews: dict[str, dict[str, str]] = {}
    finalize_flags: list[str] = []
    current_gate: str | None = None
    for raw in _load_yaml_lines(path):
        if raw.startswith("  ") and not raw.startswith("    ") and raw.strip().endswith(":"):
            current_gate = raw.strip()[:-1]
            requirements[current_gate] = []
            gate_reviews[current_gate] = {}
            continue
        if current_gate and raw.startswith("    requires: ["):
            chunk = raw.strip()[len("requires: [") : -1]
            requirements[current_gate] = [item.strip() for item in chunk.split(",") if item.strip()]
        if current_gate and raw.startswith("    review_type: "):
            gate_reviews[current_gate]["review_type"] = raw.strip()[len("review_type: ") :]
        if current_gate and raw.startswith("    verdict: "):
            gate_reviews[current_gate]["verdict"] = raw.strip()[len("verdict: ") :]
        if current_gate == "ready_to_finalize" and raw.startswith("    run_state_flags: ["):
            chunk = raw.strip()[len("run_state_flags: [") : -1]
            finalize_flags = [item.strip() for item in chunk.split(",") if item.strip()]
    return requirements, gate_reviews, finalize_flags


def _parse_routes(path: Path) -> dict[str, list[str]]:
    routes: dict[str, list[str]] = {}
    current_route: str | None = None
    in_routes = False
    for raw in _load_yaml_lines(path):
        if raw.strip() == "routes:":
            in_routes = True
            continue
        if not in_routes:
            continue
        if raw.startswith("  ") and not raw.startswith("    ") and raw.strip().endswith(":"):
            current_route = raw.strip()[:-1]
            routes[current_route] = []
            continue
        if current_route and raw.startswith("    stages: ["):
            chunk = raw.strip()[len("stages: [") : -1]
            routes[current_route] = [item.strip() for item in chunk.split(",") if item.strip()]
    return routes


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


def _load_checkpoint(task_dir: Path, *, canonical_task_id: str) -> dict[str, Any] | None:
    path = _artifact_path(task_dir, "checkpoint")
    if not path.exists():
        return None
    return _load_validated_artifact(task_dir, "checkpoint", expected_task_id=canonical_task_id)


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
    route = policy.routes[route_name]
    required = list(policy.finalize_flags)
    if "spec-review" not in route and "spec_review_approved" in required:
        required.remove("spec_review_approved")
    if "quality-review" not in route and "quality_review_approved" in required:
        required.remove("quality_review_approved")
    return required


def _record_gate(run_state: dict[str, Any], stage_name: str) -> None:
    gate_name = STAGE_GATE_MAP.get(stage_name)
    if gate_name and gate_name not in run_state["completed_gates"]:
        run_state["completed_gates"].append(gate_name)


def _expected_gates_before_stage(route: list[str], stage_name: str) -> list[str]:
    stage_index = route.index(stage_name)
    gates: list[str] = []
    for prior_stage in route[:stage_index]:
        gate_name = STAGE_GATE_MAP.get(prior_stage)
        if gate_name is not None:
            gates.append(gate_name)
    return gates


def _resume_start_index(run_state: dict[str, Any], route: list[str]) -> int:
    current_stage = run_state.get("current_stage")
    status = run_state.get("status")
    completed_gates = run_state.get("completed_gates", [])

    if current_stage not in route:
        raise RuntimeViolation(f"run-state checkpoint stage {current_stage} is not part of route")
    if not isinstance(completed_gates, list):
        raise RuntimeViolation("run-state checkpoint completed_gates must be a list")

    current_index = route.index(current_stage)
    expected_prefix = _expected_gates_before_stage(route, current_stage)
    missing_prefix = [gate for gate in expected_prefix if gate not in completed_gates]
    if missing_prefix:
        raise RuntimeViolation(
            f"run-state checkpoint is missing completed gates before {current_stage}: {', '.join(missing_prefix)}"
        )

    current_gate = STAGE_GATE_MAP.get(current_stage)
    allowed_gates = set(expected_prefix)
    if current_gate:
        allowed_gates.add(current_gate)
    unexpected_gates = [
        gate for gate in completed_gates if gate in STAGE_GATE_MAP.values() and gate not in allowed_gates
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
        terminal_gate = STAGE_GATE_MAP.get(terminal_stage)
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
    gate_name = STAGE_GATE_MAP.get(stage_name)
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


def load_runtime_policy(root: Path) -> RuntimePolicy:
    policy_root = root / "policy" / "canonical"
    gate_requirements, gate_reviews, finalize_flags = _parse_gate_requirements(policy_root / "gates.yaml")
    return RuntimePolicy(
        workflow_stages=_parse_workflow_stages(policy_root / "workflow.yaml"),
        stage_requirements=_parse_stage_requirements(policy_root / "stages.yaml"),
        gate_requirements=gate_requirements,
        gate_reviews=gate_reviews,
        routes=_parse_routes(policy_root / "complexity-routing.yaml"),
        finalize_flags=finalize_flags,
    )


def _resolve_route(policy: RuntimePolicy, route_name: str) -> list[str]:
    route = policy.routes.get(route_name)
    if route is None:
        raise RuntimeViolation(f"unknown route: {route_name}")
    return route


def advance_to_next_stage(task_dir: Path, policy: RuntimePolicy, route_name: str, current_stage: str) -> TransitionResult:
    route = _resolve_route(policy, route_name)
    canonical_task_id = _canonical_task_id(task_dir)
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

    if next_stage == "finalize":
        run_state = _load_validated_artifact(task_dir, "run-state", expected_task_id=canonical_task_id)
        required_flags = _required_finalize_flags(policy, route_name)
        missing_flags = [flag for flag in required_flags if not run_state.get(flag, False)]
        if missing_flags:
            raise RuntimeViolation(
                f"finalize requires run-state approval flags: {', '.join(missing_flags)}"
            )

    return TransitionResult(next_stage=next_stage)


def run_route(task_dir: Path, policy: RuntimePolicy, route_name: str) -> dict[str, Any]:
    route = _resolve_route(policy, route_name)
    canonical_task_id = _canonical_task_id(task_dir)
    plan_ledger = _require_plan_ledger_for_route(task_dir, route_name, canonical_task_id=canonical_task_id)
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    decision_log = _ensure_decision_log(task_dir, canonical_task_id=canonical_task_id)
    checkpoint = _load_checkpoint(task_dir, canonical_task_id=canonical_task_id)
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
    start_index = _resume_start_index(run_state, route)

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
        _sync_checkpoint(
            task_dir,
            route_name=route_name,
            route=route,
            run_state=run_state,
            plan_ledger=plan_ledger,
            checkpoint=checkpoint,
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
        _record_gate(run_state, stage_name)

        if stage_name == "execute" and not _artifact_path(task_dir, "decision-log").exists():
            raise RuntimeViolation("execute requires decision-log.json to exist")

        if stage_name == "finalize":
            required_flags = _required_finalize_flags(policy, route_name)
            missing_flags = [flag for flag in required_flags if not run_state.get(flag, False)]
            if missing_flags:
                raise RuntimeViolation(
                    f"finalize requires run-state approval flags: {', '.join(missing_flags)}"
                )
            run_state["status"] = "completed"
            run_state["final_status"] = "success"

        if stage_name == "long-run":
            run_state["status"] = "completed"
            run_state["final_status"] = run_state.get("final_status", "success")

        _append_decision(
            decision_log,
            actor="orchestrator",
            category="stage-transition",
            decision=f"stage entered: {stage_name}",
            rationale=f"route {route_name} progressed to {stage_name}",
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

    return run_state


def retry_stage(task_dir: Path, stage_name: str, max_retries: int = 2) -> dict[str, Any]:
    canonical_task_id = _canonical_task_id(task_dir)
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    decision_log = _ensure_decision_log(task_dir, canonical_task_id=canonical_task_id)
    current = int(run_state["retries"].get(stage_name, 0))
    if current >= max_retries:
        raise RuntimeViolation(f"retry budget exceeded for {stage_name}: {current}/{max_retries}")

    run_state["retries"][stage_name] = current + 1
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
    return run_state


def escalate_route(task_dir: Path, from_route: str) -> dict[str, Any]:
    if from_route not in {"small", "medium", "large_high_risk"}:
        raise RuntimeViolation(f"unknown route for escalation: {from_route}")
    canonical_task_id = _canonical_task_id(task_dir)
    run_state = _ensure_run_state(task_dir, canonical_task_id=canonical_task_id)
    decision_log = _ensure_decision_log(task_dir, canonical_task_id=canonical_task_id)
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
    return run_state
