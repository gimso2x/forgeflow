from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.evolution import adopt_example_rule, promotion_decision, proposal_approve, write_promotion_plan


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


def _gate_passing_proposal(tmp_path: Path) -> dict:
    written = _written_candidate_proposal(tmp_path)
    proposal_path = Path(written["proposal_path"])
    proposal_approve(tmp_path, proposal_path, approval="maintainer_approval", approver="kim", reason="maintainer reviewed")
    proposal_approve(tmp_path, proposal_path, approval="project_owner_approval", approver="kim", reason="owner reviewed")
    return written


def test_promotion_decision_writes_append_only_decision_without_promotion(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)
    before_events = _audit_events(tmp_path)

    result = promotion_decision(
        tmp_path,
        Path(written["proposal_path"]),
        decision="approve_policy_gate",
        decider="kim",
        reason="promotion gate reviewed",
        write=True,
    )

    assert result["decision"] == "approve_policy_gate"
    assert result["decider"] == "kim"
    assert result["would_promote"] is False
    assert result["would_mutate_rules"] is False
    assert result["written"] is True
    decision_path = Path(result["decision_path"])
    records = [json.loads(line) for line in decision_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["decision"] == "approve_policy_gate"
    assert records[0]["reason"] == "promotion gate reviewed"
    assert _audit_events(tmp_path) == before_events


def test_promotion_decision_rejects_gate_failing_proposal(tmp_path: Path) -> None:
    written = _written_candidate_proposal(tmp_path)

    try:
        promotion_decision(
            tmp_path,
            Path(written["proposal_path"]),
            decision="approve_policy_gate",
            decider="kim",
            reason="not enough approvals",
            write=True,
        )
    except ValueError as exc:
        assert "promotion gate is not ready" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_promotion_decision_rejects_missing_decider_or_reason(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)
    for decider, reason in [("", "reviewed"), ("kim", "")]:
        try:
            promotion_decision(
                tmp_path,
                Path(written["proposal_path"]),
                decision="approve_policy_gate",
                decider=decider,
                reason=reason,
                write=True,
            )
        except ValueError as exc:
            assert "decider and reason must be non-empty" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("expected ValueError")


def test_promotion_decision_rejects_unknown_decision(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)
    try:
        promotion_decision(
            tmp_path,
            Path(written["proposal_path"]),
            decision="just_ship_it",
            decider="kim",
            reason="bad idea",
            write=True,
        )
    except ValueError as exc:
        assert "unsupported promotion decision" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_promotion_decision_requires_write_flag_for_recording(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)

    result = promotion_decision(
        tmp_path,
        Path(written["proposal_path"]),
        decision="approve_policy_gate",
        decider="kim",
        reason="dry check",
        write=False,
    )

    assert result["written"] is False
    assert Path(result["decision_path"]).exists() is False
    assert result["would_promote"] is False


def test_promotion_decision_cli_outputs_json_contract(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "promotion-decision",
            "--proposal",
            written["proposal_path"],
            "--decision",
            "approve_policy_gate",
            "--decider",
            "kim",
            "--reason",
            "promotion gate reviewed",
            "--write",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["written"] is True
    assert payload["would_promote"] is False
    assert payload["would_mutate_rules"] is False
    assert Path(payload["decision_path"]).is_file()


def test_promotion_decision_cli_human_output_says_no_promotion_no_mutation(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "promotion-decision",
            "--proposal",
            written["proposal_path"],
            "--decision",
            "approve_policy_gate",
            "--decider",
            "kim",
            "--reason",
            "promotion gate reviewed",
            "--write",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Evolution promotion decision recorded:" in result.stdout
    assert "would promote: false" in result.stdout
    assert "would mutate rules: false" in result.stdout
