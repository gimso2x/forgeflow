from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.evolution import inspect_evolution_policy


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
