from __future__ import annotations

from collections.abc import Callable

from forgeflow_runtime.errors import RuntimeViolation


def next_stage_for_transition(
    route: list[str],
    current_stage: str,
    *,
    route_name: str,
    violation_factory: Callable[[str], Exception] = RuntimeViolation,
) -> str:
    if current_stage not in route:
        raise violation_factory(f"stage {current_stage} is not part of route {route_name}")

    current_index = route.index(current_stage)
    if current_index + 1 >= len(route):
        raise violation_factory(f"stage {current_stage} has no next stage in route {route_name}")

    return route[current_index + 1]
