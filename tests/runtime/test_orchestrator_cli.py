import json
import shutil
from pathlib import Path

from tests.runtime.cli_helpers import ROOT, make_task_dir, run_orchestrator_cli, write_json


_make_task_dir = make_task_dir
_run_orchestrator_cli = run_orchestrator_cli
_write_json = write_json


def test_cli_help_includes_operator_shell_examples() -> None:
    result = _run_orchestrator_cli("--help")

    assert result.returncode == 0
    assert "validate-workflow" in result.stdout
    assert "Operator shell examples:" in result.stdout
    assert "python3 scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small" in result.stdout
    assert "clarify-first is canonical" in result.stdout
    assert "Manual commands mutate the target task-dir" in result.stdout


def test_cli_validate_workflow_accepts_valid_project_overlay(tmp_path: Path) -> None:
    project_dir = tmp_path / "target-project"
    workflow_dir = project_dir / ".forgeflow"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "workflow.yaml").write_text(
        """
name: custom-project-workflow
routes:
  small:
    - clarify
    - spec-review
    - execute
    - quality-review
steps:
  execute:
    role: nextjs-worker
    non_negotiables:
      - keep changes scoped
""".lstrip(),
        encoding="utf-8",
    )

    result = _run_orchestrator_cli("validate-workflow", "--project-root", str(project_dir))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "valid"
    assert payload["project_root"] == str(project_dir.resolve())
    assert payload["override_path"] == str((workflow_dir / "workflow.yaml").resolve())
    assert payload["workflow_name"] == "custom-project-workflow"
    assert payload["routes"]["small"] == ["clarify", "spec-review", "execute", "quality-review"]
    assert payload["steps"]["execute"]["role"] == "nextjs-worker"


def test_cli_validate_workflow_reports_invalid_project_overlay(tmp_path: Path) -> None:
    project_dir = tmp_path / "target-project"
    workflow_dir = project_dir / ".forgeflow"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "workflow.yaml").write_text(
        """
routes:
  tiny:
    - clarify
""".lstrip(),
        encoding="utf-8",
    )

    result = _run_orchestrator_cli("validate-workflow", "--project-root", str(project_dir))

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("ERROR: ")
    assert "unknown workflow route: tiny" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_help_keeps_fallback_start_execute_warning_adjacent_to_examples() -> None:
    result = _run_orchestrator_cli("--help")

    assert result.returncode == 0
    examples = result.stdout.split("Operator shell examples:", 1)[1].split("Notes:", 1)[0]
    fallback_section = examples.split("# Fallback entries mutate task artifacts", 1)[1].split("# Manual stage control", 1)[0]
    assert "python3 scripts/run_orchestrator.py start" in fallback_section
    assert "python3 scripts/run_orchestrator.py execute" in fallback_section
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
    assert "python3 scripts/run_orchestrator.py exec-stage" in mutating_section
    assert "python3 scripts/run_orchestrator.py advance" in mutating_section
    assert "python3 scripts/run_orchestrator.py status" not in manual_section


def test_cli_init_bootstraps_task_from_operator_inputs(tmp_path: Path) -> None:
    # Use .forgeflow/tasks/<id> structure so project_root resolves correctly
    task_dir = tmp_path / ".forgeflow" / "tasks" / "my-task"

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
    # init only creates core JSON artifacts — no docs/agents/skills
    for name in [
        "brief.json",
        "run-state.json",
        "checkpoint.json",
        "session-state.json",
    ]:
        assert name in payload["created"]
        assert (task_dir / name).exists(), f"{name} missing in task_dir"
    # drafts should NOT exist after init alone
    assert not (task_dir / "docs" / "PRD.md").exists()
    assert not (task_dir / "CLAUDE.md").exists()
    assert "selected_architecture" not in payload
    assert "clarify를 실행하여" in payload["next_action"]
    brief = json.loads((task_dir / "brief.json").read_text(encoding="utf-8"))
    assert brief["task_id"] == "my-task-001"
    assert brief["objective"] == "Update README quickstart"
    assert brief["risk_level"] == "low"

    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert run_state["task_id"] == "my-task-001"
    assert run_state["current_stage"] == "clarify"
    assert run_state["status"] == "not_started"

    # now run clarify to generate drafts
    clarify_result = _run_orchestrator_cli("clarify", "--task-dir", str(task_dir))
    assert clarify_result.returncode == 0
    clarify_payload = json.loads(clarify_result.stdout)
    assert clarify_payload["task_id"] == "my-task-001"
    assert clarify_payload["route"] == "small"
    assert "selected_architecture" in clarify_payload

    from forgeflow_runtime.env_adapter import get_adapter_config
    config = get_adapter_config()

    # drafts now exist
    for name in [
        "docs/PRD.md",
        "docs/ARCHITECTURE.md",
        "tasks/init-summary.md",
        config["metadata_file"],
    ]:
        assert (task_dir / name).exists(), f"{name} missing after clarify"
    agents_dir = tmp_path / config["dot_dir"] / "agents"
    skills_dir = tmp_path / config["dot_dir"] / "skills"
    assert agents_dir.exists(), f"{config['dot_dir']}/agents/ missing in project_root"
    assert skills_dir.exists(), f"{config['dot_dir']}/skills/ missing in project_root"
    assert any(agents_dir.glob("*.md")), "No agent files created"
    assert any(d.is_dir() for d in skills_dir.iterdir()), "No skill dirs created"

    status_result = _run_orchestrator_cli("status", "--task-dir", str(task_dir))
    assert status_result.returncode == 0
    status_payload = json.loads(status_result.stdout)
    assert status_payload["task_id"] == "my-task-001"
    assert status_payload["route"] == "small"
    assert status_payload["current_stage"] == "execute"


