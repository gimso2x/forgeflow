"""Evolution path resolution.

Global storage:  ~/.forgeflow/evolution/   (rules, audit, proposals, decisions)
Project-local:   .forgeflow/tasks/<id>/    (observations per task)
"""
from __future__ import annotations

import os
from pathlib import Path


def global_evolution_dir() -> Path:
    """Return the shared global evolution directory (~/.forgeflow/evolution/).

    Override with FORGEFLOW_EVOLUTION_DIR env var for testing / CLI isolation.
    """
    env = os.environ.get("FORGEFLOW_EVOLUTION_DIR")
    if env:
        return Path(env)
    return Path.home() / ".forgeflow" / "evolution"


def global_rule_dir() -> Path:
    return global_evolution_dir() / "rules"


def global_retired_rule_dir() -> Path:
    return global_evolution_dir() / "retired-rules"


def global_audit_log_path() -> Path:
    return global_evolution_dir() / "audit-log.jsonl"


def global_proposal_dir() -> Path:
    return global_evolution_dir() / "proposals"


def global_proposal_approval_dir() -> Path:
    return global_evolution_dir() / "proposal-approvals"


def global_promotion_decision_dir() -> Path:
    return global_evolution_dir() / "promotion-decisions"


def global_promoted_rule_dir() -> Path:
    return global_evolution_dir() / "promoted-rules"


# Project-local: only observations stay per-project
PROJECT_TASK_DIR = Path(".forgeflow") / "tasks"
