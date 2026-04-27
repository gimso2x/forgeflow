from __future__ import annotations

import json
import subprocess
import sys

from pathlib import Path

from forgeflow_runtime.evolution import adopt_example_rule, doctor_evolution_state
from forgeflow_runtime.evolution_doctor import _audit_log_health, _collect_rule_health


ROOT = Path(__file__).resolve().parents[2]


def _write_project_rule(tmp_path: Path, rule: dict) -> None:
    project_rule_dir = tmp_path / ".forgeflow" / "evolution" / "rules"
    project_rule_dir.mkdir(parents=True, exist_ok=True)
    (project_rule_dir / f"{rule['id']}-rule.json").write_text(json.dumps(rule), encoding="utf-8")


def _valid_rule() -> dict:
    return json.loads((ROOT / "examples" / "evolution" / "no-env-commit-rule.json").read_text(encoding="utf-8"))


def test_rule_health_seam_reports_rule_safety_and_issues(tmp_path: Path) -> None:
    rule = _valid_rule()
    rule["check"]["command_id"] = "evil-command"
    _write_project_rule(tmp_path, rule)

    health = _collect_rule_health(
        tmp_path,
        loader=lambda root: [(rule, root / ".forgeflow" / "evolution" / "rules" / "no-env-commit-rule.json")],
        source="active",
        issue_code="unsafe_active_rule",
    )

    assert health.rule_ids == {"no-env-commit"}
    assert health.rules[0]["safe_to_execute"] is False
    assert health.issues == [
        {
            "severity": "error",
            "code": "unsafe_active_rule",
            "rule_id": "no-env-commit",
            "path": str(tmp_path / ".forgeflow" / "evolution" / "rules" / "no-env-commit-rule.json"),
            "failed_safety_checks": ["approved_command", "approved_command_contract"],
        }
    ]


def test_audit_log_health_seam_reports_counts_last_event_and_issues(tmp_path: Path) -> None:
    audit_path = tmp_path / ".forgeflow" / "evolution" / "audit-log.jsonl"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "timestamp": "2026-04-27T00:00:00Z",
                "event": "adopt",
                "rule_id": "x",
                "passed": True,
            }
        )
        + "\n"
        + '{"event":"missing-fields","rule_id":"x"}\n'
        + "not-json\n",
        encoding="utf-8",
    )

    health = _audit_log_health(audit_path)

    assert health.events_count == 2
    assert health.last_event == {"event": "missing-fields", "rule_id": "x"}
    assert [issue["code"] for issue in health.issues] == ["audit_event_missing_fields", "invalid_audit_json"]
    assert health.issues[0]["line"] == 2
    assert health.issues[1]["line"] == 3


def test_doctor_reports_clean_lifecycle_state(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    report = doctor_evolution_state(tmp_path)

    assert report["ok"] is True
    assert report["summary"]["active_rules"] == 1
    assert report["summary"]["retired_rules"] == 0
    assert report["summary"]["audit_events"] == 1
    assert report["issues"] == []
    assert report["active_rules"][0]["safe_to_execute"] is True


def test_doctor_detects_unsafe_active_rule_and_duplicate_retired_rule(tmp_path: Path) -> None:
    rule = _valid_rule()
    rule["check"]["command_id"] = "evil-command"
    _write_project_rule(tmp_path, rule)
    retired_dir = tmp_path / ".forgeflow" / "evolution" / "retired-rules"
    retired_dir.mkdir(parents=True)
    (retired_dir / "no-env-commit-rule.json").write_text(json.dumps(_valid_rule()), encoding="utf-8")

    report = doctor_evolution_state(tmp_path)

    assert report["ok"] is False
    issue_codes = [issue["code"] for issue in report["issues"]]
    assert "unsafe_active_rule" in issue_codes
    assert "duplicate_active_retired_rule" in issue_codes
    assert report["active_rules"][0]["failed_safety_checks"] == ["approved_command", "approved_command_contract"]


def test_doctor_detects_broken_audit_jsonl(tmp_path: Path) -> None:
    audit_path = tmp_path / ".forgeflow" / "evolution" / "audit-log.jsonl"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text('{"event":"adopt","rule_id":"x"}\nnot-json\n', encoding="utf-8")

    report = doctor_evolution_state(tmp_path)

    assert report["ok"] is False
    assert any(issue["code"] == "invalid_audit_json" and issue["line"] == 2 for issue in report["issues"])


def test_doctor_cli_outputs_json_contract(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "doctor", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["summary"]["active_rules"] == 1
    assert payload["summary"]["audit_events"] == 1


def test_doctor_cli_human_output_names_closed_loop_signals(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "doctor"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Evolution doctor:" in result.stdout
    assert "closed-loop surfaces:" in result.stdout
    assert "reactive fix learning: advisory metadata only" in result.stdout
    assert "proactive feedback learning: raw text disabled" in result.stdout
    assert "meta effectiveness review: audit-backed only" in result.stdout
