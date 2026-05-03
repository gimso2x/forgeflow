from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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


def build_route_result(run_state: dict[str, Any], plan_ledger: dict[str, Any] | None) -> dict[str, Any]:
    result = dict(run_state)
    progress = plan_ledger if plan_ledger is not None else run_state
    result["completed_gates"] = list(progress.get("completed_gates", []))
    result["retries"] = dict(progress.get("retries", result.get("retries", {})))
    return result


def stage_completion_status(stage_name: str, *, existing_final_status: str | None) -> tuple[str, str | None]:
    if stage_name == "finalize":
        return "completed", "success"
    if stage_name == "long-run":
        return "completed", existing_final_status or "success"
    return "in_progress", existing_final_status


def adaptive_route_selection(
    brief_text: str,
    plan_text: str | None = None,
    policy: Any | None = None,
    manual_route: str | None = None,
) -> RouteEntryDecision:
    """Use adaptive scoring if policy enables it, otherwise use manual route.

    Returns a :class:`RouteEntryDecision` with the selected route name
    embedded in *decision*.
    """
    from .complexity import assess_complexity, select_route, weights_from_policy

    adaptive_routing = getattr(policy, "adaptive_routing", None) if policy else None
    adaptive_enabled = bool(adaptive_routing and adaptive_routing.get("enabled", False))

    if adaptive_enabled and adaptive_routing is not None:
        weights = weights_from_policy(adaptive_routing)
        score = assess_complexity(brief_text, plan_text, weights=weights)
        route_name = select_route(
            score,
            manual_route=manual_route,
            adaptive_enabled=True,
        )
        return RouteEntryDecision(
            decision=f"adaptive route selected: {route_name}",
            rationale=score.rationale,
        )

    # Fallback: manual route or default medium
    route_name = manual_route or "medium"
    return RouteEntryDecision(
        decision=f"route selected: {route_name}",
        rationale="manual or default route applied (adaptive routing disabled)",
    )
