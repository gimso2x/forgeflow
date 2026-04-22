from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RuntimeViolation(Exception):
    """Raised when a requested stage transition violates runtime policy."""


@dataclass(frozen=True)
class RuntimePolicy:
    workflow_stages: list[str]
    stage_requirements: dict[str, list[str]]
    gate_requirements: dict[str, list[str]]
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


def _parse_gate_requirements(path: Path) -> tuple[dict[str, list[str]], list[str]]:
    requirements: dict[str, list[str]] = {}
    finalize_flags: list[str] = []
    current_gate: str | None = None
    for raw in _load_yaml_lines(path):
        if raw.startswith("  ") and not raw.startswith("    ") and raw.strip().endswith(":"):
            current_gate = raw.strip()[:-1]
            requirements[current_gate] = []
            continue
        if current_gate and raw.startswith("    requires: ["):
            chunk = raw.strip()[len("requires: [") : -1]
            requirements[current_gate] = [item.strip() for item in chunk.split(",") if item.strip()]
        if current_gate == "ready_to_finalize" and raw.startswith("    run_state_flags: ["):
            chunk = raw.strip()[len("run_state_flags: [") : -1]
            finalize_flags = [item.strip() for item in chunk.split(",") if item.strip()]
    return requirements, finalize_flags


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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _task_id(task_dir: Path) -> str:
    brief_path = _artifact_path(task_dir, "brief")
    if brief_path.exists():
        return _load_json(brief_path)["task_id"]
    run_state_path = _artifact_path(task_dir, "run-state")
    if run_state_path.exists():
        return _load_json(run_state_path)["task_id"]
    raise RuntimeViolation("task directory must contain brief.json or run-state.json")


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
        "spec_review_approved": False,
        "quality_review_approved": False,
    }


def _ensure_run_state(task_dir: Path) -> dict[str, Any]:
    path = _artifact_path(task_dir, "run-state")
    if path.exists():
        return _load_json(path)
    run_state = _default_run_state(task_dir)
    _write_json(path, run_state)
    return run_state


def _ensure_decision_log(task_dir: Path) -> dict[str, Any]:
    path = _artifact_path(task_dir, "decision-log")
    if path.exists():
        return _load_json(path)
    decision_log = {
        "schema_version": "0.1",
        "task_id": _task_id(task_dir),
        "entries": [],
    }
    _write_json(path, decision_log)
    return decision_log


def _append_decision(decision_log: dict[str, Any], *, actor: str, category: str, decision: str, rationale: str) -> None:
    sequence = len(decision_log["entries"]) + 1
    decision_log["entries"].append(
        {
            "timestamp": f"seq-{sequence:03d}",
            "actor": actor,
            "category": category,
            "decision": decision,
            "rationale": rationale,
            "affected_artifacts": ["run-state", "decision-log"],
        }
    )


def _sync_review_flags(task_dir: Path, run_state: dict[str, Any]) -> None:
    for artifact_name in ["review-report", "review-report-spec", "review-report-quality"]:
        review_path = _artifact_path(task_dir, artifact_name)
        if not review_path.exists():
            continue
        review = _load_json(review_path)
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


def load_runtime_policy(root: Path) -> RuntimePolicy:
    policy_root = root / "policy" / "canonical"
    gate_requirements, finalize_flags = _parse_gate_requirements(policy_root / "gates.yaml")
    return RuntimePolicy(
        workflow_stages=_parse_workflow_stages(policy_root / "workflow.yaml"),
        stage_requirements=_parse_stage_requirements(policy_root / "stages.yaml"),
        gate_requirements=gate_requirements,
        routes=_parse_routes(policy_root / "complexity-routing.yaml"),
        finalize_flags=finalize_flags,
    )


def advance_to_next_stage(task_dir: Path, policy: RuntimePolicy, route_name: str, current_stage: str) -> TransitionResult:
    route = policy.routes[route_name]
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

    if next_stage == "finalize":
        run_state = _load_json(_artifact_path(task_dir, "run-state"))
        required_flags = _required_finalize_flags(policy, route_name)
        missing_flags = [flag for flag in required_flags if not run_state.get(flag, False)]
        if missing_flags:
            raise RuntimeViolation(
                f"finalize requires run-state approval flags: {', '.join(missing_flags)}"
            )

    return TransitionResult(next_stage=next_stage)


def run_route(task_dir: Path, policy: RuntimePolicy, route_name: str) -> dict[str, Any]:
    route = policy.routes[route_name]
    run_state = _ensure_run_state(task_dir)
    decision_log = _ensure_decision_log(task_dir)

    _append_decision(
        decision_log,
        actor="orchestrator",
        category="routing",
        decision=f"route selected: {route_name}",
        rationale="canonical complexity route applied",
    )

    for index, stage_name in enumerate(route):
        missing_artifacts = _missing_artifacts(task_dir, policy.stage_requirements.get(stage_name, []))
        if missing_artifacts:
            raise RuntimeViolation(
                f"missing required artifacts for {stage_name}: {', '.join(missing_artifacts)}"
            )

        run_state["current_stage"] = stage_name
        run_state["status"] = "in_progress"
        _sync_review_flags(task_dir, run_state)
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
        _write_json(_artifact_path(task_dir, "run-state"), run_state)
        _write_json(_artifact_path(task_dir, "decision-log"), decision_log)

    return run_state


def retry_stage(task_dir: Path, stage_name: str, max_retries: int = 2) -> dict[str, Any]:
    run_state = _ensure_run_state(task_dir)
    decision_log = _ensure_decision_log(task_dir)
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
    _write_json(_artifact_path(task_dir, "run-state"), run_state)
    _write_json(_artifact_path(task_dir, "decision-log"), decision_log)
    return run_state


def step_back(task_dir: Path, policy: RuntimePolicy, route_name: str, current_stage: str) -> dict[str, Any]:
    route = policy.routes[route_name]
    if current_stage not in route:
        raise RuntimeViolation(f"stage {current_stage} is not part of route {route_name}")
    index = route.index(current_stage)
    if index == 0:
        raise RuntimeViolation(f"cannot step back before first stage of route {route_name}")

    previous_stage = route[index - 1]
    run_state = _ensure_run_state(task_dir)
    decision_log = _ensure_decision_log(task_dir)
    run_state["current_stage"] = previous_stage
    run_state["status"] = "in_progress"
    _append_decision(
        decision_log,
        actor="orchestrator",
        category="recovery",
        decision=f"step back: {current_stage} -> {previous_stage}",
        rationale="operator requested previous safe stage",
    )
    _write_json(_artifact_path(task_dir, "run-state"), run_state)
    _write_json(_artifact_path(task_dir, "decision-log"), decision_log)
    return run_state


def escalate_route(task_dir: Path, from_route: str) -> dict[str, Any]:
    if from_route not in {"small", "medium", "large_high_risk"}:
        raise RuntimeViolation(f"unknown route for escalation: {from_route}")
    run_state = _ensure_run_state(task_dir)
    decision_log = _ensure_decision_log(task_dir)
    run_state["current_stage"] = "clarify"
    run_state["status"] = "blocked"
    _append_decision(
        decision_log,
        actor="orchestrator",
        category="routing",
        decision=f"route escalated: {from_route} -> large_high_risk",
        rationale="risk or recovery pressure exceeded original route",
    )
    _write_json(_artifact_path(task_dir, "run-state"), run_state)
    _write_json(_artifact_path(task_dir, "decision-log"), decision_log)
    return run_state
