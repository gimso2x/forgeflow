import json
import os
import subprocess
import sys
from pathlib import Path

from forgeflow_runtime.orchestrator import load_runtime_policy, run_route


ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_task_dir(tmp_path: Path) -> Path:
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    _write_json(
        task_dir / "brief.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "objective": "Run a small route",
            "in_scope": ["runtime"],
            "out_of_scope": [],
            "constraints": ["local only"],
            "acceptance_criteria": ["route works"],
            "risk_level": "low",
        },
    )
    _write_json(
        task_dir / "run-state.json",
        {
            "schema_version": "0.1",
            "task_id": "task-001",
            "current_stage": "clarify",
            "status": "in_progress",
            "completed_gates": ["clarification_complete"],
            "failed_gates": [],
            "retries": {},
            "current_task_id": "",
            "spec_review_approved": False,
            "quality_review_approved": False,
        },
    )
    return task_dir


def _run_orchestrator_cli(
    *args: str,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_orchestrator.py"), *args],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=effective_env,
    )


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


def test_cli_execute_real_codex_uses_binary_from_path_without_live_credentials(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    codex.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "assert sys.argv[1] == 'exec'\n"
        "print('FAKE_CODEX_REAL_OUTPUT')\n",
        encoding="utf-8",
    )
    codex.chmod(0o755)

    result = _run_orchestrator_cli(
        "execute",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--adapter",
        "codex",
        "--real",
        env={"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"},
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert payload["adapter"] == "codex"
    assert (task_dir / "clarify-output.md").read_text(encoding="utf-8").strip() == "FAKE_CODEX_REAL_OUTPUT"


def test_cli_execute_real_claude_uses_binary_from_path_without_live_credentials(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    claude.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "assert '-p' in sys.argv\n"
        "assert '--bare' in sys.argv\n"
        "assert '--dangerously-skip-permissions' in sys.argv\n"
        "print('FAKE_CLAUDE_REAL_OUTPUT')\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)

    result = _run_orchestrator_cli(
        "execute",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--adapter",
        "claude",
        "--real",
        env={"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"},
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert payload["adapter"] == "claude"
    assert payload["execution_mode"] == "real"
    assert (task_dir / "clarify-output.md").read_text(encoding="utf-8").strip() == "FAKE_CLAUDE_REAL_OUTPUT"


def test_cli_execute_real_unsupported_adapter_fails_explicitly(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    result = _run_orchestrator_cli(
        "execute",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--adapter",
        "cursor",
        "--real",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert payload["error"] == "real adapter unsupported: cursor; supported real adapters: claude, codex"


def test_cli_execute_real_codex_missing_binary_is_actionable(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    result = _run_orchestrator_cli(
        "execute",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--adapter",
        "codex",
        "--real",
        env={"PATH": str(tmp_path / "empty-bin")},
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert payload["error"] == "codex binary not found on PATH; install/auth Codex CLI or omit --real to use the safe stub"


def test_real_adapter_boundary_doc_defines_supported_slice_and_failure_modes() -> None:
    doc = (ROOT / "docs" / "real-adapter-boundary.md").read_text(encoding="utf-8")

    assert "Supported real execution slice" in doc
    assert "Claude Code and Codex CLI" in doc
    assert "Stub execution remains the default" in doc
    assert "missing CLI" in doc
    assert "auth failure" in doc
    assert "non-zero exit" in doc
    assert "malformed output" in doc


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


def test_readme_examples_describe_manual_execution_flow() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "## Quickstart" in readme
    assert "make validate" in readme
    assert "make orchestrator-help" in readme
    assert "make runtime-sample" in readme
    assert "scripts/run_orchestrator.py init" in readme
    assert "Other manual `run_orchestrator.py` commands mutate their target `--task-dir`" in readme
    assert "scripts/run_orchestrator.py execute --task-dir" in readme
    assert "advance --execute" in readme
    assert "## Using ForgeFlow in Codex" in readme
    assert "cp adapters/generated/codex/CODEX.md ./CODEX.md" in readme
    assert "codex exec" in readme
    assert "## Using ForgeFlow in Claude Code" in readme
    assert "cp adapters/generated/claude/CLAUDE.md ./CLAUDE.md" in readme
    assert "claude -p" in readme
    assert "## Claude Code prompt templates" in readme
    assert "### Small task template" in readme
    assert "### Medium task template" in readme
    assert "### Large / high-risk task template" in readme
    assert "State the route you are using" in readme
    assert "Do not merge spec-review and quality-review" in readme
    assert "run`은 artifact/gate 기준으로 route 상태를 진행" in readme
    assert "execute`는 현재 stage를 어댑터로 실행" in readme


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
