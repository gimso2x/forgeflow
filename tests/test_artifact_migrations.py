from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from forgeflow_runtime.artifact_migrations import (
    ARTIFACT_VERSION_POLICY,
    CURRENT_ARTIFACT_SCHEMA_VERSION,
    MINIMUM_SUPPORTED_SCHEMA_VERSION,
    RUNTIME_VERSION_MODE,
    _migrate_0_1_to_0_2,
    migrate_artifact_payload,
)
from forgeflow_runtime.artifact_validation import validate_artifact_payload
from forgeflow_runtime.errors import RuntimeViolation


ROOT = Path(__file__).resolve().parents[1]


def test_artifact_version_policy_names_supported_versions_per_artifact_type() -> None:
    for artifact_name in ["brief", "plan", "run-state", "review-report", "checkpoint", "session-state"]:
        assert ARTIFACT_VERSION_POLICY[artifact_name].current == CURRENT_ARTIFACT_SCHEMA_VERSION
        assert MINIMUM_SUPPORTED_SCHEMA_VERSION in ARTIFACT_VERSION_POLICY[artifact_name].supported
        assert CURRENT_ARTIFACT_SCHEMA_VERSION in ARTIFACT_VERSION_POLICY[artifact_name].supported
        assert ARTIFACT_VERSION_POLICY[artifact_name].runtime_mode == RUNTIME_VERSION_MODE


def test_migrate_artifact_payload_noop_when_already_current() -> None:
    payload = {
        "schema_version": CURRENT_ARTIFACT_SCHEMA_VERSION,
        "task_id": "t-migrate",
        "objective": "keep current schema stable",
        "risk_level": "low",
        "in_scope": [],
        "out_of_scope": [],
        "constraints": [],
        "acceptance_criteria": [],
    }

    migrated, report = migrate_artifact_payload(
        artifact_name="brief",
        payload=payload,
        source_name="brief.json",
        target_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
    )

    assert migrated == payload
    assert migrated is not payload
    assert report.changed is False
    assert report.from_version == CURRENT_ARTIFACT_SCHEMA_VERSION
    assert report.to_version == CURRENT_ARTIFACT_SCHEMA_VERSION
    assert "noop" in report.steps[0]
    validate_artifact_payload(artifact_name="brief", payload=migrated, source_name="brief.json")


def test_migrate_0_1_to_0_2_brief_adds_specialist_fields() -> None:
    old_brief = {
        "schema_version": "0.1",
        "task_id": "t-old",
        "objective": "old brief without specialists",
        "risk_level": "medium",
        "in_scope": [],
        "out_of_scope": [],
        "constraints": [],
        "acceptance_criteria": [],
    }

    migrated, report = migrate_artifact_payload(
        artifact_name="brief",
        payload=old_brief,
        source_name="brief.json",
    )

    assert migrated["schema_version"] == "0.2"
    assert migrated["required_specialists"] == []
    assert migrated["skipped_specialists"] == []
    assert migrated["skip_rationale"] == ""
    assert report.changed is True
    assert "0.1->0.2" in report.steps


def test_migrate_0_1_to_0_2_review_report_adds_roles() -> None:
    old_review = {
        "schema_version": "0.1",
        "verdict": "pass",
        "findings": [],
    }

    migrated, report = migrate_artifact_payload(
        artifact_name="review-report",
        payload=old_review,
        source_name="review-report.json",
    )

    assert migrated["schema_version"] == "0.2"
    assert "review_roles" in migrated
    assert "spec-review" in migrated["review_roles"]
    assert report.changed is True


def test_migrate_0_1_to_0_2_preserves_existing_fields() -> None:
    old_review = {
        "schema_version": "0.1",
        "verdict": "pass",
        "findings": [],
        "review_roles": ["security-review"],
    }

    migrated, _ = migrate_artifact_payload(
        artifact_name="review-report",
        payload=old_review,
        source_name="review-report.json",
    )

    assert migrated["schema_version"] == "0.2"
    assert migrated["review_roles"] == ["security-review"]


def test_migrate_0_1_to_0_2_generic_artifact_bumps_version_only() -> None:
    old_plan = {
        "schema_version": "0.1",
        "task_id": "t-plan",
        "steps": [],
    }

    migrated, report = migrate_artifact_payload(
        artifact_name="plan",
        payload=old_plan,
        source_name="plan.json",
    )

    assert migrated["schema_version"] == "0.2"
    assert report.changed is True


def test_validate_artifact_payload_refuses_unknown_versions() -> None:
    payload = {"schema_version": "9.9", "task_id": "bad"}

    with pytest.raises(RuntimeViolation) as exc:
        validate_artifact_payload(artifact_name="brief", payload=payload, source_name="brief.json")

    assert "unsupported schema_version 9.9" in str(exc.value)
    assert RUNTIME_VERSION_MODE in str(exc.value)


def test_validate_artifact_payload_accepts_current_version() -> None:
    payload = {
        "schema_version": CURRENT_ARTIFACT_SCHEMA_VERSION,
        "task_id": "t-ok",
        "objective": "test",
        "risk_level": "low",
        "in_scope": [],
        "out_of_scope": [],
        "constraints": [],
        "acceptance_criteria": [],
    }
    validate_artifact_payload(artifact_name="brief", payload=payload, source_name="brief.json")


def test_validate_artifact_payload_refuses_minimum_version_without_migration() -> None:
    """0.1 artifacts must be migrated before validation; raw 0.1 payloads are refused."""
    payload = {
        "schema_version": MINIMUM_SUPPORTED_SCHEMA_VERSION,
        "task_id": "t-old",
        "objective": "test",
        "risk_level": "low",
        "in_scope": [],
        "out_of_scope": [],
        "constraints": [],
        "acceptance_criteria": [],
    }
    with pytest.raises(RuntimeViolation):
        validate_artifact_payload(artifact_name="brief", payload=payload, source_name="brief.json")


def test_migrate_0_1_to_0_2_direct_function() -> None:
    result = _migrate_0_1_to_0_2(
        {"schema_version": "0.1", "task_id": "x"},
        "plan",
    )
    assert result["schema_version"] == "0.2"
    assert result["task_id"] == "x"


def test_all_example_fixtures_use_current_schema_version() -> None:
    fixtures_dir = ROOT / "examples" / "runtime-fixtures"
    assert fixtures_dir.exists(), "examples/runtime-fixtures must be present for schema drift coverage"

    stale = []
    for f in fixtures_dir.rglob("*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        sv = data.get("schema_version")
        if sv and sv != CURRENT_ARTIFACT_SCHEMA_VERSION:
            stale.append(f"{f.relative_to(ROOT)}: {sv}")

    assert not stale, f"Fixtures with stale schema_version: {stale}"
