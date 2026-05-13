from __future__ import annotations

from pathlib import Path

import pytest

from forgeflow_runtime.errors import RuntimeViolation
from forgeflow_runtime.policy_loader import RuntimePolicy
from forgeflow_runtime.workflow_engine import workflow_from_runtime_policy
from forgeflow_runtime.workflow_override import resolve_project_workflow


def _policy() -> RuntimePolicy:
    return RuntimePolicy(
        workflow_stages=["clarify", "plan", "execute", "spec-review", "quality-review", "finalize"],
        stage_requirements={
            "clarify": [],
            "plan": ["brief.json"],
            "execute": ["plan-ledger.json"],
            "spec-review": ["implementation-evidence.json"],
            "quality-review": ["implementation-evidence.json"],
            "finalize": ["review-report.json"],
        },
        stage_gate_map={
            "spec-review": "spec_review_passed",
            "quality-review": "quality_review_passed",
        },
        gate_requirements={},
        gate_reviews={},
        routes={
            "small": {"stages": ["clarify", "execute", "quality-review", "finalize"]},
            "medium": {"stages": ["clarify", "plan", "execute", "quality-review", "finalize"]},
            "high": {
                "stages": [
                    "clarify",
                    "plan",
                    "execute",
                    "spec-review",
                    "quality-review",
                    "finalize",
                ]
            },
        },
        finalize_flags=[],
        review_order=["spec-review", "quality-review"],
    )


def _write_override(root: Path, content: str) -> Path:
    override_path = root / ".forgeflow" / "workflow.yaml"
    override_path.parent.mkdir(parents=True)
    override_path.write_text(content.strip() + "\n", encoding="utf-8")
    return override_path


def test_missing_project_workflow_returns_canonical_workflow(tmp_path: Path) -> None:
    policy = _policy()

    workflow = resolve_project_workflow(tmp_path, policy)

    canonical = workflow_from_runtime_policy(policy)
    assert workflow.routes == canonical.routes
    assert workflow.steps == canonical.steps
    assert workflow.name == "runtime-policy"


def test_valid_override_reorders_known_route_stages(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
        routes:
          medium:
            - clarify
            - execute
            - quality-review
            - finalize
        """,
    )

    workflow = resolve_project_workflow(tmp_path, _policy())

    assert workflow.routes["medium"] == ["clarify", "execute", "quality-review", "finalize"]
    assert workflow.routes["small"] == ["clarify", "execute", "quality-review", "finalize"]


def test_valid_override_changes_role_for_known_step(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
        steps:
          execute:
            role: frontend-worker
        """,
    )

    workflow = resolve_project_workflow(tmp_path, _policy())

    assert workflow.steps["execute"].role == "frontend-worker"
    assert workflow.steps["execute"].required_for_entry == ["plan-ledger.json"]


def test_override_that_removes_canonical_gate_fails(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
        steps:
          quality-review:
            gate: null
        """,
    )

    with pytest.raises(RuntimeViolation, match="cannot change canonical gate for step quality-review"):
        resolve_project_workflow(tmp_path, _policy())


def test_override_that_changes_required_for_entry_fails(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
        steps:
          execute:
            required_for_entry:
              - brief.json
        """,
    )

    with pytest.raises(RuntimeViolation, match="cannot change canonical required_for_entry for step execute"):
        resolve_project_workflow(tmp_path, _policy())


def test_override_that_references_unknown_step_fails(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
        routes:
          small:
            - clarify
            - mystery
        """,
    )

    with pytest.raises(RuntimeViolation, match="unknown workflow step in route small: mystery"):
        resolve_project_workflow(tmp_path, _policy())


def test_override_that_references_unknown_route_fails(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
        routes:
          emergency:
            - clarify
            - execute
        """,
    )

    with pytest.raises(RuntimeViolation, match="unknown workflow route: emergency"):
        resolve_project_workflow(tmp_path, _policy())
