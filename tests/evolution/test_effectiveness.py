from __future__ import annotations

import json
import subprocess
import sys

from pathlib import Path

from forgeflow_runtime.evolution import adopt_example_rule, effectiveness_review, execute_rule

ROOT = Path(__file__).resolve().parents[2]


def _audit_events(root: Path) -> list[dict]:
    audit_path = root / ".forgeflow" / "evolution" / "audit-log.jsonl"
    return [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]


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
