from __future__ import annotations

import dataclasses

import pytest

from forgeflow_runtime.coordination import (
    CoordinationPlan,
    CoordinationRule,
    WorkerRole,
    WorkerSpec,
    build_task_mapping,
    format_coordination_report,
    get_next_workers,
    parse_coordination_yaml,
    validate_plan,
)

# ── parse_coordination_yaml ──────────────────────────────────────────────

SAMPLE_YAML = """\
name: my-team
workers:
  - role: planner
    name: plan-1
    model: claude-sonnet
    capabilities: [plan, design]
  - role: implementer
    name: impl-1
    capabilities: [code, test]
  - role: reviewer
    name: rev-1
    capabilities: [review]
rules:
  - from: planner
    to: implementer
    trigger: on_complete
  - from: implementer
    to: reviewer
    trigger: on_complete
"""

EMPTY_WORKERS_YAML = """\
name: empty-team
workers:
rules:
"""

CAPS_YAML = """\
name: caps-team
workers:
  - role: planner
    name: p1
    capabilities: [plan, design, review]
  - role: tester
    name: t1
    capabilities: [test, lint, fmt]
rules:
"""


class TestParseCoordinationYaml:
    def test_basic_plan_with_workers_and_rules(self) -> None:
        plan = parse_coordination_yaml(SAMPLE_YAML)
        assert plan.name == "my-team"
        assert len(plan.workers) == 3
        assert plan.workers[0].name == "plan-1"
        assert plan.workers[0].role == WorkerRole.PLANNER
        assert plan.workers[0].model == "claude-sonnet"
        assert plan.workers[0].capabilities == ["plan", "design"]
        assert len(plan.rules) == 2
        assert plan.rules[0].from_role == WorkerRole.PLANNER
        assert plan.rules[0].to_role == WorkerRole.IMPLEMENTER
        assert plan.rules[0].trigger == "on_complete"

    def test_empty_workers_valid_empty_plan(self) -> None:
        plan = parse_coordination_yaml(EMPTY_WORKERS_YAML)
        assert plan.name == "empty-team"
        assert plan.workers == ()
        assert plan.rules == ()

    def test_capabilities_list_parsing(self) -> None:
        plan = parse_coordination_yaml(CAPS_YAML)
        assert plan.workers[0].capabilities == ["plan", "design", "review"]
        assert plan.workers[1].capabilities == ["test", "lint", "fmt"]


# ── build_task_mapping ───────────────────────────────────────────────────

class TestBuildTaskMapping:
    def test_returns_matching_workers(self) -> None:
        plan = parse_coordination_yaml(SAMPLE_YAML)
        result = build_task_mapping(plan, "plan")
        assert len(result) == 1
        assert result[0].name == "plan-1"

    def test_no_match_returns_empty(self) -> None:
        plan = parse_coordination_yaml(SAMPLE_YAML)
        result = build_task_mapping(plan, "deploy")
        assert result == []


# ── get_next_workers ─────────────────────────────────────────────────────

class TestGetNextWorkers:
    def test_returns_correct_targets(self) -> None:
        plan = parse_coordination_yaml(SAMPLE_YAML)
        result = get_next_workers(plan, WorkerRole.PLANNER, "on_complete")
        assert len(result) == 1
        assert result[0].role == WorkerRole.IMPLEMENTER

    def test_no_matching_rule_returns_empty(self) -> None:
        plan = parse_coordination_yaml(SAMPLE_YAML)
        result = get_next_workers(plan, WorkerRole.REVIEWER, "on_complete")
        assert result == []


# ── validate_plan ────────────────────────────────────────────────────────

class TestValidatePlan:
    def test_valid_plan_empty_errors(self) -> None:
        plan = parse_coordination_yaml(SAMPLE_YAML)
        assert validate_plan(plan) == []

    def test_no_workers_returns_error(self) -> None:
        plan = CoordinationPlan(name="empty", workers=(), rules=())
        errors = validate_plan(plan)
        assert len(errors) == 1
        assert "at least one worker" in errors[0]

    def test_rule_references_nonexistent_role(self) -> None:
        rule = CoordinationRule(
            from_role=WorkerRole.PLANNER,
            to_role=WorkerRole.TESTER,
            trigger="on_complete",
        )
        spec = WorkerSpec(role=WorkerRole.PLANNER, name="p1", capabilities=["plan"])
        plan = CoordinationPlan(name="bad", workers=(spec,), rules=(rule,))
        errors = validate_plan(plan)
        assert any("to_role" in e for e in errors)


# ── format_coordination_report ───────────────────────────────────────────

class TestFormatCoordinationReport:
    def test_contains_worker_names(self) -> None:
        plan = parse_coordination_yaml(SAMPLE_YAML)
        report = format_coordination_report(plan)
        assert "plan-1" in report
        assert "impl-1" in report


# ── frozen immutability ──────────────────────────────────────────────────

class TestFrozenImmutability:
    def test_coordination_plan_is_frozen(self) -> None:
        spec = WorkerSpec(role=WorkerRole.PLANNER, name="p", capabilities=["x"])
        plan = CoordinationPlan(name="test", workers=(spec,), rules=())
        with pytest.raises(dataclasses.FrozenInstanceError):
            plan.name = "changed"  # type: ignore[misc]

    def test_worker_spec_is_frozen(self) -> None:
        spec = WorkerSpec(role=WorkerRole.PLANNER, name="p", capabilities=["x"])
        with pytest.raises(dataclasses.FrozenInstanceError):
            spec.name = "changed"  # type: ignore[misc]
