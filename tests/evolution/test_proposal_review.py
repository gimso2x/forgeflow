from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.evolution import adopt_example_rule, proposal_review, write_promotion_plan

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
