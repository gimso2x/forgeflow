from __future__ import annotations


from typing import Any


def required_finalize_flags(route: list[str], finalize_flags: list[str]) -> list[str]:
    required = list(finalize_flags)
    if "spec-review" not in route and "spec_review_approved" in required:
        required.remove("spec_review_approved")
    if "quality-review" not in route and "quality_review_approved" in required:
        required.remove("quality_review_approved")
    return required


def record_completed_gate(run_state: dict[str, Any], stage_name: str, *, stage_gate_map: dict[str, str]) -> None:
    gate_name = stage_gate_map.get(stage_name)
    if gate_name and gate_name not in run_state["completed_gates"]:
        run_state["completed_gates"].append(gate_name)
