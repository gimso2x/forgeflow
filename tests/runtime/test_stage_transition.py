import pytest

from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.stage_transition import next_stage_for_transition
from forgeflow_runtime.workflow_engine import StepDefinition, WorkflowDefinition


def test_next_stage_for_transition_advances_to_following_route_stage() -> None:
    route = ["clarify", "plan", "execute"]

    assert next_stage_for_transition(route, "plan", route_name="medium") == "execute"


def test_next_stage_for_transition_rejects_stage_outside_route() -> None:
    route = ["clarify", "plan", "execute"]

    with pytest.raises(RuntimeViolation, match="stage spec-review is not part of route medium"):
        next_stage_for_transition(route, "spec-review", route_name="medium")


def test_next_stage_for_transition_rejects_terminal_stage() -> None:
    route = ["clarify", "plan", "execute"]

    with pytest.raises(RuntimeViolation, match="stage execute has no next stage in route medium"):
        next_stage_for_transition(route, "execute", route_name="medium")


def test_next_stage_for_transition_can_use_workflow_engine_contract() -> None:
    workflow = WorkflowDefinition(
        schema_version="test",
        name="test",
        routes={"custom": ["alpha", "beta", "gamma"]},
        steps={
            "alpha": StepDefinition(id="alpha", type="stage", role="coordinator"),
            "beta": StepDefinition(id="beta", type="stage", role="custom-worker"),
            "gamma": StepDefinition(id="gamma", type="stage", role="reviewer"),
        },
    )

    assert next_stage_for_transition(
        ["legacy", "route"],
        "beta",
        route_name="custom",
        workflow=workflow,
    ) == "gamma"
