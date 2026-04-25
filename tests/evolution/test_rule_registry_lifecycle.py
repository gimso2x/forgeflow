from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.evolution import adopt_example_rule, dry_run_rule, execute_rule, list_rules

ROOT = Path(__file__).resolve().parents[2]


def _audit_events(root: Path) -> list[dict]:
    audit_path = root / ".forgeflow" / "evolution" / "audit-log.jsonl"
    return [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]


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
