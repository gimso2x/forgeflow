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
