from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from forgeflow_runtime.artifact_migrations import (
    ARTIFACT_VERSION_POLICY,
    migrate_artifact_payload,
)
from forgeflow_runtime.artifact_validation import validate_artifact_payload
from forgeflow_runtime.errors import RuntimeViolation


ROOT = Path(__file__).resolve().parents[1]


def test_artifact_version_policy_names_supported_versions_per_artifact_type() -> None:
    for artifact_name in ["brief", "plan", "run-state", "review-report", "checkpoint", "session-state"]:
        assert ARTIFACT_VERSION_POLICY[artifact_name].current == "0.1"
        assert ARTIFACT_VERSION_POLICY[artifact_name].supported == ("0.1",)
        assert ARTIFACT_VERSION_POLICY[artifact_name].runtime_mode == "validate_current_refuse_unknown"


def test_migrate_artifact_payload_has_testable_noop_scaffold() -> None:
    payload = {
        "schema_version": "0.1",
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
        target_version="0.1",
    )

    assert migrated == payload
    assert migrated is not payload
    assert report.changed is False
    assert report.from_version == "0.1"
    assert report.to_version == "0.1"
    assert report.steps == ["0.1->0.1 noop"]
    validate_artifact_payload(artifact_name="brief", payload=migrated, source_name="brief.json")


def test_validate_artifact_payload_refuses_unknown_versions_with_policy_hint() -> None:
    payload = {"schema_version": "9.9", "task_id": "bad"}

    with pytest.raises(RuntimeViolation) as exc:
        validate_artifact_payload(artifact_name="brief", payload=payload, source_name="brief.json")

    assert "unsupported schema_version 9.9" in str(exc.value)
    assert "run scripts/upgrade_artifact.py" in str(exc.value)


def test_upgrade_artifact_script_performs_noop_migration(tmp_path: Path) -> None:
    artifact = tmp_path / "brief.json"
    artifact.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "task_id": "t-script",
                "objective": "script smoke",
                "risk_level": "low",
                "in_scope": [],
                "out_of_scope": [],
                "constraints": [],
                "acceptance_criteria": [],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "upgrade_artifact.py"),
            "--artifact-name",
            "brief",
            "--path",
            str(artifact),
            "--target-version",
            "0.1",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "0.1->0.1 noop" in result.stdout
    assert json.loads(artifact.read_text(encoding="utf-8"))["schema_version"] == "0.1"


def test_artifact_model_documents_upgrade_policy() -> None:
    text = (ROOT / "docs" / "artifact-model.md").read_text(encoding="utf-8")
    for required in [
        "Artifact schema migration policy",
        "scripts/upgrade_artifact.py",
        "validate_current_refuse_unknown",
        ".forgeflow/tasks/*",
        "0.1 -> 0.1 no-op",
    ]:
        assert required in text
