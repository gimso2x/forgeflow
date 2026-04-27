import json
from pathlib import Path

from tests.runtime.cli_helpers import ROOT, make_task_dir, run_orchestrator_cli, write_json


_make_task_dir = make_task_dir
_run_orchestrator_cli = run_orchestrator_cli
_write_json = write_json


def test_cli_help_includes_operator_shell_examples() -> None:
    result = _run_orchestrator_cli("--help")

    assert result.returncode == 0
    assert "Operator shell examples:" in result.stdout
    assert "python3 scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small" in result.stdout
    assert "clarify-first is canonical" in result.stdout
    assert "Manual commands mutate the target task-dir" in result.stdout


def test_cli_help_keeps_fallback_start_run_warning_adjacent_to_examples() -> None:
    result = _run_orchestrator_cli("--help")

    assert result.returncode == 0
    examples = result.stdout.split("Operator shell examples:", 1)[1].split("Notes:", 1)[0]
    fallback_section = examples.split("# Fallback entries mutate task artifacts", 1)[1].split("# Manual stage control", 1)[0]
    assert "python3 scripts/run_orchestrator.py start" in fallback_section
    assert "python3 scripts/run_orchestrator.py run" in fallback_section
    assert "can reuse persisted route" not in fallback_section


def test_cli_help_separates_read_only_status_from_mutating_manual_stage_examples() -> None:
    result = _run_orchestrator_cli("--help")

    assert result.returncode == 0
    examples = result.stdout.split("Operator shell examples:", 1)[1].split("Notes:", 1)[0]
    manual_section = examples.split("# Manual stage control", 1)[1]
    assert "# Read-only status path is repo-managed for first-clone shells." in manual_section
    assert "make setup" in manual_section
    assert "make check-env" in manual_section
    assert "make orchestrator-status" in manual_section
    assert manual_section.index("make setup") < manual_section.index("make check-env") < manual_section.index("make orchestrator-status")
    assert "# Mutating manual stage commands stay explicit operator commands." in manual_section
    mutating_section = manual_section.split("# Mutating manual stage commands stay explicit operator commands.", 1)[1]
    assert "python3 scripts/run_orchestrator.py execute" in mutating_section
    assert "python3 scripts/run_orchestrator.py advance" in mutating_section
    assert "python3 scripts/run_orchestrator.py status" not in manual_section


