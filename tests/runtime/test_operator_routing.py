import json
from pathlib import Path

import pytest

from forgeflow_runtime.operator_routing import effective_route, role_for_stage
from forgeflow_runtime.orchestrator import RuntimeViolation


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_effective_route_uses_explicit_route_before_artifacts(tmp_path: Path) -> None:
    _write_json(tmp_path / "checkpoint.json", {"route": "large_high_risk"})

    assert effective_route(task_dir=tmp_path, explicit_route="small", min_route=None) == "small"


def test_effective_route_promotes_auto_detected_route_to_minimum(tmp_path: Path) -> None:
    _write_json(tmp_path / "brief.json", {"risk_level": "low"})

    assert effective_route(task_dir=tmp_path, explicit_route=None, min_route="medium") == "medium"


def test_effective_route_reads_existing_runtime_artifact_route(tmp_path: Path) -> None:
    _write_json(tmp_path / "session-state.json", {"route": "large_high_risk"})

    assert effective_route(task_dir=tmp_path, explicit_route=None, min_route=None) == "large_high_risk"


def test_role_for_stage_rejects_unknown_stage() -> None:
    with pytest.raises(RuntimeViolation, match="no default role mapping"):
        role_for_stage("bogus", violation_factory=RuntimeViolation)
