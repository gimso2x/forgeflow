from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forgeflow_runtime.evolution_audit import utc_timestamp as _utc_timestamp
from forgeflow_runtime.evolution_audit import effectiveness_review

PROPOSAL_DIR = Path(".forgeflow") / "evolution" / "proposals"


def promotion_plan(root: Path, rule_id: str, *, since_days: int = 30) -> dict[str, Any]:
    """Build a non-mutating promotion plan from audit-backed effectiveness evidence."""

    effectiveness = effectiveness_review(root, rule_id, since_days=since_days)
    metrics = effectiveness["metrics"]
    recommendation = effectiveness["recommendation"]
    risk_flags: list[str] = []
    required_approvals: list[str] = []
    suggested_next_command: str | None = None
    if recommendation == "promotion_candidate":
        required_approvals = ["maintainer_approval", "project_owner_approval"]
        risk_flags.append("promotion_requires_separate_policy_gate")
        suggested_next_command = f"python3 scripts/forgeflow_evolution.py effectiveness --rule {rule_id} --since-days {since_days} --json"
    elif recommendation == "watch_candidate":
        risk_flags.append("single_failure_needs_observation")
    elif recommendation == "insufficient_data":
        risk_flags.append("insufficient_effectiveness_evidence")
    return {
        "rule_id": rule_id,
        "read_only": True,
        "would_mutate": False,
        "would_promote": False,
        "recommendation": recommendation,
        "required_human_approvals": required_approvals,
        "evidence_summary": {
            "window_days": effectiveness["window_days"],
            "executions": metrics["executions"],
            "passes": metrics["passes"],
            "failures": metrics["failures"],
            "blocked_executions": metrics["blocked_executions"],
        },
        "risk_flags": risk_flags,
        "suggested_next_command": suggested_next_command,
    }


def write_promotion_plan(root: Path, rule_id: str, *, since_days: int = 30) -> dict[str, Any]:
    """Persist a promotion proposal without changing rules or audit logs."""

    root = root.resolve()
    plan = promotion_plan(root, rule_id, since_days=since_days)
    proposals_dir = root / PROPOSAL_DIR
    proposals_dir.mkdir(parents=True, exist_ok=True)
    safe_rule_id = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in rule_id).strip("-") or "rule"
    timestamp = _utc_timestamp().replace(":", "").replace("-", "")
    proposal_path = proposals_dir / f"{timestamp}-{safe_rule_id}-promotion-plan.json"
    payload = {
        **plan,
        "proposal_written": True,
        "proposal_path": str(proposal_path),
    }
    proposal_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
