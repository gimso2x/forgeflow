from __future__ import annotations

import json
from pathlib import Path

from forgeflow_runtime.evolution import execute_rule


ROOT = Path(__file__).resolve().parents[2]


def _write_project_rule(tmp_path: Path, rule: dict) -> None:
    project_rule_dir = tmp_path / ".forgeflow" / "evolution" / "rules"
    project_rule_dir.mkdir(parents=True, exist_ok=True)
    (project_rule_dir / f"{rule['id']}-rule.json").write_text(json.dumps(rule), encoding="utf-8")


def _valid_rule() -> dict:
    return json.loads((ROOT / "examples" / "evolution" / "no-env-commit-rule.json").read_text(encoding="utf-8"))


def test_execute_rejects_project_rule_with_incomplete_hard_gate_evidence(tmp_path: Path) -> None:
    rule = _valid_rule()
    rule["hard_gate_evidence"].pop("audit_trail")
    _write_project_rule(tmp_path, rule)

    result = execute_rule(tmp_path, "no-env-commit")

    assert result["executed"] is False
    assert result["passed"] is False
    assert result["safety_checks"]["hard_gate_evidence_complete"] is False


def test_execute_rejects_unapproved_shell_command_even_with_valid_metadata(tmp_path: Path) -> None:
    rule = _valid_rule()
    rule["check"] = {"kind": "command", "command": "touch SHOULD_NOT_EXIST", "expected_exit_code": 0}
    _write_project_rule(tmp_path, rule)

    result = execute_rule(tmp_path, "no-env-commit")

    assert result["executed"] is False
    assert result["passed"] is False
    assert result["safety_checks"]["approved_command"] is False
    assert not (tmp_path / "SHOULD_NOT_EXIST").exists()


def test_execute_rejects_wrong_check_shape(tmp_path: Path) -> None:
    rule = _valid_rule()
    rule["check"] = {"kind": "python", "command": "git status", "expected_exit_code": "0"}
    _write_project_rule(tmp_path, rule)

    result = execute_rule(tmp_path, "no-env-commit")

    assert result["executed"] is False
    assert result["safety_checks"]["check_shape"] is False