def test_cli_init_status_points_new_users_to_clarify(tmp_path: Path) -> None:
    task_dir = tmp_path / ".forgeflow" / "tasks" / "new-user-task"
    init_result = _run_orchestrator_cli(
        "init",
        "--task-dir",
        str(task_dir),
        "--task-id",
        "new-user-task",
        "--objective",
        "Update README quickstart",
        "--risk",
        "low",
    )
    assert init_result.returncode == 0, init_result.stderr

    status_result = _run_orchestrator_cli("status", "--task-dir", str(task_dir))

    assert status_result.returncode == 0, status_result.stderr
    status_payload = json.loads(status_result.stdout)
    assert status_payload["current_stage"] == "clarify"
    assert status_payload["next_action"] == "clarify를 실행하여 brief와 초안을 완성하세요."


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


def test_cli_init_can_infer_task_dir_and_task_id_from_objective(tmp_path: Path) -> None:
    project_dir = tmp_path / "target-project"
    project_dir.mkdir()

    result = _run_orchestrator_cli(
        "init",
        "--objective",
        "Update README quickstart",
        "--risk",
        "low",
        cwd=project_dir,
    )

    assert result.returncode == 0, result.stderr
    expected_task_dir = project_dir / ".forgeflow" / "tasks" / "update-readme-quickstart"
    payload = json.loads(result.stdout)
    assert payload["task_id"] == "update-readme-quickstart"
    assert Path(payload["task_dir"]) == expected_task_dir
    brief = json.loads((expected_task_dir / "brief.json").read_text(encoding="utf-8"))
    assert brief["objective"] == "Update README quickstart"


def test_cli_init_with_task_dir_can_bootstrap_without_objective(tmp_path: Path) -> None:
    task_dir = tmp_path / ".forgeflow" / "tasks" / "manual-task"

    result = _run_orchestrator_cli("init", "--task-dir", str(task_dir), "--risk", "low")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["task_id"] == "manual-task"
    brief = json.loads((task_dir / "brief.json").read_text(encoding="utf-8"))
    assert brief["objective"] == "Bootstrap manual-task"

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
    assert result.stderr.startswith("ERROR: ")
    assert "plugin cache" in result.stderr
    assert "--task-dir" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (plugin_cache_dir / ".forgeflow" / "tasks" / "cache-write-001").exists()


def test_cli_init_without_task_dir_allows_ordinary_plugin_marketplace_named_project(tmp_path: Path) -> None:
    project_dir = tmp_path / "plugin" / "marketplace" / "myproj"
    project_dir.mkdir(parents=True)

    result = _run_orchestrator_cli(
        "init",
        "--task-id",
        "false-positive-001",
        "--objective",
        "Ordinary project path should not be blocked",
        "--risk",
        "low",
        cwd=project_dir,
    )

    assert result.returncode == 0, result.stderr
    expected_task_dir = project_dir / ".forgeflow" / "tasks" / "false-positive-001"
    payload = json.loads(result.stdout)
    assert Path(payload["task_dir"]) == expected_task_dir
    assert (expected_task_dir / "brief.json").exists()


