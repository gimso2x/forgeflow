from __future__ import annotations

import json
import subprocess
import sys

import pytest
import forgeflow_runtime.evolution as evolution_runtime
from pathlib import Path

from forgeflow_runtime.evolution import adopt_example_rule, doctor_evolution_state, effectiveness_review, promotion_plan, proposal_approve, proposal_approvals, promotion_decision, promotion_gate, list_promotions, promote_rule, promote_stub, promotion_ready, proposal_review, write_promotion_plan, dry_run_rule, execute_rule, inspect_evolution_policy, list_rules


ROOT = Path(__file__).resolve().parents[1]


def test_inspect_evolution_policy_reports_read_only_boundaries() -> None:
    report = inspect_evolution_policy(ROOT)

    assert report["policy_version"] == 0.2
    assert report["global"]["activation"] == "explicit_opt_in"
    assert report["global"]["can_block"] is False
    assert report["global"]["advises"] == ["clarify", "plan"]
    assert report["project"]["can_enforce_hard"] is True
    assert report["retrieval_contract"]["max_patterns"] == 3
    assert report["runtime_enforcement"] == "not_enabled"
    assert report["examples_valid"] is True
    assert [rule["id"] for rule in report["project_hard_examples"]] == [
        "generated-adapter-drift",
        "no-env-commit",
    ]
    assert all(rule["scope"] == "project" for rule in report["project_hard_examples"])
    assert all(rule["mode"] == "hard_exit_2" for rule in report["project_hard_examples"])


def test_forgeflow_evolution_inspect_cli_outputs_json_contract() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "inspect", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["global"]["can_block"] is False
    assert payload["project"]["can_enforce_hard"] is True
    assert payload["runtime_enforcement"] == "not_enabled"


def test_forgeflow_evolution_inspect_cli_human_output_names_safety_contract() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "inspect"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "global advisory only" in result.stdout
    assert "project HARD examples valid" in result.stdout
    assert "runtime enforcement: not enabled" in result.stdout


def test_dry_run_rule_reports_command_without_executing_it() -> None:
    result = dry_run_rule(ROOT, "generated-adapter-drift")

    assert result["rule_id"] == "generated-adapter-drift"
    assert result["would_execute"] is False
    assert result["safe_to_execute_later"] is True
    assert result["mode"] == "hard_exit_2"
    assert "python3 scripts/generate_adapters.py" in result["command"]
    assert result["safety_checks"]["scope_project"] is True
    assert result["safety_checks"]["deterministic"] is True
    assert result["safety_checks"]["global_export_disabled"] is True


def test_dry_run_rule_rejects_unknown_rule_id() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "dry-run", "--rule", "missing-rule"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "unknown evolution rule" in result.stderr


def test_forgeflow_evolution_dry_run_cli_outputs_json_without_execution() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "dry-run", "--rule", "no-env-commit", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["rule_id"] == "no-env-commit"
    assert payload["would_execute"] is False
    assert payload["safe_to_execute_later"] is True
    assert payload["safety_checks"]["raw_evidence_absent"] is True


def test_forgeflow_evolution_dry_run_human_output_says_no_command_execution() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "dry-run", "--rule", "generated-adapter-drift"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "would execute: false" in result.stdout
    assert "command not executed" in result.stdout
    assert "safe to execute later: true" in result.stdout


