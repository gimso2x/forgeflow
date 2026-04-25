from __future__ import annotations

import json
import subprocess
import sys

from pathlib import Path

from forgeflow_runtime.evolution import (
    adopt_example_rule,
    list_promotions,
    promote_rule,
    promotion_decision,
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


def test_promote_rule_requires_ready_proposal_and_writes_promotion_marker(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)
    active_rule = tmp_path / ".forgeflow" / "evolution" / "rules" / "no-env-commit-rule.json"
    before_rule = active_rule.read_text(encoding="utf-8")
    before_events = _audit_events(tmp_path)

    result = promote_rule(tmp_path, Path(written["proposal_path"]))

    assert result["mutation_mode"] == "promotion_marker"
    assert result["would_mutate_rules"] is True
    assert result["promoted"] is True
    assert result["ready"]["ready_for_promote"] is True
    assert active_rule.read_text(encoding="utf-8") == before_rule
    promotion_path = Path(result["promotion_path"])
    assert promotion_path.is_file()
    marker = json.loads(promotion_path.read_text(encoding="utf-8"))
    assert marker["rule_id"] == "no-env-commit"
    assert marker["promotion_status"] == "promoted"
    assert marker["active_rule_snapshot"]["id"] == "no-env-commit"
    events = _audit_events(tmp_path)
    assert len(events) == len(before_events) + 1
    assert events[-1]["event"] == "promote"
    assert events[-1]["rule_id"] == "no-env-commit"
    assert events[-1]["mutation_mode"] == "promotion_marker"


def test_promote_rule_rejects_not_ready_proposal_and_audits_blocked(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)

    try:
        promote_rule(tmp_path, Path(written["proposal_path"]))
    except ValueError as exc:
        assert "promotion is not ready" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_promote_cli_requires_long_acknowledgement_flag(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)

    result = subprocess.run(
        [sys.executable, "scripts/forgeflow_evolution.py", "--root", str(tmp_path), "promote", "--proposal", written["proposal_path"], "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "--i-understand-this-mutates-project-policy" in result.stderr


def test_promote_cli_json_contract_is_stub_and_no_rule_mutation(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "promote",
            "--proposal",
            written["proposal_path"],
            "--i-understand-this-mutates-project-policy",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mutation_mode"] == "promotion_marker"
    assert payload["would_mutate_rules"] is True
    assert payload["promoted"] is True
    assert Path(payload["promotion_path"]).is_file()


def test_promote_cli_human_output_says_stub_and_no_mutation(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "promote",
            "--proposal",
            written["proposal_path"],
            "--i-understand-this-mutates-project-policy",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Evolution promote:" in result.stdout
    assert "mutation mode: promotion_marker" in result.stdout
    assert "would mutate rules: true" in result.stdout
    assert "promoted: true" in result.stdout



def test_promote_rule_appends_blocked_audit_for_not_ready_proposal(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)
    before_events = _audit_events(tmp_path)

    try:
        promote_rule(tmp_path, Path(written["proposal_path"]))
    except ValueError as exc:
        assert "promotion is not ready" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")

    events = _audit_events(tmp_path)
    assert len(events) == len(before_events) + 1
    blocked = events[-1]
    assert blocked["event"] == "promote_blocked"
    assert blocked["rule_id"] == "no-env-commit"
    assert blocked["mutation_mode"] == "promotion_marker"
    assert blocked["promoted"] is False
    assert "missing_approve_policy_gate_decision" in blocked["failed_readiness_checks"]
    assert blocked["proposal_path"] == written["proposal_path"]
    assert blocked["decision_path"].endswith(".jsonl")
    assert blocked["approval_path"].endswith(".jsonl")


def test_promote_cli_acknowledged_not_ready_appends_blocked_audit(tmp_path: Path) -> None:
    written = _gate_passing_proposal(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/forgeflow_evolution.py",
            "--root",
            str(tmp_path),
            "promote",
            "--proposal",
            written["proposal_path"],
            "--i-understand-this-mutates-project-policy",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Error:" in result.stderr
    events = _audit_events(tmp_path)
    assert events[-1]["event"] == "promote_blocked"
    assert events[-1]["promoted"] is False



def test_promote_rule_refuses_duplicate_promotion_marker(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)
    first = promote_rule(tmp_path, Path(written["proposal_path"]))

    try:
        promote_rule(tmp_path, Path(written["proposal_path"]))
    except FileExistsError as exc:
        assert "promotion marker already exists" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected FileExistsError")

    marker = Path(first["promotion_path"])
    assert marker.is_file()
    events = _audit_events(tmp_path)
    assert events[-1]["event"] == "promote_blocked"
    assert "promotion_marker_already_exists" in events[-1]["failed_readiness_checks"]



def test_list_promotions_reports_written_markers(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)
    promoted = promote_rule(tmp_path, Path(written["proposal_path"]))

    result = list_promotions(tmp_path)

    assert result["promotion_dir"].endswith(".forgeflow/evolution/promoted-rules")
    assert result["count"] == 1
    marker = result["promotions"][0]
    assert marker["rule_id"] == "no-env-commit"
    assert marker["promotion_status"] == "promoted"
    assert marker["promotion_path"] == promoted["promotion_path"]
    assert marker["proposal_path"] == written["proposal_path"]
    assert marker["active_rule_path"].endswith("no-env-commit-rule.json")
    assert marker["mutation_mode"] == "promotion_marker"


def test_list_promotions_cli_json_and_human_output(tmp_path: Path) -> None:
    written = _promotion_decided_proposal(tmp_path)
    promoted = promote_rule(tmp_path, Path(written["proposal_path"]))

    json_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "forgeflow_evolution.py"),
            "--root",
            str(tmp_path),
            "promotions",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert json_result.returncode == 0, json_result.stderr
    payload = json.loads(json_result.stdout)
    assert payload["count"] == 1
    assert payload["promotions"][0]["promotion_path"] == promoted["promotion_path"]

    human_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "forgeflow_evolution.py"),
            "--root",
            str(tmp_path),
            "promotions",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert human_result.returncode == 0, human_result.stderr
    assert "Evolution promotions:" in human_result.stdout
    assert "no-env-commit promoted" in human_result.stdout
    assert promoted["promotion_path"] in human_result.stdout
