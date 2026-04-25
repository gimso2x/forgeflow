from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.evolution import (
    adopt_example_rule,
    proposal_approve,
    proposal_approvals,
    promotion_gate,
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
