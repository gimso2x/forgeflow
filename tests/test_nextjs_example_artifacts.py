from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "examples" / "end-to-end-nextjs-flow"


def test_nextjs_example_artifacts_exist() -> None:
    assert EXAMPLE_DIR.is_dir()
    for filename in [
        "README.md",
        "brief.json",
        "plan.json",
        "plan-ledger.json",
        "run-state.json",
        "decision-log.json",
        "review-report.json",
    ]:
        assert (EXAMPLE_DIR / filename).is_file()


def test_nextjs_example_brief_is_valid() -> None:
    schema = json.loads((ROOT / "schemas" / "brief.schema.json").read_text(encoding="utf-8"))
    artifact = json.loads((EXAMPLE_DIR / "brief.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(artifact)
    assert artifact["task_id"] == "dashboard-empty-state"
    assert artifact["route"] == "medium"


def test_nextjs_example_plan_is_valid() -> None:
    schema = json.loads((ROOT / "schemas" / "plan.schema.json").read_text(encoding="utf-8"))
    artifact = json.loads((EXAMPLE_DIR / "plan.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(artifact)
    assert len(artifact["steps"]) == 4


def test_nextjs_example_plan_ledger_is_valid() -> None:
    schema = json.loads((ROOT / "schemas" / "plan-ledger.schema.json").read_text(encoding="utf-8"))
    artifact = json.loads((EXAMPLE_DIR / "plan-ledger.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(artifact)
    assert artifact["task_id"] == "dashboard-empty-state"
    assert artifact["last_review_verdict"] == "approved"
    assert {task["status"] for task in artifact["tasks"]} == {"done"}


def test_nextjs_example_run_state_is_valid() -> None:
    schema = json.loads((ROOT / "schemas" / "run-state.schema.json").read_text(encoding="utf-8"))
    artifact = json.loads((EXAMPLE_DIR / "run-state.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(artifact)
    assert artifact["status"] == "completed"
    assert artifact["progress"]["percent"] == 100.0


def test_nextjs_example_decision_log_is_valid() -> None:
    schema = json.loads((ROOT / "schemas" / "decision-log.schema.json").read_text(encoding="utf-8"))
    artifact = json.loads((EXAMPLE_DIR / "decision-log.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(artifact)
    assert len(artifact["entries"]) == 3


def test_nextjs_example_review_report_is_valid() -> None:
    schema = json.loads((ROOT / "schemas" / "review-report.schema.json").read_text(encoding="utf-8"))
    artifact = json.loads((EXAMPLE_DIR / "review-report.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(artifact)
    assert artifact["verdict"] == "approved"
    assert artifact["safe_for_next_stage"] is True
