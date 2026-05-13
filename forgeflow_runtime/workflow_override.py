from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from .errors import RuntimeViolation
from .policy_loader import RuntimePolicy
from .workflow_engine import StepDefinition, WorkflowDefinition, workflow_from_runtime_policy


def resolve_project_workflow(
    root: Path,
    policy: RuntimePolicy,
    *,
    override_path: Path | None = None,
) -> WorkflowDefinition:
    """Return canonical workflow with a validated project overlay applied."""
    canonical = workflow_from_runtime_policy(policy)
    path = override_path or root / ".forgeflow" / "workflow.yaml"
    if not path.exists():
        return canonical

    override = _load_override(path)
    routes = _apply_route_overrides(canonical, override.get("routes", {}))
    steps = _apply_step_overrides(canonical, override.get("steps", {}))

    return WorkflowDefinition(
        schema_version=canonical.schema_version,
        name=str(override.get("name", canonical.name)),
        routes=routes,
        steps=steps,
    )


def _load_override(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RuntimeViolation(f"workflow override must contain a mapping: {path}")
    return raw


def _apply_route_overrides(
    canonical: WorkflowDefinition, raw_routes: Any
) -> dict[str, list[str]]:
    if raw_routes is None:
        return dict(canonical.routes)
    if not isinstance(raw_routes, dict):
        raise RuntimeViolation("workflow override routes must be a mapping")

    routes = {name: list(steps) for name, steps in canonical.routes.items()}
    for route_name, raw_steps in raw_routes.items():
        route_name = str(route_name)
        if route_name not in canonical.routes:
            raise RuntimeViolation(f"unknown workflow route: {route_name}")
        if not isinstance(raw_steps, list):
            raise RuntimeViolation(f"workflow override route {route_name} must be a list")
        step_ids = [str(step_id) for step_id in raw_steps]
        for step_id in step_ids:
            if step_id not in canonical.steps:
                raise RuntimeViolation(f"unknown workflow step in route {route_name}: {step_id}")
        routes[route_name] = step_ids
    return routes


def _apply_step_overrides(
    canonical: WorkflowDefinition, raw_steps: Any
) -> dict[str, StepDefinition]:
    if raw_steps is None:
        return dict(canonical.steps)
    if not isinstance(raw_steps, dict):
        raise RuntimeViolation("workflow override steps must be a mapping")

    steps = dict(canonical.steps)
    for step_id, raw_step in raw_steps.items():
        step_id = str(step_id)
        if step_id not in canonical.steps:
            raise RuntimeViolation(f"unknown workflow step: {step_id}")
        if not isinstance(raw_step, dict):
            raise RuntimeViolation(f"workflow override step {step_id} must be a mapping")

        canonical_step = canonical.steps[step_id]
        _reject_canonical_contract_changes(step_id, canonical_step, raw_step)
        steps[step_id] = replace(
            canonical_step,
            role=str(raw_step.get("role", canonical_step.role)),
            type=str(raw_step.get("type", canonical_step.type)),
            artifact_out=_string_list(raw_step.get("artifact_out", canonical_step.artifact_out), step_id, "artifact_out"),
            non_negotiables=_string_list(
                raw_step.get("non_negotiables", canonical_step.non_negotiables),
                step_id,
                "non_negotiables",
            ),
        )
    return steps


def _reject_canonical_contract_changes(
    step_id: str, canonical_step: StepDefinition, raw_step: dict[str, Any]
) -> None:
    if "gate" in raw_step and raw_step.get("gate") != canonical_step.gate:
        raise RuntimeViolation(f"cannot change canonical gate for step {step_id}")
    if "required_for_entry" in raw_step:
        requested = _string_list(raw_step.get("required_for_entry"), step_id, "required_for_entry")
        if requested != canonical_step.required_for_entry:
            raise RuntimeViolation(f"cannot change canonical required_for_entry for step {step_id}")


def _string_list(value: Any, step_id: str, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RuntimeViolation(f"workflow override step {step_id} {field_name} must be a list")
    return [str(item) for item in value]
