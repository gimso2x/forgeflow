from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.evolution import adopt_example_rule, proposal_approve, proposal_approvals, write_promotion_plan

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


def _written_candidate_proposal(tmp_path: Path) -> dict:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    _append_failed_execute_events(tmp_path, "no-env-commit", 2)
    return write_promotion_plan(tmp_path, "no-env-commit", since_days=30)


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