def test_cli_mutating_commands_refuse_explicit_task_dir_inside_plugin_cache(tmp_path: Path) -> None:
    plugin_task_dir = tmp_path / ".claude" / "plugins" / "cache" / "forgeflow" / ".forgeflow" / "tasks" / "bad-task"
    plugin_task_dir.mkdir(parents=True)
    _write_json(
        plugin_task_dir / "run-state.json",
        {
            "schema_version": "0.2",
            "task_id": "bad-task",
            "current_stage": "clarify",
            "status": "in_progress",
            "completed_gates": [],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "",
            "spec_review_approved": False,
            "quality_review_approved": False,
        },
    )

    for command in [
        ("init", "--task-id", "bad-task", "--objective", "Do not write here", "--risk", "low"),
        ("start",),
        ("execute", "--route", "small"),
        ("resume",),
        ("advance", "--route", "small", "--current-stage", "clarify"),
        ("retry", "--stage", "clarify"),
        ("step-back", "--route", "small", "--current-stage", "clarify"),
        ("escalate", "--from-route", "small"),
        ("exec-stage", "--route", "small"),
    ]:
        result = _run_orchestrator_cli(command[0], "--task-dir", str(plugin_task_dir), *command[1:])
        assert result.returncode == 1, (command, result.stderr)
        assert result.stdout == ""
        assert result.stderr.startswith("ERROR: ")
        assert "plugin cache" in result.stderr or "marketplace cache" in result.stderr
        assert "--task-dir" in result.stderr
        assert "Traceback" not in result.stderr


def test_cli_status_allows_read_only_inspection_inside_plugin_cache(tmp_path: Path) -> None:
    source_task_dir = ROOT / "examples" / "runtime-fixtures" / "small-doc-task"
    plugin_task_dir = tmp_path / ".claude" / "plugins" / "cache" / "forgeflow" / ".forgeflow" / "tasks" / "inspect-only"
    shutil.copytree(source_task_dir, plugin_task_dir)

    result = _run_orchestrator_cli("status", "--task-dir", str(plugin_task_dir))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["task_id"] == "task-runtime-small-001"
    assert payload["current_stage"] == "finalize"


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


def test_cli_execute_runs_sample_fixture(tmp_path: Path) -> None:
    task_dir = tmp_path / "cli-task"
    task_dir.mkdir()
    _write_json(
        task_dir / "brief.json",
        {
            "schema_version": "0.2",
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
            "schema_version": "0.2",
            "task_id": "task-cli-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["cli looks fine"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )

    result = _run_orchestrator_cli("execute", "--task-dir", str(task_dir), "--route", "small")

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


def test_cli_execute_auto_detects_small_route_and_min_route_can_raise_it(tmp_path: Path) -> None:
    task_dir = tmp_path / "cli-auto-route"
    task_dir.mkdir()
    _write_json(
        task_dir / "brief.json",
        {
            "schema_version": "0.2",
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
            "schema_version": "0.2",
            "task_id": "task-auto-001",
            "review_type": "quality",
            "verdict": "approved",
            "findings": ["cli looks fine"],
            "approved_by": "quality-reviewer",
            "next_action": "finalize 가능",
        },
    )

    auto_result = _run_orchestrator_cli("execute", "--task-dir", str(task_dir))
    assert auto_result.returncode == 0
    checkpoint = json.loads((task_dir / "checkpoint.json").read_text(encoding="utf-8"))
    assert checkpoint["route"] == "small"

    raised_result = _run_orchestrator_cli("execute", "--task-dir", str(task_dir), "--min-route", "medium")
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


def test_cli_exec_stage_runs_current_stage_and_writes_output(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)
    execute_result = _run_orchestrator_cli("exec-stage", "--task-dir", str(task_dir), "--route", "small", "--adapter", "codex")

    assert execute_result.returncode == 0
    payload = json.loads(execute_result.stdout)
    assert payload["stage"] == "clarify"
    assert payload["adapter"] == "codex"
    assert payload["execution_mode"] == "stub"
    assert "STUB EXECUTION" in payload["warning"]
    assert "[STUB MODE]" in execute_result.stderr
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
        "codex",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["next_stage"] == "execute"
    assert payload["execution"]["status"] == "success"
    assert payload["execution"]["stage"] == "execute"
    run_state = json.loads((task_dir / "run-state.json").read_text(encoding="utf-8"))
    assert run_state["current_stage"] == "execute"
    assert (task_dir / "execute-output.md").exists()


def test_cli_exec_stage_reports_non_runtime_failures_cleanly(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    result = _run_orchestrator_cli(
        "exec-stage",
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
        "codex",
    )
    assert advance_execute.returncode == 0
    advance_execute_payload = json.loads(advance_execute.stdout)
    assert advance_execute_payload["next_stage"] == "execute"
    assert advance_execute_payload["execution"]["stage"] == "execute"
    assert advance_execute_payload["execution"]["adapter"] == "codex"
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
