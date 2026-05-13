from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, TypeVar

from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.workflow_engine import WorkflowDefinition, role_for_step

ViolationT = TypeVar("ViolationT", bound=Exception)

STAGE_ROLE_MAP: dict[str, str] = {
    "clarify": "coordinator",
    "plan": "planner",
    "execute": "worker",
    "spec-review": "spec-reviewer",
    "quality-review": "quality-reviewer",
    "finalize": "coordinator",
    "long-run": "worker",
    # specialist agents (on-demand, activated via brief.required_specialists)
    "security-review": "security-reviewer",
    "ux-review": "ux-reviewer",
    "perf-review": "perf-reviewer",
    "frontend-execute": "frontend-worker",
    "backend-execute": "backend-worker",
    "infra-execute": "infra-worker",
}

ROUTE_ORDER: list[str] = ["small", "medium", "high"]
RISK_TO_ROUTE: dict[str, str] = {
    "low": "small",
    "medium": "medium",
    "high": "high",
}

# Domain vocabulary → canonical stage name mapping.
# Brief authors use short domain names (e.g. "security", "backend");
# the runtime maps them to the stage names recognised by STAGE_ROLE_MAP.
DOMAIN_TO_STAGE: dict[str, str] = {
    "security": "security-review",
    "backend": "backend-execute",
    "frontend": "frontend-execute",
    "infra": "infra-execute",
    "ux": "ux-review",
    "perf": "perf-review",
}


def _normalise_specialist(name: str) -> str | None:
    """Map a brief domain name or canonical stage name to a valid stage key.

    Returns *None* when *name* is not a recognised specialist identifier.
    """
    if name in STAGE_ROLE_MAP:
        return name
    return DOMAIN_TO_STAGE.get(name)


def role_for_stage(
    stage: str,
    *,
    workflow: WorkflowDefinition | None = None,
    violation_factory: Callable[[str], ViolationT] = ValueError,
) -> str:
    if workflow is not None:
        try:
            return role_for_step(workflow, stage)
        except RuntimeViolation as exc:
            raise violation_factory(str(exc)) from exc

    role = STAGE_ROLE_MAP.get(stage)
    if not role:
        raise violation_factory(f"no default role mapping for stage: {stage}")
    return role


def specialists_from_brief(task_dir: Path) -> list[str]:
    """Return required_specialists from brief.json, or empty list.

    Accepts both canonical stage names (``security-review``) and short
    domain names (``security``).  Unrecognised values are silently dropped.
    """
    brief_path = task_dir / "brief.json"
    if not brief_path.exists():
        return []
    payload = json.loads(brief_path.read_text(encoding="utf-8"))
    specialists = payload.get("required_specialists")
    if not isinstance(specialists, list):
        return []
    resolved: list[str] = []
    for name in specialists:
        stage = _normalise_specialist(str(name))
        if stage is not None:
            resolved.append(stage)
    return resolved


def route_rank(
    route_name: str,
    *,
    violation_factory: Callable[[str], ViolationT] = ValueError,
) -> int:
    if route_name not in ROUTE_ORDER:
        raise violation_factory(f"unknown route: {route_name}")
    return ROUTE_ORDER.index(route_name)


def auto_route_for_task_dir(task_dir: Path) -> str:
    for artifact_name in ["session-state.json", "checkpoint.json", "plan-ledger.json"]:
        path = task_dir / artifact_name
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        route_name = payload.get("route")
        if isinstance(route_name, str) and route_name:
            return route_name

    brief_path = task_dir / "brief.json"
    if brief_path.exists():
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
        risk_level = brief.get("risk_level")
        if isinstance(risk_level, str) and risk_level in RISK_TO_ROUTE:
            return RISK_TO_ROUTE[risk_level]

    return "small"


def effective_route(
    *,
    task_dir: Path,
    explicit_route: str | None,
    min_route: str | None,
    violation_factory: Callable[[str], ViolationT] = ValueError,
) -> str:
    route_name = explicit_route or auto_route_for_task_dir(task_dir)
    if min_route is None:
        return route_name
    return ROUTE_ORDER[
        max(
            route_rank(route_name, violation_factory=violation_factory),
            route_rank(min_route, violation_factory=violation_factory),
        )
    ]