def test_execute_rule_runs_safe_project_rule_when_explicitly_allowed(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    project_rule_dir = tmp_path / ".forgeflow" / "evolution" / "rules"
    project_rule_dir.mkdir(parents=True)
    source = ROOT / "examples" / "evolution" / "no-env-commit-rule.json"
    (project_rule_dir / "no-env-commit-rule.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    result = execute_rule(tmp_path, "no-env-commit")

    assert result["rule_id"] == "no-env-commit"
    assert result["source"] == "project"
    assert result["executed"] is True
    assert result["exit_code"] == 0
    assert result["expected_exit_code"] == 0
    assert result["passed"] is True
    assert result["would_execute"] is True
    assert result["safety_checks"]["scope_project"] is True


def test_forgeflow_evolution_execute_requires_explicit_danger_flag() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "execute", "--rule", "no-env-commit"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "requires --i-understand-project-local-hard-rule" in result.stderr


def test_forgeflow_evolution_execute_cli_outputs_json_after_gated_run(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    project_rule_dir = tmp_path / ".forgeflow" / "evolution" / "rules"
    project_rule_dir.mkdir(parents=True)
    source = ROOT / "examples" / "evolution" / "no-env-commit-rule.json"
    (project_rule_dir / "no-env-commit-rule.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "execute",
            "--rule",
            "no-env-commit",
            "--i-understand-project-local-hard-rule",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["rule_id"] == "no-env-commit"
    assert payload["executed"] is True
    assert payload["passed"] is True
    assert payload["exit_code"] == 0


def test_list_rules_separates_examples_from_project_local_rules(tmp_path: Path) -> None:
    project_rule_dir = tmp_path / ".forgeflow" / "evolution" / "rules"
    project_rule_dir.mkdir(parents=True)
    source = ROOT / "examples" / "evolution" / "no-env-commit-rule.json"
    (project_rule_dir / "no-env-commit-rule.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    registry = list_rules(tmp_path, include_examples=True, fallback_root=ROOT)

    assert [rule["id"] for rule in registry["project_rules"]] == ["no-env-commit"]
    assert all(rule["source"] == "project" for rule in registry["project_rules"])
    assert "generated-adapter-drift" in [rule["id"] for rule in registry["example_rules"]]
    assert all(rule["source"] == "example" for rule in registry["example_rules"])


def test_execute_rejects_example_rule_unless_copied_to_project_registry() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "execute",
            "--rule",
            "no-env-commit",
            "--i-understand-project-local-hard-rule",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "not found in project-local registry" in result.stderr


def test_dry_run_can_read_examples_but_marks_source_example() -> None:
    result = dry_run_rule(ROOT, "generated-adapter-drift")

    assert result["source"] == "example"
    assert result["would_execute"] is False


def test_forgeflow_evolution_list_cli_shows_project_and_example_sources(tmp_path: Path) -> None:
    project_rule_dir = tmp_path / ".forgeflow" / "evolution" / "rules"
    project_rule_dir.mkdir(parents=True)
    source = ROOT / "examples" / "evolution" / "no-env-commit-rule.json"
    (project_rule_dir / "no-env-commit-rule.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "list", "--include-examples", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["project_rules"][0]["id"] == "no-env-commit"
    assert payload["project_rules"][0]["source"] == "project"
    assert payload["example_rules"][0]["source"] == "example"


def test_adopt_example_rule_copies_safe_example_into_project_registry(tmp_path: Path) -> None:
    result = adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)

    assert result["adopted"] is True
    assert result["rule_id"] == "no-env-commit"
    assert result["destination"].endswith(".forgeflow/evolution/rules/no-env-commit-rule.json")
    assert Path(result["destination"]).is_file()
    registry = list_rules(tmp_path)
    assert [rule["id"] for rule in registry["project_rules"]] == ["no-env-commit"]


def test_adopt_example_rule_refuses_to_overwrite_existing_project_rule(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)

    try:
        adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    except FileExistsError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("expected duplicate adoption to fail")


def test_forgeflow_evolution_adopt_cli_then_execute_project_rule(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    adopt = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "adopt", "--example", "no-env-commit", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert adopt.returncode == 0, adopt.stderr
    adopt_payload = json.loads(adopt.stdout)
    assert adopt_payload["adopted"] is True

    execute = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "execute",
            "--rule",
            "no-env-commit",
            "--i-understand-project-local-hard-rule",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert execute.returncode == 0, execute.stderr
    execute_payload = json.loads(execute.stdout)
    assert execute_payload["source"] == "project"
    assert execute_payload["passed"] is True


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


def test_adopt_example_ignores_project_rules_in_fallback_root(tmp_path: Path) -> None:
    fallback = tmp_path / "fallback"
    target = tmp_path / "target"
    fallback_project_rule_dir = fallback / ".forgeflow" / "evolution" / "rules"
    fallback_project_rule_dir.mkdir(parents=True)
    rule = _valid_rule()
    (fallback_project_rule_dir / "no-env-commit-rule.json").write_text(json.dumps(rule), encoding="utf-8")
    example_dir = fallback / "examples" / "evolution"
    example_dir.mkdir(parents=True)
    (example_dir / "no-env-commit-rule.json").write_text((ROOT / "examples" / "evolution" / "no-env-commit-rule.json").read_text(encoding="utf-8"), encoding="utf-8")
    (example_dir / "generated-adapter-drift-rule.json").write_text((ROOT / "examples" / "evolution" / "generated-adapter-drift-rule.json").read_text(encoding="utf-8"), encoding="utf-8")

    result = adopt_example_rule(target, "no-env-commit", fallback_root=fallback)

    assert result["adopted"] is True
    assert "/examples/evolution/" in result["source"]


def _audit_events(root: Path) -> list[dict]:
    audit_path = root / ".forgeflow" / "evolution" / "audit-log.jsonl"
    return [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]


def test_adopt_example_rule_records_project_local_audit_event(tmp_path: Path) -> None:
    result = adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)

    events = _audit_events(tmp_path)
    assert len(events) == 1
    event = events[0]
    assert event["event"] == "adopt"
    assert event["rule_id"] == "no-env-commit"
    assert event["source"] == result["source"]
    assert event["destination"] == result["destination"]
    assert event["passed"] is True
    assert event["timestamp"].endswith("Z")
    assert event["schema_version"] == 1


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
    assert event["failed_safety_checks"] == ["check_shape", "approved_command"]
    assert execute["executed"] is False


def test_audit_events_returns_recent_events_limited_newest_last(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    execute_rule(tmp_path, "no-env-commit")

    from forgeflow_runtime.evolution import audit_events

    result = audit_events(tmp_path, limit=1)
    events = result["events"]

    assert len(events) == 1
    assert events[0]["event"] == "execute"
    assert events[0]["rule_id"] == "no-env-commit"


def test_audit_cli_outputs_json_events(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    execute_rule(tmp_path, "no-env-commit")

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "audit", "--limit", "1", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["audit_log"].endswith(".forgeflow/evolution/audit-log.jsonl")
    assert len(payload["events"]) == 1
    assert payload["events"][0]["event"] == "execute"


def test_audit_cli_human_output_handles_empty_log(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "audit"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Evolution audit log:" in result.stdout
    assert "- <none>" in result.stdout


def test_retire_project_rule_moves_rule_out_of_active_registry_and_records_audit(tmp_path: Path) -> None:
    adopt = adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)

    from forgeflow_runtime.evolution import retire_rule

    result = retire_rule(tmp_path, "no-env-commit", reason="false positive in this project")

    assert result["retired"] is True
    assert result["rule_id"] == "no-env-commit"
    assert not Path(adopt["destination"]).exists()
    assert Path(result["destination"]).is_file()
    registry = list_rules(tmp_path)
    assert registry["project_rules"] == []
    events = _audit_events(tmp_path)
    assert events[-1]["event"] == "retire"
    assert events[-1]["rule_id"] == "no-env-commit"
    assert events[-1]["reason"] == "false positive in this project"


def test_retire_cli_outputs_json_and_prevents_later_execute(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)

    retire = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "retire", "--rule", "no-env-commit", "--reason", "too noisy", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert retire.returncode == 0, retire.stderr
    payload = json.loads(retire.stdout)
    assert payload["retired"] is True
    execute = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "execute", "--rule", "no-env-commit", "--i-understand-project-local-hard-rule"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert execute.returncode == 1
    assert "not found in project-local registry" in execute.stderr


def test_retire_cli_missing_rule_returns_clean_error(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "retire", "--rule", "missing", "--reason", "not needed"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Error:" in result.stderr
    assert "not found in project-local registry" in result.stderr
    assert "Traceback" not in result.stderr


def test_retire_rule_rolls_back_move_when_audit_write_fails(tmp_path: Path, monkeypatch) -> None:
    adopt = adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)

    from forgeflow_runtime import evolution

    def fail_audit(root: Path, event: dict) -> None:
        raise OSError("audit disk full")

    monkeypatch.setattr(evolution, "_append_audit_event", fail_audit)

    try:
        evolution.retire_rule(tmp_path, "no-env-commit", reason="test rollback")
    except OSError as exc:
        assert "audit disk full" in str(exc)
    else:
        raise AssertionError("expected audit failure")

    assert Path(adopt["destination"]).is_file()
    registry = list_rules(tmp_path)
    assert [rule["id"] for rule in registry["project_rules"]] == ["no-env-commit"]


def test_restore_retired_rule_moves_rule_back_to_active_registry_and_records_audit(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    from forgeflow_runtime.evolution import restore_rule, retire_rule

    retire_rule(tmp_path, "no-env-commit", reason="too noisy")
    result = restore_rule(tmp_path, "no-env-commit", reason="false positive fixed")

    assert result["restored"] is True
    assert result["rule_id"] == "no-env-commit"
    assert Path(result["destination"]).is_file()
    registry = list_rules(tmp_path)
    assert [rule["id"] for rule in registry["project_rules"]] == ["no-env-commit"]
    events = _audit_events(tmp_path)
    assert events[-1]["event"] == "restore"
    assert events[-1]["reason"] == "false positive fixed"


def test_restore_cli_outputs_json_and_allows_later_execute(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    from forgeflow_runtime.evolution import retire_rule
    retire_rule(tmp_path, "no-env-commit", reason="too noisy")

    restore = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "restore", "--rule", "no-env-commit", "--reason", "needed again", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert restore.returncode == 0, restore.stderr
    payload = json.loads(restore.stdout)
    assert payload["restored"] is True
    execute = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "execute", "--rule", "no-env-commit", "--i-understand-project-local-hard-rule", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert execute.returncode == 0, execute.stderr


def test_restore_rule_rolls_back_move_when_audit_write_fails(tmp_path: Path, monkeypatch) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    from forgeflow_runtime import evolution
    evolution.retire_rule(tmp_path, "no-env-commit", reason="too noisy")

    retired = tmp_path / ".forgeflow" / "evolution" / "retired-rules" / "no-env-commit-rule.json"

    def fail_audit(root: Path, event: dict) -> None:
        raise OSError("audit disk full")

    monkeypatch.setattr(evolution, "_append_audit_event", fail_audit)

    try:
        evolution.restore_rule(tmp_path, "no-env-commit", reason="test rollback")
    except OSError as exc:
        assert "audit disk full" in str(exc)
    else:
        raise AssertionError("expected audit failure")

    assert retired.is_file()
    assert list_rules(tmp_path)["project_rules"] == []


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
    assert report["active_rules"][0]["failed_safety_checks"] == ["approved_command"]


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


def test_effectiveness_review_reports_effective_candidate_from_clean_audit(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    execute_rule(tmp_path, "no-env-commit")
    execute_rule(tmp_path, "no-env-commit")

    report = effectiveness_review(tmp_path, "no-env-commit", since_days=30)

    assert report["rule_id"] == "no-env-commit"
    assert report["read_only"] is True
    assert report["window_days"] == 30
    assert report["metrics"]["executions"] == 2
    assert report["metrics"]["failures"] == 0
    assert report["recommendation"] == "effective_candidate"
    assert report["would_promote"] is False
    assert report["would_mutate"] is False


def test_effectiveness_review_marks_watch_candidate_after_one_failure(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    events = _audit_events(tmp_path)
    audit_path = tmp_path / ".forgeflow" / "evolution" / "audit-log.jsonl"
    events.append({
        "schema_version": 1,
        "timestamp": "2026-04-24T00:00:00Z",
        "event": "execute",
        "rule_id": "no-env-commit",
        "executed": True,
        "passed": False,
        "exit_code": 1,
        "expected_exit_code": 0,
        "failed_safety_checks": [],
    })
    audit_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    report = effectiveness_review(tmp_path, "no-env-commit", since_days=30)

    assert report["metrics"]["failures"] == 1
    assert report["recommendation"] == "watch_candidate"
    assert report["would_promote"] is False


def test_effectiveness_review_marks_promotion_candidate_after_repeated_failures_but_does_not_mutate(tmp_path: Path) -> None:
    adopt = adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    audit_path = tmp_path / ".forgeflow" / "evolution" / "audit-log.jsonl"
    events = _audit_events(tmp_path)
    for _ in range(2):
        events.append({
            "schema_version": 1,
            "timestamp": "2026-04-24T00:00:00Z",
            "event": "execute",
            "rule_id": "no-env-commit",
            "executed": True,
            "passed": False,
            "exit_code": 1,
            "expected_exit_code": 0,
            "failed_safety_checks": [],
        })
    audit_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    report = effectiveness_review(tmp_path, "no-env-commit", since_days=30)

    assert report["metrics"]["failures"] == 2
    assert report["recommendation"] == "promotion_candidate"
    assert report["would_promote"] is False
    assert Path(adopt["destination"]).is_file()


def test_effectiveness_cli_outputs_json_contract(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    execute_rule(tmp_path, "no-env-commit")

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "effectiveness", "--rule", "no-env-commit", "--since-days", "30", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["rule_id"] == "no-env-commit"
    assert payload["read_only"] is True
    assert payload["would_mutate"] is False


def test_effectiveness_cli_human_output_says_read_only(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "effectiveness", "--rule", "no-env-commit"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Evolution effectiveness:" in result.stdout
    assert "read-only: true" in result.stdout
    assert "would mutate: false" in result.stdout


def _append_failed_execute_events(root: Path, rule_id: str, count: int) -> None:
    audit_path = root / ".forgeflow" / "evolution" / "audit-log.jsonl"
    events = _audit_events(root)
    for _ in range(count):
        events.append({
            "schema_version": 1,
            "timestamp": "2026-04-24T00:00:00Z",
            "event": "execute",
            "rule_id": rule_id,
            "executed": True,
            "passed": False,
            "exit_code": 1,
            "expected_exit_code": 0,
            "failed_safety_checks": [],
        })
    audit_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")


def test_promotion_plan_builds_non_mutating_plan_for_candidate(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    _append_failed_execute_events(tmp_path, "no-env-commit", 2)

    plan = promotion_plan(tmp_path, "no-env-commit", since_days=30)

    assert plan["rule_id"] == "no-env-commit"
    assert plan["read_only"] is True
    assert plan["would_mutate"] is False
    assert plan["recommendation"] == "promotion_candidate"
    assert plan["evidence_summary"]["failures"] == 2
    assert "maintainer_approval" in plan["required_human_approvals"]
    assert "project_owner_approval" in plan["required_human_approvals"]
    assert plan["suggested_next_command"].startswith("python3 scripts/forgeflow_evolution.py effectiveness")


def test_promotion_plan_refuses_to_suggest_action_for_insufficient_data(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)

    plan = promotion_plan(tmp_path, "no-env-commit", since_days=30)

    assert plan["recommendation"] == "insufficient_data"
    assert plan["required_human_approvals"] == []
    assert "insufficient_effectiveness_evidence" in plan["risk_flags"]
    assert plan["suggested_next_command"] is None


def test_promotion_plan_cli_outputs_json_contract(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    _append_failed_execute_events(tmp_path, "no-env-commit", 2)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "promotion-plan", "--rule", "no-env-commit", "--since-days", "30", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["recommendation"] == "promotion_candidate"
    assert payload["would_mutate"] is False
    assert payload["evidence_summary"]["failures"] == 2


def test_promotion_plan_cli_human_output_says_no_mutation(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    _append_failed_execute_events(tmp_path, "no-env-commit", 2)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "promotion-plan", "--rule", "no-env-commit"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Evolution promotion plan:" in result.stdout
    assert "read-only: true" in result.stdout
    assert "would mutate: false" in result.stdout
    assert "required approvals:" in result.stdout


def test_write_promotion_plan_persists_proposal_without_audit_or_rule_mutation(tmp_path: Path) -> None:
    adopt = adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    before_events = _audit_events(tmp_path)
    _append_failed_execute_events(tmp_path, "no-env-commit", 2)
    events_after_failures = _audit_events(tmp_path)

    result = write_promotion_plan(tmp_path, "no-env-commit", since_days=30)

    proposal_path = Path(result["proposal_path"])
    assert proposal_path.is_file()
    assert proposal_path.parent == tmp_path / ".forgeflow" / "evolution" / "proposals"
    assert proposal_path.name.endswith("-no-env-commit-promotion-plan.json")
    payload = json.loads(proposal_path.read_text(encoding="utf-8"))
    assert payload["recommendation"] == "promotion_candidate"
    assert payload["would_mutate"] is False
    assert payload["proposal_written"] is True
    assert Path(adopt["destination"]).is_file()
    assert _audit_events(tmp_path) == events_after_failures
    assert len(events_after_failures) == len(before_events) + 2


def test_promotion_plan_cli_write_outputs_path_and_keeps_json_contract(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    _append_failed_execute_events(tmp_path, "no-env-commit", 2)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "promotion-plan", "--rule", "no-env-commit", "--since-days", "30", "--write", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["proposal_written"] is True
    assert payload["proposal_path"].endswith("-no-env-commit-promotion-plan.json")
    assert Path(payload["proposal_path"]).is_file()
    assert payload["would_mutate"] is False


def test_promotion_plan_cli_write_human_output_names_written_file(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    _append_failed_execute_events(tmp_path, "no-env-commit", 2)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "promotion-plan", "--rule", "no-env-commit", "--write"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "proposal written:" in result.stdout
    assert ".forgeflow/evolution/proposals/" in result.stdout


def _written_candidate_proposal(tmp_path: Path) -> dict:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    _append_failed_execute_events(tmp_path, "no-env-commit", 2)
    return write_promotion_plan(tmp_path, "no-env-commit", since_days=30)


def test_proposal_review_accepts_valid_candidate_and_remains_read_only(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    before_events = _audit_events(tmp_path)

    review = proposal_review(tmp_path, Path(written["proposal_path"]))

    assert review["proposal_path"] == written["proposal_path"]
    assert review["read_only"] is True
    assert review["would_mutate"] is False
    assert review["valid"] is True
    assert review["rule_id"] == "no-env-commit"
    assert review["active_rule_exists"] is True
    assert review["issues"] == []
    assert _audit_events(tmp_path) == before_events


def test_proposal_review_rejects_insufficient_data_proposal(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    written = write_promotion_plan(tmp_path, "no-env-commit", since_days=30)

    review = proposal_review(tmp_path, Path(written["proposal_path"]))

    assert review["valid"] is False
    assert "not_promotion_candidate" in [issue["code"] for issue in review["issues"]]


def test_proposal_review_detects_missing_required_approval_and_risk_flag(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])
    payload = json.loads(proposal_path.read_text(encoding="utf-8"))
    payload["required_human_approvals"] = ["maintainer_approval"]
    payload["risk_flags"] = []
    proposal_path.write_text(json.dumps(payload), encoding="utf-8")

    review = proposal_review(tmp_path, proposal_path)

    codes = [issue["code"] for issue in review["issues"]]
    assert review["valid"] is False
    assert "missing_required_approval" in codes
    assert "missing_risk_flag" in codes


def test_proposal_review_detects_missing_active_rule(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    active_rule = tmp_path / ".forgeflow" / "evolution" / "rules" / "no-env-commit-rule.json"
    active_rule.unlink()

    review = proposal_review(tmp_path, Path(written["proposal_path"]))

    assert review["valid"] is False
    assert review["active_rule_exists"] is False
    assert "active_rule_missing" in [issue["code"] for issue in review["issues"]]


def test_proposal_review_cli_outputs_json_contract(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "proposal-review", "--proposal", written["proposal_path"], "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["read_only"] is True
    assert payload["would_mutate"] is False


def test_proposal_review_cli_human_output_says_read_only(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "proposal-review", "--proposal", written["proposal_path"]],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Evolution proposal review:" in result.stdout
    assert "read-only: true" in result.stdout
    assert "would mutate: false" in result.stdout
    assert "valid: true" in result.stdout


def test_proposal_review_cli_returns_clean_error_for_malformed_json(tmp_path: Path) -> None:
    proposal = tmp_path / "broken.json"
    proposal.write_text("not-json", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "proposal-review", "--proposal", str(proposal)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Error:" in result.stderr
    assert "Traceback" not in result.stderr



def test_proposal_approve_appends_required_approval_without_rule_or_audit_mutation(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    before_events = _audit_events(tmp_path)
    active_rule = tmp_path / ".forgeflow" / "evolution" / "rules" / "no-env-commit-rule.json"
    before_rule = active_rule.read_text(encoding="utf-8")

    result = proposal_approve(
        tmp_path,
        Path(written["proposal_path"]),
        approval="maintainer_approval",
        approver="kim",
        reason="reviewed evidence",
    )

    assert result["rule_id"] == "no-env-commit"
    assert result["approval"] == "maintainer_approval"
    assert result["approver"] == "kim"
    assert result["would_promote"] is False
    assert result["would_mutate_rules"] is False
    assert result["review"]["valid"] is True
    approval_path = Path(result["approval_path"])
    records = [json.loads(line) for line in approval_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["approval"] == "maintainer_approval"
    assert records[0]["approver"] == "kim"
    assert records[0]["reason"] == "reviewed evidence"
    assert records[0]["proposal_path"] == written["proposal_path"]
    assert active_rule.read_text(encoding="utf-8") == before_rule
    assert _audit_events(tmp_path) == before_events


def test_proposal_approve_rejects_missing_reason_or_approver(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    for approver, reason in [("", "reviewed"), ("kim", "")]:
        try:
            proposal_approve(
                tmp_path,
                Path(written["proposal_path"]),
                approval="maintainer_approval",
                approver=approver,
                reason=reason,
            )
        except ValueError as exc:
            assert "approver and reason must be non-empty" in str(exc)
        else:  # pragma: no cover - failure path
            raise AssertionError("expected ValueError")


def test_proposal_approve_rejects_unknown_approval_type(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    try:
        proposal_approve(
            tmp_path,
            Path(written["proposal_path"]),
            approval="random_blessing",
            approver="kim",
            reason="nope",
        )
    except ValueError as exc:
        assert "approval is not required by proposal" in str(exc)
    else:  # pragma: no cover - failure path
        raise AssertionError("expected ValueError")


def test_proposal_approve_rejects_insufficient_data_proposal(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    written = write_promotion_plan(tmp_path, "no-env-commit", since_days=30)

    try:
        proposal_approve(
            tmp_path,
            Path(written["proposal_path"]),
            approval="maintainer_approval",
            approver="kim",
            reason="reviewed evidence",
        )
    except ValueError as exc:
        assert "proposal review failed" in str(exc)
    else:  # pragma: no cover - failure path
        raise AssertionError("expected ValueError")


def test_proposal_approve_returns_clean_error_for_malformed_proposal_cli(tmp_path: Path) -> None:
    proposal = tmp_path / "broken.json"
    proposal.write_text("not-json", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "proposal-approve",
            "--proposal",
            str(proposal),
            "--approval",
            "maintainer_approval",
            "--approver",
            "kim",
            "--reason",
            "reviewed evidence",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Error:" in result.stderr
    assert "Traceback" not in result.stderr


def test_proposal_approve_repeated_approval_appends_explicit_duplicate_records(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])

    first = proposal_approve(
        tmp_path,
        proposal_path,
        approval="maintainer_approval",
        approver="kim",
        reason="first review",
    )
    second = proposal_approve(
        tmp_path,
        proposal_path,
        approval="maintainer_approval",
        approver="kim",
        reason="second review",
    )

    records = [json.loads(line) for line in Path(first["approval_path"]).read_text(encoding="utf-8").splitlines()]
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert len(records) == 2
    assert [record["reason"] for record in records] == ["first review", "second review"]


def test_proposal_approve_cli_outputs_json_contract(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "proposal-approve",
            "--proposal",
            written["proposal_path"],
            "--approval",
            "project_owner_approval",
            "--approver",
            "kim",
            "--reason",
            "owner reviewed evidence",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["approval"] == "project_owner_approval"
    assert payload["would_promote"] is False
    assert payload["would_mutate_rules"] is False
    assert Path(payload["approval_path"]).is_file()


def test_proposal_approve_cli_human_output_says_no_promotion(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "proposal-approve",
            "--proposal",
            written["proposal_path"],
            "--approval",
            "maintainer_approval",
            "--approver",
            "kim",
            "--reason",
            "reviewed evidence",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Evolution proposal approval recorded:" in result.stdout
    assert "would promote: false" in result.stdout
    assert "would mutate rules: false" in result.stdout



def test_proposal_approvals_reports_missing_and_recorded_approvals(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])
    proposal_approve(
        tmp_path,
        proposal_path,
        approval="maintainer_approval",
        approver="kim",
        reason="maintainer reviewed evidence",
    )

    result = proposal_approvals(tmp_path, proposal_path)

    assert result["proposal_path"] == written["proposal_path"]
    assert result["rule_id"] == "no-env-commit"
    assert result["read_only"] is True
    assert result["would_promote"] is False
    assert result["would_mutate_rules"] is False
    assert result["required_approvals"] == ["maintainer_approval", "project_owner_approval"]
    assert result["recorded_approvals"] == ["maintainer_approval"]
    assert result["missing_approvals"] == ["project_owner_approval"]
    assert result["ready_for_policy_gate"] is False
    assert len(result["records"]) == 1


def test_proposal_approvals_ready_when_all_required_approvals_recorded(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])
    proposal_approve(tmp_path, proposal_path, approval="maintainer_approval", approver="kim", reason="maintainer reviewed")
    proposal_approve(tmp_path, proposal_path, approval="project_owner_approval", approver="kim", reason="owner reviewed")

    result = proposal_approvals(tmp_path, proposal_path)

    assert result["recorded_approvals"] == ["maintainer_approval", "project_owner_approval"]
    assert result["missing_approvals"] == []
    assert result["ready_for_policy_gate"] is True
    assert result["would_promote"] is False


def test_proposal_approvals_includes_duplicate_records_but_counts_unique_approvals(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])
    proposal_approve(tmp_path, proposal_path, approval="maintainer_approval", approver="kim", reason="first")
    proposal_approve(tmp_path, proposal_path, approval="maintainer_approval", approver="kim", reason="second")

    result = proposal_approvals(tmp_path, proposal_path)

    assert len(result["records"]) == 2
    assert result["duplicates"] == ["maintainer_approval"]
    assert result["recorded_approvals"] == ["maintainer_approval"]
    assert result["missing_approvals"] == ["project_owner_approval"]


def test_proposal_approvals_rejects_invalid_proposal(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    written = write_promotion_plan(tmp_path, "no-env-commit", since_days=30)

    try:
        proposal_approvals(tmp_path, Path(written["proposal_path"]))
    except ValueError as exc:
        assert "proposal review failed" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_proposal_approvals_cli_outputs_json_contract(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])
    proposal_approve(tmp_path, proposal_path, approval="maintainer_approval", approver="kim", reason="maintainer reviewed")

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "proposal-approvals", "--proposal", written["proposal_path"], "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ready_for_policy_gate"] is False
    assert payload["would_promote"] is False
    assert payload["would_mutate_rules"] is False
    assert payload["missing_approvals"] == ["project_owner_approval"]


def test_proposal_approvals_cli_human_output_shows_missing_approvals(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "proposal-approvals", "--proposal", written["proposal_path"]],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Evolution proposal approvals:" in result.stdout
    assert "would promote: false" in result.stdout
    assert "ready for policy gate: false" in result.stdout
    assert "missing approvals:" in result.stdout
    assert "maintainer_approval" in result.stdout



def test_promotion_gate_ready_when_proposal_valid_and_all_approvals_present(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])
    proposal_approve(tmp_path, proposal_path, approval="maintainer_approval", approver="kim", reason="maintainer reviewed")
    proposal_approve(tmp_path, proposal_path, approval="project_owner_approval", approver="kim", reason="owner reviewed")

    result = promotion_gate(tmp_path, proposal_path)

    assert result["proposal_valid"] is True
    assert result["all_required_approvals_present"] is True
    assert result["approval_records_complete"] is True
    assert result["risk_flags_acknowledged"] is True
    assert result["ready_for_policy_gate"] is True
    assert result["would_promote"] is False
    assert result["would_mutate_rules"] is False
    assert result["issues"] == []


def test_promotion_gate_reports_missing_approvals_without_promoting(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])
    proposal_approve(tmp_path, proposal_path, approval="maintainer_approval", approver="kim", reason="maintainer reviewed")

    result = promotion_gate(tmp_path, proposal_path)

    assert result["ready_for_policy_gate"] is False
    assert result["all_required_approvals_present"] is False
    assert result["missing_approvals"] == ["project_owner_approval"]
    assert "missing_required_approvals" in [issue["code"] for issue in result["issues"]]
    assert result["would_promote"] is False


def test_promotion_gate_detects_incomplete_approval_records(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])
    proposal_approve(tmp_path, proposal_path, approval="maintainer_approval", approver="kim", reason="maintainer reviewed")
    proposal_approve(tmp_path, proposal_path, approval="project_owner_approval", approver="kim", reason="owner reviewed")
    status = proposal_approvals(tmp_path, proposal_path)
    records = [json.loads(line) for line in Path(status["approval_path"]).read_text(encoding="utf-8").splitlines()]
    records[1]["reason"] = ""
    Path(status["approval_path"]).write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    result = promotion_gate(tmp_path, proposal_path)

    assert result["approval_records_complete"] is False
    assert result["ready_for_policy_gate"] is False
    assert "incomplete_approval_record" in [issue["code"] for issue in result["issues"]]


def test_promotion_gate_rejects_invalid_proposal(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    written = write_promotion_plan(tmp_path, "no-env-commit", since_days=30)

    result = promotion_gate(tmp_path, Path(written["proposal_path"]))

    assert result["proposal_valid"] is False
    assert result["ready_for_policy_gate"] is False
    assert "proposal_review_failed" in [issue["code"] for issue in result["issues"]]
    assert result["would_promote"] is False


def test_promotion_gate_cli_outputs_json_contract(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])
    proposal_approve(tmp_path, proposal_path, approval="maintainer_approval", approver="kim", reason="maintainer reviewed")
    proposal_approve(tmp_path, proposal_path, approval="project_owner_approval", approver="kim", reason="owner reviewed")

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "promotion-gate", "--proposal", written["proposal_path"], "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ready_for_policy_gate"] is True
    assert payload["would_promote"] is False
    assert payload["would_mutate_rules"] is False


def test_promotion_gate_cli_human_output_says_read_only_and_no_promotion(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "promotion-gate", "--proposal", written["proposal_path"]],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Evolution promotion gate:" in result.stdout
    assert "read-only: true" in result.stdout
    assert "would promote: false" in result.stdout
    assert "ready for policy gate: false" in result.stdout



def _gate_passing_proposal(tmp_path: Path) -> dict:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])
    proposal_approve(tmp_path, proposal_path, approval="maintainer_approval", approver="kim", reason="maintainer reviewed")
    proposal_approve(tmp_path, proposal_path, approval="project_owner_approval", approver="kim", reason="owner reviewed")
    return written


def test_promotion_decision_writes_append_only_decision_without_promotion(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)
    before_events = _audit_events(tmp_path)

    result = promotion_decision(
        tmp_path,
        Path(written["proposal_path"]),
        decision="approve_policy_gate",
        decider="kim",
        reason="promotion gate reviewed",
        write=True,
    )

    assert result["decision"] == "approve_policy_gate"
    assert result["decider"] == "kim"
    assert result["would_promote"] is False
    assert result["would_mutate_rules"] is False
    assert result["written"] is True
    decision_path = Path(result["decision_path"])
    records = [json.loads(line) for line in decision_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["decision"] == "approve_policy_gate"
    assert records[0]["reason"] == "promotion gate reviewed"
    assert _audit_events(tmp_path) == before_events


def test_promotion_decision_rejects_gate_failing_proposal(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    try:
        promotion_decision(
            tmp_path,
            Path(written["proposal_path"]),
            decision="approve_policy_gate",
            decider="kim",
            reason="not enough approvals",
            write=True,
        )
    except ValueError as exc:
        assert "promotion gate is not ready" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_promotion_decision_rejects_missing_decider_or_reason(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)
    for decider, reason in [("", "reviewed"), ("kim", "")]:
        try:
            promotion_decision(
                tmp_path,
                Path(written["proposal_path"]),
                decision="approve_policy_gate",
                decider=decider,
                reason=reason,
                write=True,
            )
        except ValueError as exc:
            assert "decider and reason must be non-empty" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("expected ValueError")


def test_promotion_decision_rejects_unknown_decision(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)
    try:
        promotion_decision(
            tmp_path,
            Path(written["proposal_path"]),
            decision="just_ship_it",
            decider="kim",
            reason="bad idea",
            write=True,
        )
    except ValueError as exc:
        assert "unsupported promotion decision" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_promotion_decision_requires_write_flag_for_recording(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)

    result = promotion_decision(
        tmp_path,
        Path(written["proposal_path"]),
        decision="approve_policy_gate",
        decider="kim",
        reason="dry check",
        write=False,
    )

    assert result["written"] is False
    assert Path(result["decision_path"]).exists() is False
    assert result["would_promote"] is False


def test_promotion_decision_cli_outputs_json_contract(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "promotion-decision",
            "--proposal",
            written["proposal_path"],
            "--decision",
            "approve_policy_gate",
            "--decider",
            "kim",
            "--reason",
            "promotion gate reviewed",
            "--write",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["written"] is True
    assert payload["would_promote"] is False
    assert payload["would_mutate_rules"] is False
    assert Path(payload["decision_path"]).is_file()


def test_promotion_decision_cli_human_output_says_no_promotion_no_mutation(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "promotion-decision",
            "--proposal",
            written["proposal_path"],
            "--decision",
            "approve_policy_gate",
            "--decider",
            "kim",
            "--reason",
            "promotion gate reviewed",
            "--write",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Evolution promotion decision recorded:" in result.stdout
    assert "would promote: false" in result.stdout
    assert "would mutate rules: false" in result.stdout



def _promotion_decided_proposal(tmp_path: Path) -> dict:
    written = _gate_passing_proposal(tmp_path)
    promotion_decision(
        tmp_path,
        Path(written["proposal_path"]),
        decision="approve_policy_gate",
        decider="kim",
        reason="promotion gate reviewed",
        write=True,
    )
    return written


def test_promotion_ready_true_when_gate_and_decision_records_are_complete(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)

    result = promotion_ready(tmp_path, Path(written["proposal_path"]))

    assert result["ready_for_promote"] is True
    assert result["promotion_gate_ready"] is True
    assert result["approve_policy_gate_decision_present"] is True
    assert result["decision_records_complete"] is True
    assert result["active_rule_exists"] is True
    assert result["would_promote"] is False
    assert result["would_mutate_rules"] is False
    assert result["issues"] == []


def test_promotion_ready_reports_missing_decision_record(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)

    result = promotion_ready(tmp_path, Path(written["proposal_path"]))

    assert result["ready_for_promote"] is False
    assert result["approve_policy_gate_decision_present"] is False
    assert "missing_approve_policy_gate_decision" in [issue["code"] for issue in result["issues"]]


def test_promotion_ready_detects_incomplete_decision_record(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)
    ready = promotion_ready(tmp_path, Path(written["proposal_path"]))
    records = [json.loads(line) for line in Path(ready["decision_path"]).read_text(encoding="utf-8").splitlines()]
    records[0]["decider"] = ""
    Path(ready["decision_path"]).write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    result = promotion_ready(tmp_path, Path(written["proposal_path"]))

    assert result["ready_for_promote"] is False
    assert result["decision_records_complete"] is False
    assert "incomplete_promotion_decision_record" in [issue["code"] for issue in result["issues"]]


def test_promotion_ready_detects_stale_missing_active_rule(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)
    active_rule = tmp_path / ".forgeflow" / "evolution" / "rules" / "no-env-commit-rule.json"
    active_rule.unlink()

    result = promotion_ready(tmp_path, Path(written["proposal_path"]))

    assert result["ready_for_promote"] is False
    assert result["active_rule_exists"] is False
    assert "active_rule_missing" in [issue["code"] for issue in result["issues"]]


def test_promotion_ready_reports_gate_failure_for_invalid_proposal(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    result = promotion_ready(tmp_path, Path(written["proposal_path"]))

    assert result["ready_for_promote"] is False
    assert result["promotion_gate_ready"] is False
    assert "promotion_gate_not_ready" in [issue["code"] for issue in result["issues"]]


def test_promotion_ready_cli_outputs_json_contract(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "promotion-ready", "--proposal", written["proposal_path"], "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ready_for_promote"] is True
    assert payload["would_promote"] is False
    assert payload["would_mutate_rules"] is False


def test_promotion_ready_cli_human_output_says_no_promotion_and_readiness(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "promotion-ready", "--proposal", written["proposal_path"]],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Evolution promotion ready:" in result.stdout
    assert "ready for promote: false" in result.stdout
    assert "would promote: false" in result.stdout
    assert "would mutate rules: false" in result.stdout



def test_promote_rule_requires_ready_proposal_and_writes_promotion_marker(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)
    active_rule = tmp_path / ".forgeflow" / "evolution" / "rules" / "no-env-commit-rule.json"
    before_rule = active_rule.read_text(encoding="utf-8")
    before_events = _audit_events(tmp_path)

    result = promote_rule(tmp_path, Path(written["proposal_path"]))

    assert result["mutation_mode"] == "promotion_marker"
    assert result["would_mutate_rules"] is True
    assert result["promoted"] is True
    assert result["ready"]["ready_for_promote"] is True
    assert active_rule.read_text(encoding="utf-8") == before_rule
    promotion_path = Path(result["promotion_path"])
    assert promotion_path.is_file()
    marker = json.loads(promotion_path.read_text(encoding="utf-8"))
    assert marker["rule_id"] == "no-env-commit"
    assert marker["promotion_status"] == "promoted"
    assert marker["active_rule_snapshot"]["id"] == "no-env-commit"
    events = _audit_events(tmp_path)
    assert len(events) == len(before_events) + 1
    assert events[-1]["event"] == "promote"
    assert events[-1]["rule_id"] == "no-env-commit"
    assert events[-1]["mutation_mode"] == "promotion_marker"


def test_promote_rule_rejects_not_ready_proposal_and_audits_blocked(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)

    try:
        promote_rule(tmp_path, Path(written["proposal_path"]))
    except ValueError as exc:
        assert "promotion is not ready" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_promote_cli_requires_long_acknowledgement_flag(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "promote", "--proposal", written["proposal_path"], "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "--i-understand-this-mutates-project-policy" in result.stderr


def test_promote_cli_json_contract_is_stub_and_no_rule_mutation(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "promote",
            "--proposal",
            written["proposal_path"],
            "--i-understand-this-mutates-project-policy",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mutation_mode"] == "promotion_marker"
    assert payload["would_mutate_rules"] is True
    assert payload["promoted"] is True
    assert Path(payload["promotion_path"]).is_file()


def test_promote_cli_human_output_says_stub_and_no_mutation(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "promote",
            "--proposal",
            written["proposal_path"],
            "--i-understand-this-mutates-project-policy",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Evolution promote:" in result.stdout
    assert "mutation mode: promotion_marker" in result.stdout
    assert "would mutate rules: true" in result.stdout
    assert "promoted: true" in result.stdout



def test_promote_rule_appends_blocked_audit_for_not_ready_proposal(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)
    before_events = _audit_events(tmp_path)

    try:
        promote_rule(tmp_path, Path(written["proposal_path"]))
    except ValueError as exc:
        assert "promotion is not ready" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")

    events = _audit_events(tmp_path)
    assert len(events) == len(before_events) + 1
    blocked = events[-1]
    assert blocked["event"] == "promote_blocked"
    assert blocked["rule_id"] == "no-env-commit"
    assert blocked["mutation_mode"] == "promotion_marker"
    assert blocked["promoted"] is False
    assert "missing_approve_policy_gate_decision" in blocked["failed_readiness_checks"]
    assert blocked["proposal_path"] == written["proposal_path"]
    assert blocked["decision_path"].endswith(".jsonl")
    assert blocked["approval_path"].endswith(".jsonl")


def test_promote_cli_acknowledged_not_ready_appends_blocked_audit(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "promote",
            "--proposal",
            written["proposal_path"],
            "--i-understand-this-mutates-project-policy",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Error:" in result.stderr
    events = _audit_events(tmp_path)
    assert events[-1]["event"] == "promote_blocked"
    assert events[-1]["promoted"] is False



def test_promote_rule_refuses_duplicate_promotion_marker(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)
    first = promote_rule(tmp_path, Path(written["proposal_path"]))

    try:
        promote_rule(tmp_path, Path(written["proposal_path"]))
    except FileExistsError as exc:
        assert "promotion marker already exists" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected FileExistsError")

    marker = Path(first["promotion_path"])
    assert marker.is_file()
    events = _audit_events(tmp_path)
    assert events[-1]["event"] == "promote_blocked"
    assert "promotion_marker_already_exists" in events[-1]["failed_readiness_checks"]



def test_list_promotions_reports_written_markers(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)
    promoted = promote_rule(tmp_path, Path(written["proposal_path"]))

    result = list_promotions(tmp_path)

    assert result["promotion_dir"].endswith(".forgeflow/evolution/promoted-rules")
    assert result["count"] == 1
    marker = result["promotions"][0]
    assert marker["rule_id"] == "no-env-commit"
    assert marker["promotion_status"] == "promoted"
    assert marker["promotion_path"] == promoted["promotion_path"]
    assert marker["proposal_path"] == written["proposal_path"]
    assert marker["active_rule_path"].endswith("no-env-commit-rule.json")
    assert marker["mutation_mode"] == "promotion_marker"


def test_list_promotions_cli_json_and_human_output(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)
    promoted = promote_rule(tmp_path, Path(written["proposal_path"]))

    json_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "forgeflow_evolution.py"),
            "--root",
            str(tmp_path),
            "promotions",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert json_result.returncode == 0, json_result.stderr
    payload = json.loads(json_result.stdout)
    assert payload["count"] == 1
    assert payload["promotions"][0]["promotion_path"] == promoted["promotion_path"]

    human_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "forgeflow_evolution.py"),
            "--root",
            str(tmp_path),
            "promotions",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert human_result.returncode == 0, human_result.stderr
    assert "Evolution promotions:" in human_result.stdout
    assert "no-env-commit promoted" in human_result.stdout
    assert promoted["promotion_path"] in human_result.stdout



def test_generated_adapter_drift_command_uses_non_mutating_check() -> None:
    script = (ROOT / "scripts" / "generate_adapters.py").read_text(encoding="utf-8")
    runtime = (ROOT / "forgeflow_runtime" / "evolution.py").read_text(encoding="utf-8")

    assert "--check" in script
    assert "out_file.write_text" in script
    assert "if args.check" in script
    assert '[sys.executable, "scripts/generate_adapters.py", "--check"]' in runtime



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
