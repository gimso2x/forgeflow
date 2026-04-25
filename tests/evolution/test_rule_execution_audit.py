from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import forgeflow_runtime.evolution as evolution_runtime
from forgeflow_runtime.evolution import adopt_example_rule, execute_rule


ROOT = Path(__file__).resolve().parents[2]


def _audit_events(root: Path) -> list[dict]:
    log_path = root / ".forgeflow" / "evolution" / "audit-log.jsonl"
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]


def _write_project_rule(tmp_path: Path, rule: dict) -> None:
    project_rule_dir = tmp_path / ".forgeflow" / "evolution" / "rules"
    project_rule_dir.mkdir(parents=True, exist_ok=True)
    (project_rule_dir / f"{rule['id']}-rule.json").write_text(json.dumps(rule), encoding="utf-8")


def _valid_rule() -> dict:
    return json.loads((ROOT / "examples" / "evolution" / "no-env-commit-rule.json").read_text(encoding="utf-8"))


def test_execute_rule_records_audit_event_for_passed_rule(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)

    execute = execute_rule(tmp_path, "no-env-commit")

    events = _audit_events(tmp_path)
    assert [event["event"] for event in events] == ["adopt", "execute"]
    event = events[-1]
    assert event["rule_id"] == "no-env-commit"
    assert event["passed"] is True
    assert event["executed"] is True
    assert event["exit_code"] == execute["exit_code"]
    assert event["expected_exit_code"] == 0
    assert event["timestamp"].endswith("Z")


def test_execute_rule_records_audit_event_when_safety_checks_block_execution(tmp_path: Path) -> None:
    rule = _valid_rule()
    rule["check"] = {"kind": "command", "command": "touch SHOULD_NOT_EXIST", "expected_exit_code": 0}
    _write_project_rule(tmp_path, rule)

    execute = execute_rule(tmp_path, "no-env-commit")

    events = _audit_events(tmp_path)
    assert len(events) == 1
    event = events[0]
    assert event["event"] == "execute"
    assert event["rule_id"] == "no-env-commit"
    assert event["passed"] is False
    assert event["executed"] is False
    assert event["failed_safety_checks"] == ["check_shape", "approved_command", "approved_command_contract"]
    assert execute["executed"] is False


def test_execute_rule_timeout_appends_audit_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)

    def timeout_command(command_id: str, root: Path):
        raise subprocess.TimeoutExpired(cmd=["forgeflow-approved-command", command_id], timeout=30, output="partial")

    monkeypatch.setattr(evolution_runtime, "_run_approved_command", timeout_command)

    result = execute_rule(tmp_path, "no-env-commit")

    assert result["passed"] is False
    assert result["executed"] is True
    events = _audit_events(tmp_path)
    assert events[-1]["event"] == "execute"
    assert events[-1]["rule_id"] == "no-env-commit"
    assert events[-1]["passed"] is False
    assert events[-1]["exit_code"] is None
    assert events[-1]["timeout"] is True
