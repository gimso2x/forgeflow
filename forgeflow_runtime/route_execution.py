from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteEntryDecision:
    decision: str
    rationale: str
    already_complete: bool = False


def route_entry_decision(
    *,
    route_name: str,
    start_index: int,
    resume_from_stage: str | None,
    route_length: int,
) -> RouteEntryDecision:
    if start_index >= route_length:
        return RouteEntryDecision(
            decision=f"route already complete: {route_name}",
            rationale="validated checkpoint already reached route terminal stage",
            already_complete=True,
        )
    if start_index == 0:
        return RouteEntryDecision(
            decision=f"route selected: {route_name}",
            rationale="canonical complexity route applied",
        )
    return RouteEntryDecision(
        decision=f"route resumed: {route_name} from {resume_from_stage}",
        rationale="validated checkpoint state reused instead of replaying prior stages",
    )


def route_iteration_stages(route: list[str], start_index: int) -> list[str]:
    return list(route[start_index:])
