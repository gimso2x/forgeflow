import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "forgeflow_monitor.py"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def make_fixture(root: Path) -> Path:
    tasks = root / ".forgeflow" / "tasks"

    write_json(
        tasks / "done-task" / "run-state.json",
        {"task_id": "done-task", "route": "small", "current_stage": "finalize", "status": "completed"},
    )
    write_json(
        tasks / "done-task" / "review-report.json",
        {"task_id": "done-task", "approved": True, "findings": []},
    )

    write_json(
        tasks / "blocked-task" / "run-state.json",
        {
            "task_id": "blocked-task",
            "route": "medium",
            "current_stage": "execute",
            "status": "blocked",
            "blocked_reason": "missing API key",
        },
    )

    write_json(
        tasks / "rejected-task" / "run-state.json",
        {"task_id": "rejected-task", "route": "medium", "current_stage": "quality-review", "status": "in_progress"},
    )
    write_json(
        tasks / "rejected-task" / "review-report.json",
        {
            "task_id": "rejected-task",
            "approved": False,
            "findings": [
                {"severity": "high", "message": "missing verification evidence"},
            ],
        },
    )

    return tasks


def run_monitor(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_monitor_json_summarizes_task_health(tmp_path):
    tasks = make_fixture(tmp_path)

    result = run_monitor("--tasks", str(tasks), "--format", "json", "--recent", "10")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"]["total_tasks"] == 3
    assert payload["summary"]["completed"] == 1
    assert payload["summary"]["blocked"] == 1
    assert payload["summary"]["review_rejected"] == 1
    assert payload["summary"]["artifact_errors"] == 0
    patterns = payload["top_failure_patterns"]
    assert any(item["message"] == "missing API key" for item in patterns)
    assert any(item["message"] == "missing verification evidence" for item in patterns)


def test_monitor_markdown_renders_summary_and_task_rows(tmp_path):
    tasks = make_fixture(tmp_path)

    result = run_monitor("--tasks", str(tasks), "--format", "md", "--recent", "10")

    assert result.returncode == 0, result.stderr
    assert "# ForgeFlow monitor summary" in result.stdout
    assert "Total tasks: 3" in result.stdout
    assert "Review rejected: 1" in result.stdout
    assert "| done-task | small | finalize | completed | approved |" in result.stdout
    assert "| rejected-task | medium | quality-review | in_progress | rejected |" in result.stdout


def test_monitor_tolerates_missing_and_malformed_artifacts(tmp_path):
    tasks = tmp_path / ".forgeflow" / "tasks"
    (tasks / "empty-task").mkdir(parents=True)
    bad = tasks / "bad-task" / "run-state.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{not json", encoding="utf-8")

    result = run_monitor("--tasks", str(tasks), "--format", "json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"]["total_tasks"] == 2
    assert payload["summary"]["unknown"] == 2
    assert payload["summary"]["artifact_errors"] == 1


def test_monitor_summarizes_partial_review_artifacts_without_run_state(tmp_path):
    tasks = tmp_path / ".forgeflow" / "tasks"
    write_json(
        tasks / "review-only-task" / "review-report.json",
        {
            "approved": False,
            "findings": [{"summary": "quality gate evidence missing"}],
        },
    )

    result = run_monitor("--tasks", str(tasks), "--format", "json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"]["total_tasks"] == 1
    assert payload["summary"]["unknown"] == 1
    assert payload["summary"]["review_rejected"] == 1
    assert payload["summary"]["artifact_errors"] == 0
    assert payload["tasks"][0]["task_id"] == "review-only-task"
    assert payload["tasks"][0]["review_status"] == "rejected"
    assert payload["top_failure_patterns"] == [{"message": "quality gate evidence missing", "count": 1}]


def test_monitor_missing_tasks_root_returns_empty_summary(tmp_path):
    result = run_monitor("--tasks", str(tmp_path / "missing"), "--format", "json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"]["total_tasks"] == 0
    assert payload["tasks"] == []
