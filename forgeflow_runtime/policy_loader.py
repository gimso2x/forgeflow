from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class PolicyLoadError(Exception):
    """Raised when a policy file is missing or malformed."""


@dataclass(frozen=True)
class GateRetryConfig:
    """Typed configuration for RALF gate retry behaviour."""

    max_attempts: int = 3
    circuit_breaker: int = 3


@dataclass(frozen=True)
class RuntimePolicy:
    workflow_stages: list[str]
    stage_requirements: dict[str, list[str]]
    stage_gate_map: dict[str, str]
    gate_requirements: dict[str, list[str]]
    gate_reviews: dict[str, dict[str, str]]
    routes: dict[str, dict[str, Any]]
    finalize_flags: list[str]
    review_order: list[str]
    orchestration: dict[str, Any] | None = None
    gate_retry: dict[str, Any] | None = None
    budget: dict[str, Any] | None = None
    adaptive_routing: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None  # {enabled, registry_path, categories, max_file_lines}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise PolicyLoadError(f"Policy file not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_runtime_policy(root: Path) -> RuntimePolicy:
    policy_dir = root / "policy" / "canonical"

    stages_doc = _load_yaml(policy_dir / "stages.yaml")
    gates_doc = _load_yaml(policy_dir / "gates.yaml")
    workflow_doc = _load_yaml(policy_dir / "workflow.yaml")
    routing_doc = _load_yaml(policy_dir / "complexity-routing.yaml")

    stages_data = stages_doc.get("stages", {})
    gates_data = gates_doc.get("gates", {})

    workflow_stages = list(stages_data.keys())
    stage_requirements: dict[str, list[str]] = {}
    stage_gate_map: dict[str, str] = {}

    for name, info in stages_data.items():
        if isinstance(info, dict):
            stage_requirements[name] = info.get("required_for_entry", [])
            if "gate" in info:
                stage_gate_map[name] = info["gate"]
        else:
            stage_requirements[name] = []

    # Fallback gate mapping if not declared in stages.yaml
    if not stage_gate_map:
        for gate_name in gates_data.keys():
            for stage_name in workflow_stages:
                norm_stage = stage_name.replace("-", "_")
                if gate_name.startswith(norm_stage) or gate_name.startswith(
                    stage_name.replace("-", "")
                ):
                    stage_gate_map[stage_name] = gate_name
                    break

    gate_requirements: dict[str, list[str]] = {}
    gate_reviews: dict[str, dict[str, str]] = {}
    finalize_flags: list[str] = []

    for gate_name, info in gates_data.items():
        if not isinstance(info, dict):
            continue
        gate_requirements[gate_name] = info.get("requires", [])
        if info.get("review_type"):
            gate_reviews[gate_name] = {
                "review_type": info["review_type"],
                "verdict": info.get("verdict", ""),
            }
        flags = info.get("run_state_flags", [])
        if flags:
            finalize_flags.extend(flags)

    routes: dict[str, dict[str, Any]] = {}
    for route_name, route_info in routing_doc.get("routes", {}).items():
        if isinstance(route_info, dict):
            routes[route_name] = {
                "stages": route_info.get("stages", []),
                "max_retries": route_info.get("max_retries", 2),
                "traits": route_info.get("traits", []),
            }
        else:
            routes[route_name] = {"stages": [], "max_retries": 2, "traits": []}

    review_order = workflow_doc.get("review_order", [])
    orchestration = routing_doc.get("orchestration", None)
    adaptive_routing = routing_doc.get("adaptive_routing", None)

    return RuntimePolicy(
        workflow_stages=workflow_stages,
        stage_requirements=stage_requirements,
        stage_gate_map=stage_gate_map,
        gate_requirements=gate_requirements,
        gate_reviews=gate_reviews,
        routes=routes,
        finalize_flags=finalize_flags,
        review_order=review_order,
        orchestration=orchestration,
        adaptive_routing=adaptive_routing,
    )
