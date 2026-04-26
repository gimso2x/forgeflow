import pytest

from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.stage_transition import next_stage_for_transition


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
