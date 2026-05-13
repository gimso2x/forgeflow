from __future__ import annotations

from pathlib import Path

import pytest

from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.workflow_engine import (
    WorkflowDefinition,
    evaluate_template,
    load_workflow,
    next_step,
    resolve_route,
    role_for_step,
)


def _write_workflow(path: Path) -> None:
    path.write_text(
        """
{
  "schema_version": "0.1",
  "name": "test-pipeline",
  "routes": {
    "small": ["clarify", "execute", "quality-review", "finalize"],
    "medium": ["clarify", "plan", "execute", "quality-review", "finalize"],
    "high": ["clarify", "plan", "execute", "spec-review", "quality-review", "finalize", "long-run"]
  },
  "steps": {
    "clarify": {
      "type": "stage",
      "role": "coordinator",
      "artifact_out": ["brief.json"],
      "required_for_entry": []
    },
    "plan": {
      "type": "stage",
      "role": "planner",
      "artifact_out": ["plan-ledger.json"],
      "required_for_entry": ["brief.json"],
      "non_negotiables": ["plan must be executable"]
    },
    "execute": {
      "type": "stage",
      "role": "worker",
      "artifact_out": ["implementation-evidence.json"],
      "required_for_entry": ["plan-ledger.json"]
    },
    "spec-review": {
      "type": "gate",
      "role": "spec-reviewer",
      "artifact_out": ["review-report.json"],
      "required_for_entry": ["implementation-evidence.json"],
      "gate": "spec_review_passed"
    },
    "quality-review": {
      "type": "gate",
      "role": "quality-reviewer",
      "artifact_out": ["review-report.json"],
      "required_for_entry": ["implementation-evidence.json"],
      "gate": "quality_review_passed"
    },
    "finalize": {
      "type": "stage",
      "role": "coordinator",
      "artifact_out": ["session-state.json"],
      "required_for_entry": ["review-report.json"]
    },
    "long-run": {
      "type": "stage",
      "role": "worker",
      "artifact_out": ["eval-record.json"],
      "required_for_entry": ["review-report.json"]
    }
  }
}
""".strip(),
        encoding="utf-8",
    )


def test_load_workflow_reads_json_definition(tmp_path: Path) -> None:
    workflow_path = tmp_path / "default.json"
    _write_workflow(workflow_path)

    workflow = load_workflow(workflow_path)

    assert isinstance(workflow, WorkflowDefinition)
    assert workflow.schema_version == "0.1"
    assert workflow.name == "test-pipeline"
    assert workflow.routes["medium"] == ["clarify", "plan", "execute", "quality-review", "finalize"]
    assert workflow.steps["plan"].role == "planner"
    assert workflow.steps["plan"].non_negotiables == ["plan must be executable"]


def test_resolve_route_returns_ordered_step_definitions(tmp_path: Path) -> None:
    workflow_path = tmp_path / "default.json"
    _write_workflow(workflow_path)
    workflow = load_workflow(workflow_path)

    steps = resolve_route(workflow, "high")

    assert [step.id for step in steps] == [
        "clarify",
        "plan",
        "execute",
        "spec-review",
        "quality-review",
        "finalize",
        "long-run",
    ]
    assert [step.role for step in steps] == [
        "coordinator",
        "planner",
        "worker",
        "spec-reviewer",
        "quality-reviewer",
        "coordinator",
        "worker",
    ]


def test_resolve_route_rejects_unknown_route(tmp_path: Path) -> None:
    workflow_path = tmp_path / "default.json"
    _write_workflow(workflow_path)
    workflow = load_workflow(workflow_path)

    with pytest.raises(RuntimeViolation, match="unknown route: bogus"):
        resolve_route(workflow, "bogus")


def test_resolve_route_rejects_missing_step_referenced_by_route(tmp_path: Path) -> None:
    workflow_path = tmp_path / "broken.json"
    workflow_path.write_text(
        '{"schema_version":"0.1","name":"broken","routes":{"small":["clarify","missing"]},"steps":{"clarify":{"type":"stage","role":"coordinator"}}}',
        encoding="utf-8",
    )
    workflow = load_workflow(workflow_path)

    with pytest.raises(RuntimeViolation, match="route small references unknown step: missing"):
        resolve_route(workflow, "small")


def test_next_step_advances_with_workflow_route(tmp_path: Path) -> None:
    workflow_path = tmp_path / "default.json"
    _write_workflow(workflow_path)
    workflow = load_workflow(workflow_path)

    assert next_step(workflow, "medium", "plan").id == "execute"
    assert next_step(workflow, "medium", "plan").role == "worker"


def test_next_step_rejects_step_outside_route(tmp_path: Path) -> None:
    workflow_path = tmp_path / "default.json"
    _write_workflow(workflow_path)
    workflow = load_workflow(workflow_path)

    with pytest.raises(RuntimeViolation, match="step spec-review is not part of route medium"):
        next_step(workflow, "medium", "spec-review")


def test_next_step_rejects_terminal_step(tmp_path: Path) -> None:
    workflow_path = tmp_path / "default.json"
    _write_workflow(workflow_path)
    workflow = load_workflow(workflow_path)

    with pytest.raises(RuntimeViolation, match="step finalize has no next step in route medium"):
        next_step(workflow, "medium", "finalize")


def test_role_for_step_reads_role_from_workflow_definition(tmp_path: Path) -> None:
    workflow_path = tmp_path / "default.json"
    _write_workflow(workflow_path)
    workflow = load_workflow(workflow_path)

    assert role_for_step(workflow, "quality-review") == "quality-reviewer"


def test_role_for_step_rejects_unknown_step(tmp_path: Path) -> None:
    workflow_path = tmp_path / "default.json"
    _write_workflow(workflow_path)
    workflow = load_workflow(workflow_path)

    with pytest.raises(RuntimeViolation, match="unknown step: bogus"):
        role_for_step(workflow, "bogus")


def test_evaluate_template_replaces_double_brace_paths() -> None:
    rendered = evaluate_template(
        "route={{ task.risk_level }} status={{ steps.plan.status }} literal={{ missing.value }}",
        {
            "task": {"risk_level": "high"},
            "steps": {"plan": {"status": "approved"}},
        },
    )

    assert rendered == "route=high status=approved literal="
