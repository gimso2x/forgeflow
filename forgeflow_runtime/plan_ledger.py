from __future__ import annotations

from typing import Any

from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.gate_evaluation import gate_evidence_ref
from forgeflow_runtime.resume_validation import plan_ledger_progress


def current_plan_task(plan_ledger: dict[str, Any] | None) -> dict[str, Any] | None:
    if plan_ledger is None:
        return None
    current_task_id = plan_ledger.get("current_task_id")
    if not current_task_id:
        return None
    for task in plan_ledger.get("tasks", []):
        if task.get("id") == current_task_id:
            return task
    raise RuntimeViolation(f"plan-ledger.json current_task_id {current_task_id} is not present in tasks[]")


def canonical_current_task_id(run_state: dict[str, Any], plan_ledger: dict[str, Any] | None) -> str:
    ledger_task_id = (plan_ledger or {}).get("current_task_id")
    if isinstance(ledger_task_id, str) and ledger_task_id:
        return ledger_task_id
    run_state_task_id = run_state.get("current_task_id")
    if isinstance(run_state_task_id, str) and run_state_task_id:
        return run_state_task_id
    return ""


def append_evidence_ref(task: dict[str, Any], evidence_ref: str) -> None:
    evidence_refs = task.setdefault("evidence_refs", [])
    if evidence_ref not in evidence_refs:
        evidence_refs.append(evidence_ref)


def sync_plan_ledger_gate(plan_ledger: dict[str, Any] | None, *, stage_name: str, gate_name: str | None) -> None:
    plan_ledger_progress(plan_ledger)
    task = current_plan_task(plan_ledger)
    if task is None or gate_name is None:
        return
    task["status"] = "in_progress"
    completed_stages = plan_ledger.setdefault("completed_stages", [])
    if stage_name not in completed_stages:
        completed_stages.append(stage_name)
    completed_gates = plan_ledger.setdefault("completed_gates", [])
    if gate_name not in completed_gates:
        completed_gates.append(gate_name)
    append_evidence_ref(task, gate_evidence_ref(stage_name, gate_name))


def sync_plan_ledger_retry(plan_ledger: dict[str, Any] | None, *, stage_name: str) -> None:
    plan_ledger_progress(plan_ledger)
    task = current_plan_task(plan_ledger)
    if task is None:
        return
    task["status"] = "in_progress"
    task["attempt_count"] = int(task.get("attempt_count", 0)) + 1
    retries = plan_ledger.setdefault("retries", {})
    retries[stage_name] = int(retries.get(stage_name, 0)) + 1


def sync_plan_ledger_review(plan_ledger: dict[str, Any] | None, *, review_artifact: str | None, verdict: str | None) -> None:
    if plan_ledger is None or verdict is None:
        return
    plan_ledger["last_review_verdict"] = verdict
    task = current_plan_task(plan_ledger)
    if task is None or review_artifact is None:
        return
    append_evidence_ref(task, f"{review_artifact}#verdict:{verdict}")


def finalize_plan_ledger_task(plan_ledger: dict[str, Any] | None) -> None:
    task = current_plan_task(plan_ledger)
    if task is None:
        return
    task["status"] = "done"
    task["attempt_count"] = max(1, int(task.get("attempt_count", 0)))


def rewind_plan_ledger_progress(
    plan_ledger: dict[str, Any] | None,
    *,
    route: list[str],
    resume_stage: str,
    stage_gate_map: dict[str, str],
) -> None:
    progress = plan_ledger_progress(plan_ledger)
    task = current_plan_task(plan_ledger)
    if progress is None or task is None:
        return

    resume_index = route.index(resume_stage)
    preserved_stages = route[:resume_index]
    removed_stages = route[resume_index:]
    preserved_gates = [
        gate_name
        for gate_name in (stage_gate_map.get(stage_name) for stage_name in preserved_stages)
        if gate_name is not None
    ]
    removed_gate_refs = {
        gate_evidence_ref(stage_name, gate_name)
        for stage_name in removed_stages
        for gate_name in [stage_gate_map.get(stage_name)]
        if gate_name is not None
    }
    removed_review_prefixes: set[str] = set()
    if "spec-review" in removed_stages:
        removed_review_prefixes.update(
            {
                "review-report-spec.json#verdict:",
                "review-report.json#verdict:",
            }
        )
    if "quality-review" in removed_stages:
        removed_review_prefixes.update(
            {
                "review-report-quality.json#verdict:",
                "review-report.json#verdict:",
            }
        )
    if "long-run" in removed_stages:
        removed_review_prefixes.add("eval-record.json#verdict:")

    progress["completed_stages"] = [stage_name for stage_name in progress.get("completed_stages", []) if stage_name in preserved_stages]
    progress["completed_gates"] = [gate_name for gate_name in progress.get("completed_gates", []) if gate_name in preserved_gates]
    task["status"] = "in_progress"
    task["evidence_refs"] = [
        evidence_ref
        for evidence_ref in task.get("evidence_refs", [])
        if evidence_ref not in removed_gate_refs
        and not any(evidence_ref.startswith(prefix) for prefix in removed_review_prefixes)
    ]
    if any(stage_name in {"spec-review", "quality-review", "long-run"} for stage_name in removed_stages):
        progress.pop("last_review_verdict", None)

