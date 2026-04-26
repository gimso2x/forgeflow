import json
from collections.abc import Callable
from pathlib import Path

from forgeflow_runtime.orchestrator import escalate_route


def test_escalate_route_switches_to_large_high_risk(
    tmp_path: Path,
    make_task_dir: Callable[[Path], Path],
    assert_schema_valid: Callable[[str, dict], None],
) -> None:
    task_dir = make_task_dir(tmp_path)

    state = escalate_route(task_dir=task_dir, from_route="small")

    assert state["status"] == "blocked"
    assert state["current_stage"] == "clarify"
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    assert_schema_valid("checkpoint", checkpoint)
    assert checkpoint["route"] == "large_high_risk"
    assert checkpoint["current_stage"] == "clarify"
    assert checkpoint["next_action"] == "Resume at plan after reloading canonical artifacts."

    decision_log = json.loads((task_dir / "decision-log.json").read_text(encoding="utf-8"))
    assert decision_log["entries"][-1]["decision"] == "route escalated: small -> large_high_risk"
