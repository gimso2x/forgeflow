from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.evolution import adopt_example_rule, audit_events, execute_rule


ROOT = Path(__file__).resolve().parents[2]


def test_audit_events_returns_recent_events_limited_newest_last(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    execute_rule(tmp_path, "no-env-commit")

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
