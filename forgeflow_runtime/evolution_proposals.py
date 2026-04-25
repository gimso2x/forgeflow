from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forgeflow_runtime.evolution_audit import utc_timestamp as _utc_timestamp
from forgeflow_runtime.evolution_rules import load_project_rules as _load_project_rules

PROPOSAL_APPROVAL_DIR = Path(".forgeflow") / "evolution" / "proposal-approvals"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _active_rule_exists(root: Path, rule_id: str) -> bool:
    return any(rule.get("id") == rule_id for rule, _path in _load_project_rules(root))


def proposal_review(root: Path, proposal_path: Path) -> dict[str, Any]:
    """Read-only validation for a persisted promotion proposal."""

    root = root.resolve()
    proposal_path = proposal_path.resolve()
    try:
        proposal = _load_json(proposal_path)
    except json.JSONDecodeError as exc:
        raise ValueError(f"proposal JSON is invalid: {exc}") from exc
    if not isinstance(proposal, dict):
        raise ValueError("proposal JSON must be an object")
    rule_id = proposal.get("rule_id")
    issues: list[dict[str, Any]] = []

    def add_issue(code: str, severity: str = "error", **extra: Any) -> None:
        issues.append({"severity": severity, "code": code, **extra})

    if proposal.get("would_mutate") is not False:
        add_issue("proposal_may_mutate")
    if proposal.get("would_promote") is not False:
        add_issue("proposal_may_promote")
    if proposal.get("recommendation") != "promotion_candidate":
        add_issue("not_promotion_candidate", recommendation=proposal.get("recommendation"))
    approvals = proposal.get("required_human_approvals")
    required = {"maintainer_approval", "project_owner_approval"}
    if not isinstance(approvals, list):
        add_issue("missing_required_approval", missing=sorted(required))
    else:
        missing = sorted(required.difference(approvals))
        if missing:
            add_issue("missing_required_approval", missing=missing)
    risk_flags = proposal.get("risk_flags")
    if not isinstance(risk_flags, list) or "promotion_requires_separate_policy_gate" not in risk_flags:
        add_issue("missing_risk_flag", required="promotion_requires_separate_policy_gate")
    evidence = proposal.get("evidence_summary")
    if not isinstance(evidence, dict) or int(evidence.get("failures", 0) or 0) < 2:
        add_issue("insufficient_evidence_summary")
    active_rule_exists = isinstance(rule_id, str) and _active_rule_exists(root, rule_id)
    if not active_rule_exists:
        add_issue("active_rule_missing")
    return {
        "proposal_path": str(proposal_path),
        "rule_id": rule_id,
        "read_only": True,
        "would_mutate": False,
        "valid": not issues,
        "active_rule_exists": active_rule_exists,
        "issues": issues,
    }


def proposal_approval_path(root: Path, proposal_path: Path) -> Path:
    safe_id = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in proposal_path.stem).strip("-") or "proposal"
    return root / PROPOSAL_APPROVAL_DIR / f"{safe_id}.jsonl"


def read_proposal_approval_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def proposal_approve(root: Path, proposal_path: Path, *, approval: str, approver: str, reason: str) -> dict[str, Any]:
    """Append an approval record for a valid persisted proposal without promoting."""

    root = root.resolve()
    proposal_path = proposal_path.resolve()
    approval = approval.strip()
    approver = approver.strip()
    reason = reason.strip()
    if not approver or not reason:
        raise ValueError("approver and reason must be non-empty")
    if not approval:
        raise ValueError("approval must be non-empty")

    review = proposal_review(root, proposal_path)
    if not review["valid"]:
        issue_codes = ", ".join(issue["code"] for issue in review["issues"])
        raise ValueError(f"proposal review failed: {issue_codes}")

    proposal = _load_json(proposal_path)
    required_approvals = proposal.get("required_human_approvals")
    if not isinstance(required_approvals, list) or approval not in required_approvals:
        raise ValueError(f"approval is not required by proposal: {approval}")

    approvals_path = proposal_approval_path(root, proposal_path)
    approvals_path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_proposal_approval_records(approvals_path)
    duplicate = any(record.get("approval") == approval and record.get("approver") == approver for record in existing)
    record = {
        "schema_version": 1,
        "timestamp": _utc_timestamp(),
        "proposal_path": str(proposal_path),
        "rule_id": review["rule_id"],
        "approval": approval,
        "approver": approver,
        "reason": reason,
        "duplicate": duplicate,
        "would_promote": False,
        "would_mutate_rules": False,
    }
    with approvals_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "proposal_path": str(proposal_path),
        "approval_path": str(approvals_path),
        "rule_id": review["rule_id"],
        "approval": approval,
        "approver": approver,
        "reason": reason,
        "duplicate": duplicate,
        "would_promote": False,
        "would_mutate_rules": False,
        "review": review,
    }


def proposal_approvals(root: Path, proposal_path: Path) -> dict[str, Any]:
    """Read approval ledger status for a valid proposal without promoting."""

    root = root.resolve()
    proposal_path = proposal_path.resolve()
    review = proposal_review(root, proposal_path)
    if not review["valid"]:
        issue_codes = ", ".join(issue["code"] for issue in review["issues"])
        raise ValueError(f"proposal review failed: {issue_codes}")
    proposal = _load_json(proposal_path)
    required = proposal.get("required_human_approvals")
    if not isinstance(required, list):
        required = []
    approvals_path = proposal_approval_path(root, proposal_path)
    records = read_proposal_approval_records(approvals_path)
    recorded_set = {record.get("approval") for record in records if record.get("approval") in required}
    recorded = [approval for approval in required if approval in recorded_set]
    missing = [approval for approval in required if approval not in recorded_set]
    duplicate_set = {
        record.get("approval")
        for record in records
        if record.get("approval") in recorded_set and record.get("duplicate") is True
    }
    duplicates = [approval for approval in required if approval in duplicate_set]
    return {
        "proposal_path": str(proposal_path),
        "approval_path": str(approvals_path),
        "rule_id": review["rule_id"],
        "read_only": True,
        "would_promote": False,
        "would_mutate_rules": False,
        "required_approvals": required,
        "recorded_approvals": recorded,
        "missing_approvals": missing,
        "duplicates": duplicates,
        "ready_for_policy_gate": not missing and bool(required),
        "records": records,
        "review": review,
    }
