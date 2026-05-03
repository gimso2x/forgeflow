"""Declarative coordination for multi-worker orchestration.

Defines worker roles, specs, coordination rules, and plans so that a
team of specialised agents can be wired together declaratively.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class WorkerRole(str, Enum):
    PLANNER = "planner"
    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"
    TESTER = "tester"
    ORCHESTRATOR = "orchestrator"


@dataclass(frozen=True)
class WorkerSpec:
    role: WorkerRole
    name: str
    model: str | None = None
    capabilities: list[str] = ()
    max_concurrent: int = 1


@dataclass(frozen=True)
class CoordinationRule:
    from_role: WorkerRole
    to_role: WorkerRole
    trigger: str  # "on_complete" | "on_failure" | "on_review"
    condition: str | None = None


@dataclass(frozen=True)
class CoordinationPlan:
    name: str
    workers: tuple[WorkerSpec, ...] = ()
    rules: tuple[CoordinationRule, ...] = ()


# ---------------------------------------------------------------------------
# Minimal YAML-like parser
# ---------------------------------------------------------------------------

def _parse_list(value: str) -> list[str]:
    """Parse '[a, b, c]' into ['a', 'b', 'c']."""
    m = re.match(r"^\s*\[(.*)\]\s*$", value)
    if not m:
        return [v.strip() for v in value.split(",") if v.strip()]
    return [v.strip() for v in m.group(1).split(",") if v.strip()]


def parse_coordination_yaml(yaml_text: str) -> CoordinationPlan:
    """Parse a minimal YAML-like coordination plan definition."""
    name = "unnamed"
    workers: list[WorkerSpec] = []
    rules: list[CoordinationRule] = []

    current_worker: dict[str, Any] = {}
    current_rule: dict[str, Any] = {}
    section: str | None = None  # "workers" | "rules"

    role_map = {r.value: r for r in WorkerRole}

    def _flush_worker() -> None:
        nonlocal current_worker
        if "role" in current_worker:
            workers.append(WorkerSpec(
                role=role_map[current_worker.get("role", "implementer")],
                name=current_worker.get("name", ""),
                model=current_worker.get("model"),
                capabilities=current_worker.get("capabilities", []),
                max_concurrent=int(current_worker.get("max_concurrent", 1)),
            ))
        current_worker = {}

    def _flush_rule() -> None:
        nonlocal current_rule
        if "from" in current_rule:
            rules.append(CoordinationRule(
                from_role=role_map[current_rule.get("from", "implementer")],
                to_role=role_map[current_rule.get("to", "implementer")],
                trigger=current_rule.get("trigger", "on_complete"),
                condition=current_rule.get("condition"),
            ))
        current_rule = {}

    for raw_line in yaml_text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue

        # Top-level key
        if re.match(r"^\w", line):
            _flush_worker()
            _flush_rule()
            key_val = line.split(":", 1)
            if len(key_val) == 2:
                key, val = key_val
                if key.strip() == "name":
                    name = val.strip()
                elif key.strip() == "workers":
                    section = "workers"
                elif key.strip() == "rules":
                    section = "rules"
                else:
                    section = None
            continue

        # List item start
        if line.strip().startswith("- "):
            if section == "workers":
                _flush_worker()
                kv = line.strip()[2:].split(":", 1)
                if len(kv) == 2:
                    current_worker[kv[0].strip()] = kv[1].strip()
            elif section == "rules":
                _flush_rule()
                kv = line.strip()[2:].split(":", 1)
                if len(kv) == 2:
                    current_rule[kv[0].strip()] = kv[1].strip()
            continue

        # Continuation key
        kv = line.split(":", 1)
        if len(kv) == 2:
            key, val = kv
            key_stripped = key.strip()
            val_stripped = val.strip()
            if section == "workers" and key_stripped == "capabilities":
                current_worker[key_stripped] = _parse_list(val_stripped)
            elif section == "workers":
                current_worker[key_stripped] = val_stripped
            elif section == "rules":
                current_rule[key_stripped] = val_stripped

    _flush_worker()
    _flush_rule()

    return CoordinationPlan(name=name, workers=tuple(workers), rules=tuple(rules))


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def build_task_mapping(plan: CoordinationPlan, task_type: str) -> list[WorkerSpec]:
    """Return workers whose capabilities include *task_type*."""
    return [w for w in plan.workers if task_type in w.capabilities]


def get_next_workers(
    plan: CoordinationPlan,
    current_role: WorkerRole,
    trigger: str,
) -> list[WorkerSpec]:
    """Find rules matching *current_role* + *trigger* and return target workers."""
    targets: list[WorkerSpec] = []
    for rule in plan.rules:
        if rule.from_role == current_role and rule.trigger == trigger:
            targets.extend(
                w for w in plan.workers if w.role == rule.to_role
            )
    return targets


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_plan(plan: CoordinationPlan) -> list[str]:
    """Return a list of validation errors (empty means valid)."""
    errors: list[str] = []
    if not plan.workers:
        errors.append("Plan must have at least one worker")
    worker_roles = {w.role for w in plan.workers}
    for rule in plan.rules:
        if rule.from_role not in worker_roles:
            errors.append(
                f"Rule references unknown from_role '{rule.from_role.value}'"
            )
        if rule.to_role not in worker_roles:
            errors.append(
                f"Rule references unknown to_role '{rule.to_role.value}'"
            )
    return errors


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def format_coordination_report(plan: CoordinationPlan) -> str:
    """Return a human-readable team diagram."""
    lines: list[str] = [f"Team: {plan.name}"]
    lines.append(f"Workers ({len(plan.workers)}):")
    for w in plan.workers:
        model_info = f" [{w.model}]" if w.model else ""
        lines.append(f"  - {w.name} ({w.role.value}){model_info}  caps={w.capabilities}")
    lines.append(f"Rules ({len(plan.rules)}):")
    for r in plan.rules:
        cond = f" [{r.condition}]" if r.condition else ""
        lines.append(
            f"  - {r.from_role.value} --({r.trigger})--> {r.to_role.value}{cond}"
        )
    return "\n".join(lines)
