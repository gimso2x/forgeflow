from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forgeflow_runtime.evolution_audit import utc_timestamp as _utc_timestamp
from forgeflow_runtime.evolution_proposals import (
    _active_rule_exists,
    proposal_approvals,
    proposal_review,
)

PROMOTION_DECISION_DIR = Path(".forgeflow") / "evolution" / "promotion-decisions"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def promotion_gate(root: Path, proposal_path: Path) -> dict[str, Any]:
    """Read-only promotion gate check. This never promotes or mutates rules."""

    root = root.resolve()
    proposal_path = proposal_path.resolve()
    issues: list[dict[str, Any]] = []

    try:
        approvals = proposal_approvals(root, proposal_path)
        review = approvals["review"]
    except ValueError as exc:
        try:
            review = proposal_review(root, proposal_path)
            proposal_valid = review["valid"]
            review_issues = review.get("issues", [])
        except ValueError as review_exc:
            proposal_valid = False
            review_issues = [{"severity": "error", "code": "proposal_review_error", "message": str(review_exc)}]
            review = {"valid": False, "issues": review_issues, "rule_id": None}
        issues.append({"severity": "error", "code": "proposal_review_failed", "message": str(exc), "review_issues": review_issues})
        return {
            "proposal_path": str(proposal_path),
            "rule_id": review.get("rule_id"),
            "read_only": True,
            "proposal_valid": proposal_valid,
            "all_required_approvals_present": False,
            "approval_records_complete": False,
            "risk_flags_acknowledged": False,
            "required_approvals": [],
            "recorded_approvals": [],
            "missing_approvals": [],
            "duplicates": [],
            "ready_for_policy_gate": False,
            "would_promote": False,
            "would_mutate_rules": False,
            "issues": issues,
        }

    proposal = _load_json(proposal_path)
    risk_flags = proposal.get("risk_flags")
    risk_flags_acknowledged = isinstance(risk_flags, list) and "promotion_requires_separate_policy_gate" in risk_flags
    if not risk_flags_acknowledged:
        issues.append({"severity": "error", "code": "risk_flags_not_acknowledged"})

    all_required = approvals["missing_approvals"] == [] and bool(approvals["required_approvals"])
    if not all_required:
        issues.append({"severity": "error", "code": "missing_required_approvals", "missing": approvals["missing_approvals"]})

    incomplete_records = []
    required_set = set(approvals["required_approvals"])
    for index, record in enumerate(approvals["records"]):
        if record.get("approval") not in required_set:
            continue
        if not str(record.get("approver", "")).strip() or not str(record.get("reason", "")).strip():
            incomplete_records.append({"index": index, "approval": record.get("approval")})
    approval_records_complete = not incomplete_records
    if incomplete_records:
        issues.append({"severity": "error", "code": "incomplete_approval_record", "records": incomplete_records})

    ready = review["valid"] and all_required and approval_records_complete and risk_flags_acknowledged
    return {
        "proposal_path": str(proposal_path),
        "approval_path": approvals["approval_path"],
        "rule_id": review["rule_id"],
        "read_only": True,
        "proposal_valid": review["valid"],
        "all_required_approvals_present": all_required,
        "approval_records_complete": approval_records_complete,
        "risk_flags_acknowledged": risk_flags_acknowledged,
        "required_approvals": approvals["required_approvals"],
        "recorded_approvals": approvals["recorded_approvals"],
        "missing_approvals": approvals["missing_approvals"],
        "duplicates": approvals["duplicates"],
        "ready_for_policy_gate": ready,
        "would_promote": False,
        "would_mutate_rules": False,
        "issues": issues,
    }


def promotion_decision_path(root: Path, proposal_path: Path) -> Path:
    safe_id = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in proposal_path.stem).strip("-") or "proposal"
    return root / PROMOTION_DECISION_DIR / f"{safe_id}.jsonl"


def promotion_decision(root: Path, proposal_path: Path, *, decision: str, decider: str, reason: str, write: bool = False) -> dict[str, Any]:
    """Record a human policy-gate decision without promoting or mutating rules."""

    root = root.resolve()
    proposal_path = proposal_path.resolve()
    decision = decision.strip()
    decider = decider.strip()
    reason = reason.strip()
    if decision != "approve_policy_gate":
        raise ValueError(f"unsupported promotion decision: {decision}")
    if not decider or not reason:
        raise ValueError("decider and reason must be non-empty")
    gate = promotion_gate(root, proposal_path)
    if not gate["ready_for_policy_gate"]:
        issue_codes = ", ".join(issue["code"] for issue in gate["issues"])
        raise ValueError(f"promotion gate is not ready: {issue_codes}")

    decision_path = promotion_decision_path(root, proposal_path)
    record = {
        "schema_version": 1,
        "timestamp": _utc_timestamp(),
        "proposal_path": str(proposal_path),
        "rule_id": gate["rule_id"],
        "decision": decision,
        "decider": decider,
        "reason": reason,
        "gate_ready": True,
        "would_promote": False,
        "would_mutate_rules": False,
    }
    if write:
        decision_path.parent.mkdir(parents=True, exist_ok=True)
        with decision_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "proposal_path": str(proposal_path),
        "decision_path": str(decision_path),
        "rule_id": gate["rule_id"],
        "decision": decision,
        "decider": decider,
        "reason": reason,
        "written": write,
        "would_promote": False,
        "would_mutate_rules": False,
        "gate": gate,
    }


def read_promotion_decision_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def promotion_ready(root: Path, proposal_path: Path) -> dict[str, Any]:
    """Read-only readiness check for a future mutating promote command."""

    root = root.resolve()
    proposal_path = proposal_path.resolve()
    issues: list[dict[str, Any]] = []
    gate = promotion_gate(root, proposal_path)
    if not gate["ready_for_policy_gate"]:
        issues.append({"severity": "error", "code": "promotion_gate_not_ready", "gate_issues": gate.get("issues", [])})

    decision_path = promotion_decision_path(root, proposal_path)
    records = read_promotion_decision_records(decision_path)
    approving_records = [record for record in records if record.get("decision") == "approve_policy_gate"]
    decision_present = bool(approving_records)
    if not decision_present:
        issues.append({"severity": "error", "code": "missing_approve_policy_gate_decision"})

    incomplete_records = []
    for index, record in enumerate(approving_records):
        if not str(record.get("decider", "")).strip() or not str(record.get("reason", "")).strip():
            incomplete_records.append({"index": index, "decision": record.get("decision")})
    decision_records_complete = not incomplete_records
    if incomplete_records:
        issues.append({"severity": "error", "code": "incomplete_promotion_decision_record", "records": incomplete_records})

    rule_id = gate.get("rule_id")
    active_rule_exists = isinstance(rule_id, str) and _active_rule_exists(root, rule_id)
    if not active_rule_exists:
        issues.append({"severity": "error", "code": "active_rule_missing"})

    ready = gate["ready_for_policy_gate"] and decision_present and decision_records_complete and active_rule_exists
    return {
        "proposal_path": str(proposal_path),
        "decision_path": str(decision_path),
        "rule_id": rule_id,
        "read_only": True,
        "promotion_gate_ready": gate["ready_for_policy_gate"],
        "approve_policy_gate_decision_present": decision_present,
        "decision_records_complete": decision_records_complete,
        "active_rule_exists": active_rule_exists,
        "ready_for_promote": ready,
        "would_promote": False,
        "would_mutate_rules": False,
        "decision_records": records,
        "gate": gate,
        "issues": issues,
    }
