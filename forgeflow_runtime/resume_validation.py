from __future__ import annotations

from typing import Any, Callable

ViolationFactory = Callable[[str], Exception]


def plan_ledger_progress(plan_ledger: dict[str, Any] | None) -> dict[str, Any] | None:
    if plan_ledger is None:
        return None
    plan_ledger.setdefault("completed_stages", [])
    plan_ledger.setdefault("completed_gates", [])
    plan_ledger.setdefault("retries", {})
    return plan_ledger


def expected_gates_before_stage(route: list[str], stage_name: str, *, stage_gate_map: dict[str, str]) -> list[str]:
    stage_index = route.index(stage_name)
    gates: list[str] = []
    for prior_stage in route[:stage_index]:
        gate_name = stage_gate_map.get(prior_stage)
        if gate_name is not None:
            gates.append(gate_name)
    return gates


def resume_start_index(
    run_state: dict[str, Any],
    route: list[str],
    *,
    stage_gate_map: dict[str, str],
    violation_factory: ViolationFactory,
    plan_ledger: dict[str, Any] | None = None,
) -> int:
    current_stage = run_state.get("current_stage")
    status = run_state.get("status")
    source_name = "plan-ledger" if plan_ledger is not None else "run-state"
    progress_source = plan_ledger_progress(plan_ledger) if plan_ledger is not None else run_state
    completed_gates = progress_source.get("completed_gates", [])
    completed_stages = progress_source.get("completed_stages", [])

    if current_stage not in route:
        raise violation_factory(f"run-state checkpoint stage {current_stage} is not part of route")
    if not isinstance(completed_gates, list):
        source_name = "plan-ledger" if plan_ledger is not None else "run-state"
        raise violation_factory(f"{source_name} checkpoint completed_gates must be a list")
    if not isinstance(completed_stages, list):
        raise violation_factory(f"{source_name} checkpoint completed_stages must be a list")

    current_index = route.index(current_stage)
    allowed_stages = set(route[: current_index + 1])
    unexpected_stages = [stage_name for stage_name in completed_stages if stage_name not in allowed_stages]
    if unexpected_stages:
        raise violation_factory(
            f"{source_name} checkpoint has out-of-sequence completed stages at {current_stage}: {', '.join(unexpected_stages)}"
        )
    expected_prefix = expected_gates_before_stage(route, current_stage, stage_gate_map=stage_gate_map)
    missing_prefix = [gate for gate in expected_prefix if gate not in completed_gates]
    if missing_prefix:
        raise violation_factory(
            f"{source_name} checkpoint is missing completed gates before {current_stage}: {', '.join(missing_prefix)}"
        )

    current_gate = stage_gate_map.get(current_stage)
    allowed_gates = set(expected_prefix)
    if current_gate:
        allowed_gates.add(current_gate)
    unexpected_gates = [
        gate for gate in completed_gates if gate in stage_gate_map.values() and gate not in allowed_gates
    ]
    if unexpected_gates:
        raise violation_factory(
            f"{source_name} checkpoint has out-of-sequence completed gates at {current_stage}: {', '.join(unexpected_gates)}"
        )

    if status == "completed":
        terminal_stage = route[-1]
        if current_stage != terminal_stage:
            raise violation_factory(
                f"completed {source_name} checkpoint must already be at terminal stage {terminal_stage}"
            )
        terminal_gate = stage_gate_map.get(terminal_stage)
        if terminal_gate and terminal_gate not in completed_gates:
            raise violation_factory(
                f"completed {source_name} checkpoint is missing terminal gate {terminal_gate}"
            )
        return len(route)

    if current_gate and current_gate in completed_gates:
        current_index += 1

    if status in {"in_progress", "blocked", "not_started"}:
        return current_index
    raise violation_factory(f"run-state checkpoint has unsupported status: {status}")