def test_cli_init_bootstraps_task_from_operator_inputs(tmp_path: Path) -> None:
    task_dir = tmp_path / "my-task"

    result = _run_orchestrator_cli(
        "init",
        "--task-dir",
        str(task_dir),
        "--task-id",
        "my-task-001",
        "--objective",
        "Update README quickstart",
        "--risk",
        "low",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["task_id"] == "my-task-001"
    assert payload["route"] == "small"
    assert payload["created"] == ["brief.json", "run-state.json", "checkpoint.json", "session-state.json"]
    assert payload["next_action"] == "run status or execute the clarify stage"

    brief = json.loads((task_dir / "brief.json").read_text(encoding="utf-8"))
    assert brief["task_id"] == "my-task-001"
    assert brief["objective"] == "Update README quickstart"
    assert brief["risk_level"] == "low"

    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert run_state["task_id"] == "my-task-001"
    assert run_state["current_stage"] == "clarify"
    assert run_state["status"] == "not_started"

    status_result = _run_orchestrator_cli("status", "--task-dir", str(task_dir))
    assert status_result.returncode == 0
    status_payload = json.loads(status_result.stdout)
    assert status_payload["task_id"] == "my-task-001"
    assert status_payload["route"] == "small"
    assert status_payload["current_stage"] == "clarify"


def test_cli_init_without_task_dir_writes_under_current_project_forgeflow_tasks(tmp_path: Path) -> None:
    project_dir = tmp_path / "target-project"
    project_dir.mkdir()

    result = _run_orchestrator_cli(
        "init",
        "--task-id",
        "readme-quickstart-001",
        "--objective",
        "Update README quickstart",
        "--risk",
        "low",
        cwd=project_dir,
    )

    assert result.returncode == 0, result.stderr
    expected_task_dir = project_dir / ".forgeflow" / "tasks" / "readme-quickstart-001"
    payload = json.loads(result.stdout)
    assert Path(payload["task_dir"]) == expected_task_dir
    assert (expected_task_dir / "brief.json").exists()
    assert (expected_task_dir / "run-state.json").exists()
    assert not (ROOT / ".forgeflow" / "tasks" / "readme-quickstart-001").exists()


def test_cli_init_without_task_dir_refuses_plugin_cache_cwd(tmp_path: Path) -> None:
    plugin_cache_dir = tmp_path / ".claude" / "plugins" / "cache" / "forgeflow"
    plugin_cache_dir.mkdir(parents=True)

    result = _run_orchestrator_cli(
        "init",
        "--task-id",
        "cache-write-001",
        "--objective",
        "Do not write into plugin cache",
        "--risk",
        "low",
        cwd=plugin_cache_dir,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "plugin cache" in result.stderr
    assert "--task-dir" in result.stderr
    assert not (plugin_cache_dir / ".forgeflow" / "tasks" / "cache-write-001").exists()


def test_cli_init_refuses_to_overwrite_existing_artifacts(tmp_path: Path) -> None:
    task_dir = tmp_path / "existing-task"
    task_dir.mkdir()
    (task_dir / "brief.json").write_text("{}", encoding="utf-8")

    result = _run_orchestrator_cli(
        "init",
        "--task-dir",
        str(task_dir),
        "--task-id",
        "existing-001",
        "--objective",
        "Do not overwrite me",
        "--risk",
        "low",
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("ERROR: init refuses to overwrite existing task artifacts")


def test_cli_run_executes_sample_fixture(tmp_path: Path) -> None:
    task_dir = tmp_path / "cli-task"
    task_dir.mkdir()
    _write_json(
        task_dir / "brief.json",
        {
            "schema_version": "0.1",
            "task_id": "task-cli-001",
            "objective": "Run CLI route",
            "in_scope": ["runtime"],
            "out_of_scope": [],
            "constraints": ["local only"],
            "acceptance_criteria": ["cli works"],
            "risk_level": "low",
        },
    )
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "task-cli-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["cli looks fine"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )

    result = _run_orchestrator_cli("run", "--task-dir", str(task_dir), "--route", "small")

    assert result.returncode == 0
    assert (task_dir / "run-state.json").exists()
    assert (task_dir / "decision-log.json").exists()


def test_cli_supports_start_resume_and_status(tmp_path: Path) -> None:
    task_dir = tmp_path / "cli-start-task"

    start_result = _run_orchestrator_cli("start", "--task-dir", str(task_dir), "--route", "medium")
    assert start_result.returncode == 0
    assert json.loads(start_result.stdout)["route"] == "medium"

    status_result = _run_orchestrator_cli("status", "--task-dir", str(task_dir), "--route", "medium")
    assert status_result.returncode == 0
    assert json.loads(status_result.stdout)["current_stage"] == "clarify"

    resume_result = _run_orchestrator_cli("resume", "--task-dir", str(task_dir), "--route", "medium")
    assert resume_result.returncode == 0
    assert json.loads(resume_result.stdout)["route"] == "medium"


def test_cli_start_supports_min_route_override_without_explicit_route(tmp_path: Path) -> None:
    task_dir = tmp_path / "cli-min-route-start"

    start_result = _run_orchestrator_cli("start", "--task-dir", str(task_dir), "--min-route", "medium")

    assert start_result.returncode == 0
    payload = json.loads(start_result.stdout)
    assert payload["route"] == "medium"


def test_cli_run_auto_detects_small_route_and_min_route_can_raise_it(tmp_path: Path) -> None:
    task_dir = tmp_path / "cli-auto-route"
    task_dir.mkdir()
    _write_json(
        task_dir / "brief.json",
        {
            "schema_version": "0.1",
            "task_id": "task-auto-001",
            "objective": "Auto route selection",
            "in_scope": ["runtime"],
            "out_of_scope": [],
            "constraints": ["local only"],
            "acceptance_criteria": ["auto route works"],
            "risk_level": "low",
        },
    )
    _write_json(
        task_dir / "review-report.json",
        {
            "schema_version": "0.1",
            "task_id": "task-auto-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["cli looks fine"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )

    auto_result = _run_orchestrator_cli("run", "--task-dir", str(task_dir))
    assert auto_result.returncode == 0
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    assert checkpoint["route"] == "small"

    raised_result = _run_orchestrator_cli("run", "--task-dir", str(task_dir), "--min-route", "medium")
    assert raised_result.returncode == 1
    assert "medium route requires plan-ledger.json" in raised_result.stderr


def test_cli_supports_recovery_commands(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    advance_result = _run_orchestrator_cli(
        "advance",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--current-stage",
        "clarify",
    )
    assert advance_result.returncode == 0
    assert json.loads(advance_result.stdout)["next_stage"] == "execute"

    retry_result = _run_orchestrator_cli("retry", "--task-dir", str(task_dir), "--stage", "execute", "--max-retries", "2")
    assert retry_result.returncode == 0
    assert json.loads(retry_result.stdout)["retries"]["execute"] == 1

    step_back_result = _run_orchestrator_cli(
        "step-back",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--current-stage",
        "quality-review",
    )
    assert step_back_result.returncode == 0
    assert json.loads(step_back_result.stdout)["current_stage"] == "execute"

    escalate_result = _run_orchestrator_cli("escalate", "--task-dir", str(task_dir), "--from-route", "small")
    assert escalate_result.returncode == 0
    assert json.loads(escalate_result.stdout)["status"] == "blocked"


def test_cli_execute_runs_current_stage_and_writes_output(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)
    execute_result = _run_orchestrator_cli("execute", "--task-dir", str(task_dir), "--route", "small", "--adapter", "codex")

    assert execute_result.returncode == 0
    payload = json.loads(execute_result.stdout)
    assert payload["stage"] == "clarify"
    assert payload["adapter"] == "codex"
    output_path = task_dir / "clarify-output.md"
    assert output_path.exists()
    assert "stub-codex-output" in output_path.read_text(encoding="utf-8")


def test_cli_advance_with_execute_runs_next_stage_and_updates_run_state(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    result = _run_orchestrator_cli(
        "advance",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--current-stage",
        "clarify",
        "--execute",
        "--adapter",
        "cursor",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["next_stage"] == "execute"
    assert payload["execution"]["status"] == "success"
    assert payload["execution"]["stage"] == "execute"
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert run_state["current_stage"] == "execute"
    assert (task_dir / "execute-output.md").exists()


def test_cli_execute_reports_non_runtime_failures_cleanly(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    result = _run_orchestrator_cli(
        "execute",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--role",
        "nonexistent-role",
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("ERROR: unknown role: nonexistent-role")


def test_cli_advance_execute_failure_keeps_previous_stage_state(tmp_path: Path) -> None:
    task_dir = tmp_path / "cli-medium-failure"

    start_result = _run_orchestrator_cli("start", "--task-dir", str(task_dir), "--route", "medium")
    assert start_result.returncode == 0

    advance_result = _run_orchestrator_cli(
        "advance",
        "--task-dir",
        str(task_dir),
        "--route",
        "medium",
        "--current-stage",
        "clarify",
        "--execute",
        "--role",
        "nonexistent-role",
    )
    assert advance_result.returncode == 1
    assert "ERROR: unknown role: nonexistent-role" in advance_result.stderr

    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert run_state["current_stage"] == "clarify"
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    assert checkpoint["current_stage"] == "clarify"
    assert not (task_dir / "plan-output.md").exists()


def test_cli_medium_route_execute_flow_is_automated_end_to_end(tmp_path: Path) -> None:
    task_dir = tmp_path / "cli-medium-flow"

    start_result = _run_orchestrator_cli("start", "--task-dir", str(task_dir), "--route", "medium")
    assert start_result.returncode == 0

    advance_plan = _run_orchestrator_cli(
        "advance",
        "--task-dir",
        str(task_dir),
        "--route",
        "medium",
        "--current-stage",
        "clarify",
        "--execute",
        "--adapter",
        "codex",
    )
    assert advance_plan.returncode == 0
    advance_plan_payload = json.loads(advance_plan.stdout)
    assert advance_plan_payload["next_stage"] == "plan"
    assert advance_plan_payload["execution"]["stage"] == "plan"
    assert (task_dir / "plan-output.md").exists()

    status_after_plan = _run_orchestrator_cli("status", "--task-dir", str(task_dir), "--route", "medium")
    assert status_after_plan.returncode == 0
    assert json.loads(status_after_plan.stdout)["current_stage"] == "plan"

    advance_execute = _run_orchestrator_cli(
        "advance",
        "--task-dir",
        str(task_dir),
        "--route",
        "medium",
        "--current-stage",
        "plan",
        "--execute",
        "--adapter",
        "cursor",
    )
    assert advance_execute.returncode == 0
    advance_execute_payload = json.loads(advance_execute.stdout)
    assert advance_execute_payload["next_stage"] == "execute"
    assert advance_execute_payload["execution"]["stage"] == "execute"
    assert advance_execute_payload["execution"]["adapter"] == "cursor"
    assert (task_dir / "execute-output.md").exists()

    status_after_execute = _run_orchestrator_cli("status", "--task-dir", str(task_dir), "--route", "medium")
    assert status_after_execute.returncode == 0
    status_payload = json.loads(status_after_execute.stdout)
    assert status_payload["current_stage"] == "execute"
    assert status_payload["current_task_id"] == "task-1"
    assert status_payload["required_gates"] == ["execution_evidenced", "quality_review_passed", "ready_to_finalize"]

    resume_result = _run_orchestrator_cli("resume", "--task-dir", str(task_dir), "--route", "medium")
    assert resume_result.returncode == 0
    resume_payload = json.loads(resume_result.stdout)
    assert resume_payload["current_stage"] == "execute"
    assert resume_payload["current_task_id"] == "task-1"
