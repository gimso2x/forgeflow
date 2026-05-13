from collections.abc import Callable
from pathlib import Path

import pytest

from forgeflow_runtime.operator_routing import effective_route, role_for_stage
from forgeflow_runtime.orchestrator import RuntimeViolation
from forgeflow_runtime.workflow_engine import StepDefinition, WorkflowDefinition


def test_effective_route_uses_explicit_route_before_artifacts(
    tmp_path: Path,
    write_json: Callable[[Path, dict], None],
) -> None:
    write_json(tmp_path / "checkpoint.json", {"route": "high"})

    assert effective_route(task_dir=tmp_path, explicit_route="small", min_route=None) == "small"


def test_effective_route_promotes_auto_detected_route_to_minimum(
    tmp_path: Path,
    write_json: Callable[[Path, dict], None],
) -> None:
    write_json(tmp_path / "brief.json", {"risk_level": "low"})

    assert effective_route(task_dir=tmp_path, explicit_route=None, min_route="medium") == "medium"


def test_effective_route_reads_existing_runtime_artifact_route(
    tmp_path: Path,
    write_json: Callable[[Path, dict], None],
) -> None:
    write_json(tmp_path / "session-state.json", {"route": "high"})

    assert effective_route(task_dir=tmp_path, explicit_route=None, min_route=None) == "high"


def test_role_for_stage_rejects_unknown_stage() -> None:
    with pytest.raises(RuntimeViolation, match="no default role mapping"):
        role_for_stage("bogus", violation_factory=RuntimeViolation)


def test_role_for_stage_can_use_workflow_engine_role_mapping() -> None:
    workflow = WorkflowDefinition(
        schema_version="test",
        name="test",
        routes={"custom": ["custom-review"]},
        steps={
            "custom-review": StepDefinition(
                id="custom-review",
                type="gate",
                role="custom-reviewer",
            )
        },
    )

    assert role_for_stage(
        "custom-review",
        workflow=workflow,
        violation_factory=RuntimeViolation,
    ) == "custom-reviewer"
