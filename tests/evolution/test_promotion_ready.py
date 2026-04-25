from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.evolution import (
    adopt_example_rule,
    promotion_decision,
    promotion_ready,
    proposal_approve,
    write_promotion_plan,
)

ROOT = Path(__file__).resolve().parents[2]


def _audit_events(root: Path) -> list[dict]:
    audit_path = root / ".forgeflow" / "evolution" / "audit-log.jsonl"
    return [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]


def _append_failed_execute_events(root: Path, rule_id: str, count: int) -> None:
    audit_path = root / ".forgeflow" / "evolution" / "audit-log.jsonl"
    events = _audit_events(root)
    for _ in range(count):
        events.append(
            {
                "schema_version": 1,
                "timestamp": "2026-04-24T00:00:00Z",
                "event": "execute",
                "rule_id": rule_id,
                "executed": True,
                "passed": False,
                "exit_code": 1,
                "expected_exit_code": 0,
                "failed_safety_checks": [],
            }
        )
    audit_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")


def _written_candidate_proposal(tmp_path: Path) -> dict:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    _append_failed_execute_events(tmp_path, "no-env-commit", 2)
    return write_promotion_plan(tmp_path, "no-env-commit", since_days=30)


def _gate_passing_proposal(tmp_path: Path) -> dict:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])
    proposal_approve(tmp_path, proposal_path, approval="maintainer_approval", approver="kim", reason="maintainer reviewed")
    proposal_approve(tmp_path, proposal_path, approval="project_owner_approval", approver="kim", reason="owner reviewed")
    return written


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
