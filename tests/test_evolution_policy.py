from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.evolution import dry_run_rule, execute_rule, inspect_evolution_policy


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


def test_execute_rule_runs_safe_project_rule_when_explicitly_allowed() -> None:
    result = execute_rule(ROOT, "no-env-commit")

    assert result["rule_id"] == "no-env-commit"
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


def test_forgeflow_evolution_execute_cli_outputs_json_after_gated_run() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
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
