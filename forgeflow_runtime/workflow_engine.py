from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .errors import RuntimeViolation
from .policy_loader import RuntimePolicy


@dataclass(frozen=True)
class StepDefinition:
    id: str
    type: str
    role: str
    artifact_out: list[str] = field(default_factory=list)
    required_for_entry: list[str] = field(default_factory=list)
    gate: str | None = None
    non_negotiables: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowDefinition:
    schema_version: str
    name: str
    routes: dict[str, list[str]]
    steps: dict[str, StepDefinition]


def workflow_from_runtime_policy(policy: RuntimePolicy, *, name: str = "runtime-policy") -> WorkflowDefinition:
    """Build a workflow definition from the legacy RuntimePolicy shape.

    This keeps the new workflow engine aligned with policy.routes without
    replacing the existing policy loader or changing route semantics.
    """
    route_steps = {
        route_name: [str(stage) for stage in route_info.get("stages", [])]
        for route_name, route_info in policy.routes.items()
    }
    step_ids: list[str] = []
    for stage in policy.workflow_stages:
        if stage not in step_ids:
            step_ids.append(stage)
    for route in route_steps.values():
        for stage in route:
            if stage not in step_ids:
                step_ids.append(stage)

    steps = {
        step_id: StepDefinition(
            id=step_id,
            type="gate" if step_id in policy.stage_gate_map else "stage",
            role=_default_role_for_step(step_id),
            required_for_entry=list(policy.stage_requirements.get(step_id, [])),
            gate=policy.stage_gate_map.get(step_id),
        )
        for step_id in step_ids
    }
    return WorkflowDefinition(
        schema_version="runtime-policy",
        name=name,
        routes=route_steps,
        steps=steps,
    )


def load_workflow(path: str | Path) -> WorkflowDefinition:
    workflow_path = Path(path)
    raw = workflow_path.read_text(encoding="utf-8")
    if workflow_path.suffix.lower() == ".json":
        data = json.loads(raw)
    else:
        data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise RuntimeViolation(f"workflow file must contain a mapping: {workflow_path}")

    raw_routes = data.get("routes", {})
    if not isinstance(raw_routes, dict):
        raise RuntimeViolation("workflow routes must be a mapping")
    routes = {name: _string_list(stages, f"route {name}") for name, stages in raw_routes.items()}

    raw_steps = data.get("steps", {})
    if not isinstance(raw_steps, dict):
        raise RuntimeViolation("workflow steps must be a mapping")
    steps = {
        step_id: _step_definition(step_id, raw_step)
        for step_id, raw_step in raw_steps.items()
    }

    return WorkflowDefinition(
        schema_version=str(data.get("schema_version", "")),
        name=str(data.get("name", "")),
        routes=routes,
        steps=steps,
    )


def resolve_route(workflow: WorkflowDefinition, route_name: str) -> list[StepDefinition]:
    if route_name not in workflow.routes:
        raise RuntimeViolation(f"unknown route: {route_name}")

    resolved: list[StepDefinition] = []
    for step_id in workflow.routes[route_name]:
        step = workflow.steps.get(step_id)
        if step is None:
            raise RuntimeViolation(f"route {route_name} references unknown step: {step_id}")
        resolved.append(step)
    return resolved


def next_step(workflow: WorkflowDefinition, route_name: str, current_step: str) -> StepDefinition:
    route = resolve_route(workflow, route_name)
    step_ids = [step.id for step in route]
    if current_step not in step_ids:
        raise RuntimeViolation(f"step {current_step} is not part of route {route_name}")
    index = step_ids.index(current_step)
    if index + 1 >= len(route):
        raise RuntimeViolation(f"step {current_step} has no next step in route {route_name}")
    return route[index + 1]


def role_for_step(workflow: WorkflowDefinition, step_id: str) -> str:
    step = workflow.steps.get(step_id)
    if step is None:
        raise RuntimeViolation(f"unknown step: {step_id}")
    return step.role


def evaluate_template(template: str, context: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        path = match.group(1).strip()
        value: Any = context
        for part in path.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return ""
        return str(value)

    return re.sub(r"\{\{\s*([^{}]+?)\s*\}\}", replace, template)


def _step_definition(step_id: str, raw_step: Any) -> StepDefinition:
    if not isinstance(raw_step, dict):
        raise RuntimeViolation(f"step {step_id} must be a mapping")
    return StepDefinition(
        id=step_id,
        type=str(raw_step.get("type", "stage")),
        role=str(raw_step.get("role", "worker")),
        artifact_out=_string_list(raw_step.get("artifact_out", []), f"step {step_id} artifact_out"),
        required_for_entry=_string_list(
            raw_step.get("required_for_entry", []), f"step {step_id} required_for_entry"
        ),
        gate=raw_step.get("gate"),
        non_negotiables=_string_list(
            raw_step.get("non_negotiables", []), f"step {step_id} non_negotiables"
        ),
    )


def _string_list(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RuntimeViolation(f"{label} must be a list")
    return [str(item) for item in value]


def _default_role_for_step(step_id: str) -> str:
    role_map = {
        "clarify": "coordinator",
        "plan": "planner",
        "execute": "worker",
        "spec-review": "spec-reviewer",
        "quality-review": "quality-reviewer",
        "finalize": "coordinator",
        "long-run": "worker",
        "security-review": "security-reviewer",
        "ux-review": "ux-reviewer",
        "perf-review": "perf-reviewer",
        "frontend-execute": "frontend-worker",
        "backend-execute": "backend-worker",
        "infra-execute": "infra-worker",
    }
    return role_map.get(step_id, "worker")
