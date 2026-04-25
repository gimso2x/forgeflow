from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.evolution import adopt_example_rule, proposal_approve, write_promotion_plan

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


def test_proposal_approve_appends_required_approval_without_rule_or_audit_mutation(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    before_events = _audit_events(tmp_path)
    active_rule = tmp_path / ".forgeflow" / "evolution" / "rules" / "no-env-commit-rule.json"
    before_rule = active_rule.read_text(encoding="utf-8")

    result = proposal_approve(
        tmp_path,
        Path(written["proposal_path"]),
        approval="maintainer_approval",
        approver="kim",
        reason="reviewed evidence",
    )

    assert result["rule_id"] == "no-env-commit"
    assert result["approval"] == "maintainer_approval"
    assert result["approver"] == "kim"
    assert result["would_promote"] is False
    assert result["would_mutate_rules"] is False
    assert result["review"]["valid"] is True
    approval_path = Path(result["approval_path"])
    records = [json.loads(line) for line in approval_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["approval"] == "maintainer_approval"
    assert records[0]["approver"] == "kim"
    assert records[0]["reason"] == "reviewed evidence"
    assert records[0]["proposal_path"] == written["proposal_path"]
    assert active_rule.read_text(encoding="utf-8") == before_rule
    assert _audit_events(tmp_path) == before_events


def test_proposal_approve_rejects_missing_reason_or_approver(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    for approver, reason in [("", "reviewed"), ("kim", "")]:
        try:
            proposal_approve(
                tmp_path,
                Path(written["proposal_path"]),
                approval="maintainer_approval",
                approver=approver,
                reason=reason,
            )
        except ValueError as exc:
            assert "approver and reason must be non-empty" in str(exc)
        else:  # pragma: no cover - failure path
            raise AssertionError("expected ValueError")


def test_proposal_approve_rejects_unknown_approval_type(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    try:
        proposal_approve(
            tmp_path,
            Path(written["proposal_path"]),
            approval="random_blessing",
            approver="kim",
            reason="nope",
        )
    except ValueError as exc:
        assert "approval is not required by proposal" in str(exc)
    else:  # pragma: no cover - failure path
        raise AssertionError("expected ValueError")


def test_proposal_approve_rejects_insufficient_data_proposal(tmp_path: Path) -> None:
    adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)
    written = write_promotion_plan(tmp_path, "no-env-commit", since_days=30)

    try:
        proposal_approve(
            tmp_path,
            Path(written["proposal_path"]),
            approval="maintainer_approval",
            approver="kim",
            reason="reviewed evidence",
        )
    except ValueError as exc:
        assert "proposal review failed" in str(exc)
    else:  # pragma: no cover - failure path
        raise AssertionError("expected ValueError")


def test_proposal_approve_returns_clean_error_for_malformed_proposal_cli(tmp_path: Path) -> None:
    proposal = tmp_path / "broken.json"
    proposal.write_text("not-json", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "proposal-approve",
            "--proposal",
            str(proposal),
            "--approval",
            "maintainer_approval",
            "--approver",
            "kim",
            "--reason",
            "reviewed evidence",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Error:" in result.stderr
    assert "Traceback" not in result.stderr


def test_proposal_approve_repeated_approval_appends_explicit_duplicate_records(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])

    first = proposal_approve(
        tmp_path,
        proposal_path,
        approval="maintainer_approval",
        approver="kim",
        reason="first review",
    )
    second = proposal_approve(
        tmp_path,
        proposal_path,
        approval="maintainer_approval",
        approver="kim",
        reason="second review",
    )

    records = [json.loads(line) for line in Path(first["approval_path"]).read_text(encoding="utf-8").splitlines()]
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert len(records) == 2
    assert [record["reason"] for record in records] == ["first review", "second review"]


def test_proposal_approve_cli_outputs_json_contract(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "proposal-approve",
            "--proposal",
            written["proposal_path"],
            "--approval",
            "project_owner_approval",
            "--approver",
            "kim",
            "--reason",
            "owner reviewed evidence",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["approval"] == "project_owner_approval"
    assert payload["would_promote"] is False
    assert payload["would_mutate_rules"] is False
    assert Path(payload["approval_path"]).is_file()


def test_proposal_approve_cli_human_output_says_no_promotion(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "proposal-approve",
            "--proposal",
            written["proposal_path"],
            "--approval",
            "maintainer_approval",
            "--approver",
            "kim",
            "--reason",
            "reviewed evidence",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Evolution proposal approval recorded:" in result.stdout
    assert "would promote: false" in result.stdout
    assert "would mutate rules: false" in result.stdout
