from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from forgeflow_runtime.evolution_audit import (
    AUDIT_LOG_PATH,
    append_audit_event as _append_audit_event,
    audit_events,
    effectiveness_review,
    read_audit_events as _read_audit_events,
)
from forgeflow_runtime.evolution_execution import (
    execute_rule as _execute_rule,
    run_approved_command as _run_approved_command,
)
from forgeflow_runtime.evolution_doctor import (
    audit_required_field_issues as _audit_required_field_issues,
    doctor_evolution_state as _doctor_evolution_state,
)
from forgeflow_runtime.evolution_lifecycle import (
    adopt_example_rule,
    load_retired_rule_by_id as _load_retired_rule_by_id,
    load_retired_rules as _load_retired_rules,
    move_with_audit_rollback as _move_with_audit_rollback,
    retire_rule as _retire_rule,
    restore_rule as _restore_rule,
    rule_filename as _rule_filename,
)
from forgeflow_runtime.evolution_promotion_plans import (
    PROPOSAL_DIR,
    promotion_plan,
    write_promotion_plan,
)
from forgeflow_runtime.evolution_proposals import (
    PROPOSAL_APPROVAL_DIR,
    proposal_approval_path as _proposal_approval_path,
    proposal_approvals,
    proposal_approve,
    proposal_review,
    read_proposal_approval_records as _read_proposal_approval_records,
)
from forgeflow_runtime.evolution_promotion_gates import (
    PROMOTION_DECISION_DIR,
    promotion_decision,
    promotion_decision_path as _promotion_decision_path,
    promotion_gate,
    promotion_ready,
    read_promotion_decision_records as _read_promotion_decision_records,
)
from forgeflow_runtime.evolution_promotions import (
    PROMOTED_RULE_DIR,
    active_rule_by_id as _active_rule_by_id,
    append_promote_blocked_audit as _append_promote_blocked_audit,
    list_promotions,
    promote_rule,
    promote_stub,
    promotion_marker_path as _promotion_marker_path,
)
from forgeflow_runtime.evolution_rules import (
    APPROVED_COMMANDS,
    PROJECT_RULE_DIR,
    RETIRED_RULE_DIR,
    dry_run_rule,
    _example_summary,
    failed_safety_checks as _failed_safety_checks,
    list_rules,
    load_example_rule_by_id as _load_example_rule_by_id,
    load_example_rules as _load_example_rules,
    load_project_rules as _load_project_rules,
    load_rule_by_id as _load_rule_by_id,
    safety_checks as _safety_checks,
)


EVOLUTION_EXAMPLES = [
    "generated-adapter-drift-rule.json",
    "no-env-commit-rule.json",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def retire_rule(root: Path, rule_id: str, *, reason: str) -> dict[str, Any]:
    return _retire_rule(root, rule_id, reason=reason, audit_append=_append_audit_event)


def restore_rule(root: Path, rule_id: str, *, reason: str) -> dict[str, Any]:
    return _restore_rule(root, rule_id, reason=reason, audit_append=_append_audit_event)




def execute_rule(root: Path, rule_id: str) -> dict[str, Any]:
    """Execute a safety-validated project-local rule command."""

    return _execute_rule(root, rule_id, audit_append=_append_audit_event, command_runner=_run_approved_command)


def doctor_evolution_state(root: Path) -> dict[str, Any]:
    """Read-only health check for the project-local evolution lifecycle."""

    return _doctor_evolution_state(
        root,
        project_rule_loader=_load_project_rules,
        retired_rule_loader=_load_retired_rules,
    )


def inspect_evolution_policy(root: Path) -> dict[str, Any]:
    """Return a read-only summary of the canonical evolution policy.

    This deliberately does not execute rule commands. The first runtime surface is
    inspection, not enforcement. Self-evolution that starts by running arbitrary
    project commands is how tools become tiny haunted houses.
    """

    root = root.resolve()
    policy = _load_yaml(root / "policy" / "canonical" / "evolution.yaml")
    global_scope = policy["scopes"]["global"]
    project_scope = policy["scopes"]["project"]

    examples = []
    examples_valid = True
    for rule, path in _load_example_rules(root):
        summary = _example_summary(rule)
        examples.append(summary)
        if not all(_safety_checks(rule).values()):
            examples_valid = False

    return {
        "policy_version": policy.get("version"),
        "global": {
            "artifact_root": global_scope.get("artifact_root"),
            "activation": global_scope.get("activation"),
            "permissions": global_scope.get("permissions", []),
            "forbidden": global_scope.get("forbidden", []),
            "advises": [
                permission.removeprefix("advise_")
                for permission in global_scope.get("permissions", [])
                if permission.startswith("advise_")
            ],
            "can_block": False,
        },
        "project": {
            "artifact_root": project_scope.get("artifact_root"),
            "permissions": project_scope.get("permissions", []),
            "hard_gate_requires": project_scope.get("hard_gate_requires", []),
            "can_enforce_hard": "enforce_adopted_hard_rules" in project_scope.get("permissions", []),
        },
        "retrieval_contract": policy.get("retrieval_contract", {}),
        "rule_lifecycle": policy.get("rule_lifecycle", []),
        "signal_sources": policy.get("signal_sources", []),
        "project_hard_examples": examples,
        "examples_valid": examples_valid,
        "runtime_enforcement": "not_enabled",
    }
