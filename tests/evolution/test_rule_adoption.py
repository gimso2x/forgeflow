from __future__ import annotations

import json

from pathlib import Path

from forgeflow_runtime.evolution import adopt_example_rule


ROOT = Path(__file__).resolve().parents[2]


def _valid_rule() -> dict:
    return json.loads((ROOT / "examples" / "evolution" / "no-env-commit-rule.json").read_text(encoding="utf-8"))


def _audit_events(root: Path) -> list[dict]:
    audit_path = root / ".forgeflow" / "evolution" / "audit-log.jsonl"
    return [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]


def test_adopt_example_ignores_project_rules_in_fallback_root(tmp_path: Path) -> None:
    fallback = tmp_path / "fallback"
    target = tmp_path / "target"
    fallback_project_rule_dir = fallback / ".forgeflow" / "evolution" / "rules"
    fallback_project_rule_dir.mkdir(parents=True)
    rule = _valid_rule()
    (fallback_project_rule_dir / "no-env-commit-rule.json").write_text(json.dumps(rule), encoding="utf-8")
    example_dir = fallback / "examples" / "evolution"
    example_dir.mkdir(parents=True)
    (example_dir / "no-env-commit-rule.json").write_text((ROOT / "examples" / "evolution" / "no-env-commit-rule.json").read_text(encoding="utf-8"), encoding="utf-8")
    (example_dir / "generated-adapter-drift-rule.json").write_text((ROOT / "examples" / "evolution" / "generated-adapter-drift-rule.json").read_text(encoding="utf-8"), encoding="utf-8")

    result = adopt_example_rule(target, "no-env-commit", fallback_root=fallback)

    assert result["adopted"] is True
    assert "/examples/evolution/" in result["source"]


def test_adopt_example_rule_records_project_local_audit_event(tmp_path: Path) -> None:
    result = adopt_example_rule(tmp_path, "no-env-commit", fallback_root=ROOT)

    events = _audit_events(tmp_path)
    assert len(events) == 1
    event = events[0]
    assert event["event"] == "adopt"
    assert event["rule_id"] == "no-env-commit"
    assert event["source"] == result["source"]
    assert event["destination"] == result["destination"]
    assert event["passed"] is True
    assert event["timestamp"].endswith("Z")
    assert event["schema_version"] == 1
