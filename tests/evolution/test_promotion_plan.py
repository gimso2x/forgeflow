from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.evolution import adopt_example_rule, promotion_plan, write_promotion_plan

ROOT = Path(__file__).resolve().parents[2]


def _audit_events(root: Path) -> list[dict]:
    audit_path = root / ".forgeflow" / "evolution" / "audit-log.jsonl"
    return [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]


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
