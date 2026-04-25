from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forgeflow_runtime.evolution_audit import append_audit_event as _append_audit_event
from forgeflow_runtime.evolution_audit import utc_timestamp as _utc_timestamp
from forgeflow_runtime.evolution_promotion_gates import promotion_ready
from forgeflow_runtime.evolution_rules import load_project_rules as _load_project_rules

PROMOTED_RULE_DIR = Path(".forgeflow") / "evolution" / "promoted-rules"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def promotion_marker_path(root: Path, proposal_path: Path) -> Path:
    safe_id = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in proposal_path.stem).strip("-") or "proposal"
    return root / PROMOTED_RULE_DIR / f"{safe_id}.json"


def active_rule_by_id(root: Path, rule_id: str) -> tuple[dict[str, Any], Path]:
    for rule, path in _load_project_rules(root):
        if rule.get("id") == rule_id:
            return rule, path
    raise ValueError(f"active project-local rule not found: {rule_id}")


def append_promote_blocked_audit(root: Path, proposal_path: Path, ready: dict[str, Any]) -> None:
    failed_checks = [issue["code"] for issue in ready["issues"]]
    blocked_event = {
        "event": "promote_blocked",
        "rule_id": ready["rule_id"],
        "proposal_path": str(proposal_path),
        "decision_path": ready["decision_path"],
        "approval_path": ready.get("gate", {}).get("approval_path"),
        "mutation_mode": "promotion_marker",
        "would_mutate_rules": False,
        "promoted": False,
        "passed": False,
        "failed_readiness_checks": failed_checks,
    }
    _append_audit_event(root, blocked_event)


def promote_rule(root: Path, proposal_path: Path) -> dict[str, Any]:
    """Finalize promotion by writing an immutable promotion marker, not editing the active rule."""

    root = root.resolve()
    proposal_path = proposal_path.resolve()
    ready = promotion_ready(root, proposal_path)
    if not ready["ready_for_promote"]:
        append_promote_blocked_audit(root, proposal_path, ready)
        issue_codes = ", ".join(issue["code"] for issue in ready["issues"])
        raise ValueError(f"promotion is not ready: {issue_codes}")

    rule, rule_path = active_rule_by_id(root, ready["rule_id"])
    marker_path = promotion_marker_path(root, proposal_path)
    if marker_path.exists():
        blocked_event = {
            "event": "promote_blocked",
            "rule_id": ready["rule_id"],
            "proposal_path": str(proposal_path),
            "decision_path": ready["decision_path"],
            "approval_path": ready.get("gate", {}).get("approval_path"),
            "promotion_path": str(marker_path),
            "mutation_mode": "promotion_marker",
            "would_mutate_rules": False,
            "promoted": False,
            "passed": False,
            "failed_readiness_checks": ["promotion_marker_already_exists"],
        }
        _append_audit_event(root, blocked_event)
        raise FileExistsError(f"promotion marker already exists: {marker_path}")
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker = {
        "schema_version": 1,
        "timestamp": _utc_timestamp(),
        "promotion_status": "promoted",
        "rule_id": ready["rule_id"],
        "proposal_path": str(proposal_path),
        "active_rule_path": str(rule_path),
        "decision_path": ready["decision_path"],
        "approval_path": ready.get("gate", {}).get("approval_path"),
        "mutation_mode": "promotion_marker",
        "active_rule_snapshot": rule,
    }
    marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    event = {
        "event": "promote",
        "rule_id": ready["rule_id"],
        "proposal_path": str(proposal_path),
        "promotion_path": str(marker_path),
        "mutation_mode": "promotion_marker",
        "would_mutate_rules": True,
        "promoted": True,
        "passed": True,
    }
    _append_audit_event(root, event)
    return {
        "proposal_path": str(proposal_path),
        "promotion_path": str(marker_path),
        "rule_id": ready["rule_id"],
        "mutation_mode": "promotion_marker",
        "would_mutate_rules": True,
        "promoted": True,
        "audit_event": event,
        "ready": ready,
    }


def list_promotions(root: Path) -> dict[str, Any]:
    """Read promotion marker snapshots written by promote_rule."""

    root = root.resolve()
    promotion_dir = root / PROMOTED_RULE_DIR
    promotions: list[dict[str, Any]] = []
    if promotion_dir.is_dir():
        for path in sorted(promotion_dir.glob("*.json")):
            marker = _load_json(path)
            promotions.append(
                {
                    "promotion_path": str(path),
                    "rule_id": marker.get("rule_id"),
                    "promotion_status": marker.get("promotion_status"),
                    "timestamp": marker.get("timestamp"),
                    "proposal_path": marker.get("proposal_path"),
                    "active_rule_path": marker.get("active_rule_path"),
                    "decision_path": marker.get("decision_path"),
                    "approval_path": marker.get("approval_path"),
                    "mutation_mode": marker.get("mutation_mode"),
                }
            )
    return {
        "promotion_dir": str(promotion_dir),
        "count": len(promotions),
        "promotions": promotions,
    }


def promote_stub(root: Path, proposal_path: Path) -> dict[str, Any]:
    """Backward-compatible alias for the first safe promote implementation."""

    return promote_rule(root, proposal_path)
