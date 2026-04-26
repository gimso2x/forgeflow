from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, TypeVar

ViolationT = TypeVar("ViolationT", bound=Exception)

STAGE_ROLE_MAP: dict[str, str] = {
    "clarify": "coordinator",
    "plan": "planner",
    "execute": "worker",
    "spec-review": "spec-reviewer",
    "quality-review": "quality-reviewer",
    "finalize": "coordinator",
    "long-run": "worker",
}

ROUTE_ORDER: list[str] = ["small", "medium", "large_high_risk"]
RISK_TO_ROUTE: dict[str, str] = {
    "low": "small",
    "medium": "medium",
    "high": "large_high_risk",
}


def role_for_stage(
    stage: str,
    *,
    violation_factory: Callable[[str], ViolationT] = ValueError,
) -> str:
    role = STAGE_ROLE_MAP.get(stage)
    if not role:
        raise violation_factory(f"no default role mapping for stage: {stage}")
    return role


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
