import json
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.orchestrator import load_runtime_policy, run_route

from tests.runtime.cli_helpers import ROOT, make_task_dir, run_orchestrator_cli

_make_task_dir = make_task_dir
_run_orchestrator_cli = run_orchestrator_cli


def test_install_documents_manual_execution_flow() -> None:
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

    assert "make validate" in install
    assert "make runtime-sample" in install
    assert "scripts/run_orchestrator.py init" in install
    assert "run_orchestrator.py execute" in install
    assert "adapter codex" in install
    assert "adapter claude" in install
    assert "cp adapters/generated/codex/CODEX.md" in install
    assert "cp adapters/generated/claude/CLAUDE.md" in install
    assert "codex exec" in install
    assert "claude -p" in install


def test_runtime_sample_cli_uses_disposable_fixture_copy() -> None:
    fixture_dir = ROOT / "examples" / "runtime-fixtures" / "small-doc-task"
    tracked_files = {
        path.relative_to(fixture_dir): path.read_text(encoding="utf-8")
        for path in fixture_dir.rglob("*")
        if path.is_file()
    }

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_runtime_sample.py",
            "--fixture-dir",
            str(fixture_dir),
            "--route",
            "small",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "completed"
    assert payload["current_stage"] == "finalize"
    assert payload["sample_source_fixture"] == "examples/runtime-fixtures/small-doc-task"
    assert "sample_workspace" not in payload

    for rel, original in tracked_files.items():
        assert (fixture_dir / rel).read_text(encoding="utf-8") == original


def test_runtime_sample_cli_rejects_non_directory_fixture(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-dir.json"
    file_path.write_text("{}", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_runtime_sample.py",
            "--fixture-dir",
            str(file_path),
            "--route",
            "small",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("ERROR: fixture directory is not a directory:")


def test_cli_reports_runtime_violations_without_tracebacks(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    for command_args, expected_error in [
        (("run", "--task-dir", str(task_dir), "--route", "unknown"), "ERROR: unknown route: unknown"),
        (
            ("advance", "--task-dir", str(task_dir), "--route", "unknown", "--current-stage", "clarify"),
            "ERROR: unknown route: unknown",
        ),
        (
            ("step-back", "--task-dir", str(task_dir), "--route", "unknown", "--current-stage", "quality-review"),
            "ERROR: unknown route: unknown",
        ),
        (("escalate", "--task-dir", str(task_dir), "--from-route", "unknown"), "ERROR: unknown route for escalation: unknown"),
    ]:
        result = _run_orchestrator_cli(*command_args)

        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr.startswith(expected_error)


def test_medium_and_large_runtime_fixtures_run_end_to_end(tmp_path: Path) -> None:
    fixtures_root = ROOT / "examples" / "runtime-fixtures"

    for fixture_name, route_name, expected_stage in [
        ("medium-refactor-task", "medium", "finalize"),
        ("medium-plan-with-weak-verification", "medium", "finalize"),
        ("large-migration-task", "large_high_risk", "long-run"),
        ("large-approved-but-unsafe", "large_high_risk", "long-run"),
    ]:
        source_dir = fixtures_root / fixture_name
        task_dir = tmp_path / fixture_name
        subprocess.run(["cp", "-R", str(source_dir), str(task_dir)], check=True)

        result = run_route(task_dir=task_dir, policy=load_runtime_policy(ROOT), route_name=route_name)

        assert result["status"] == "completed"
        assert result["current_stage"] == expected_stage


def test_adherence_eval_cli_runs_valid_and_negative_fixtures() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_adherence_evals.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ADHERENCE EVALS: PASS" in result.stdout
    assert "small-doc-task" in result.stdout
    assert "resume-small-task" in result.stdout
    assert "medium-refactor-task" in result.stdout
    assert "medium-plan-with-weak-verification" in result.stdout
    assert "large-migration-task" in result.stdout
    assert "large-approved-but-unsafe" in result.stdout
    assert "missing-quality-approval" in result.stdout
    assert "invalid-review-report" in result.stdout
    assert "missing-run-state-before-spec-review" in result.stdout
    assert "missing-eval-record-before-long-run" in result.stdout
    assert "mixed-task-review-report" in result.stdout
    assert "mixed-task-decision-log" in result.stdout
    assert "checkpoint-gate-drift" in result.stdout
    assert "future-gate-checkpoint-drift" in result.stdout
    assert "completed-checkpoint-drift" in result.stdout
    assert "medium-ledger-gate-drift" in result.stdout
    assert "large-spec-quality-mismatch" in result.stdout
    assert "large-session-state-stale-review-ref" in result.stdout
    assert "medium-session-state-route-drift" in result.stdout
