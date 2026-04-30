from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dependency_manifest_names_runtime_and_test_dependencies() -> None:
    requirements = ROOT / "requirements.txt"

    assert requirements.exists()
    content = requirements.read_text(encoding="utf-8")
    assert "jsonschema" in content
    assert "PyYAML" in content
    assert "pytest" in content


def test_makefile_exposes_idempotent_setup_and_environment_check() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert ".PHONY: setup" in makefile
    assert "ifeq ($(OS),Windows_NT)" in makefile
    assert "VENV_BIN := $(VENV)/Scripts" in makefile
    assert "VENV_BIN := $(VENV)/bin" in makefile
    assert "$(PYTHON) -m venv $(VENV)" in makefile
    assert "$(VENV_PYTHON) -m pip install" in makefile
    assert "check-env" in makefile
    assert "$(VENV_PYTHON) scripts/check_environment.py" in makefile
    assert "$(VENV_PYTHON) scripts/validate_structure.py" in makefile
    assert "$(VENV_PYTHON) -m pytest tests/test_first_clone_setup.py -q" in makefile
    assert "$(VENV_PYTHON) -m pytest tests/test_codex_plugin_install.py -q" in makefile


def test_windows_powershell_wrappers_are_documented_and_present() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    windows_doc = (ROOT / "docs/windows.md").read_text(encoding="utf-8")

    for name in ["setup.ps1", "validate.ps1", "run_orchestrator.ps1", "install_codex_plugin.ps1"]:
        assert (ROOT / "scripts" / name).exists()
    assert (ROOT / "scripts" / "install_codex_plugin.py").exists()
    assert ".\\scripts\\setup.ps1" in readme
    assert ".\\scripts\\validate.ps1" in install
    assert ".\\scripts\\run_orchestrator.ps1" in windows_doc
    assert ".\\scripts\\install_codex_plugin.ps1" in windows_doc
    assert "$env:PYTHON" in windows_doc
    assert "py -3" in windows_doc
    assert "subprocess argument lists" in windows_doc
    assert "windows-smoke" in windows_doc


def test_makefile_smoke_targets_use_repo_managed_python_environment() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    smoke_section = makefile.split("plan-cli-smoke:", 1)[1].split("generate:", 1)[0]

    assert "\tpytest " not in smoke_section
    assert "\t$(PYTHON) scripts/" not in smoke_section
    assert smoke_section.count("$(VENV_PYTHON) -m pytest") >= 10
    assert "$(VENV_PYTHON) scripts/smoke_plan_cli.py" in smoke_section
    assert "$(VENV_PYTHON) scripts/smoke_claude_plugin.py" in smoke_section


def test_makefile_non_setup_helper_targets_use_repo_managed_python_environment() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    helper_section = makefile.split("runtime-sample:", 1)[1].split("clean:", 1)[0]

    assert "\t$(PYTHON) scripts/" not in helper_section
    assert "$(VENV_PYTHON) scripts/run_runtime_sample.py" in helper_section
    assert "$(VENV_PYTHON) scripts/run_adherence_evals.py" in helper_section
    assert "$(VENV_PYTHON) scripts/generate_adapters.py" in helper_section
    assert "$(VENV_PYTHON) scripts/validate_sample_artifacts.py" in helper_section


def test_readme_quickstart_points_to_install_guide() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

    assert "## Installation" in readme
    assert "INSTALL.md" in readme
    assert "make setup" in install
    assert "make check-env" in install
    assert "make validate" in install
    assert install.index("make setup") < install.index("make check-env")
    assert install.index("make check-env") < install.index("make validate")


def test_install_update_path_rechecks_first_clone_dependencies_before_validation() -> None:
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    update_section = install.split("## 업데이트", 1)[1]

    assert "git -C /path/to/forgeflow pull" in update_section
    assert update_section.index("make -C /path/to/forgeflow setup") < update_section.index("make -C /path/to/forgeflow check-env") < update_section.index("make -C /path/to/forgeflow validate")
    assert "현재 shell 위치와 무관하게" in update_section
    assert "새 dependency가 추가된 release" in update_section


def test_install_runtime_sample_uses_repo_managed_make_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    sample_section = install.split("샘플 실행:", 1)[1].split("직접 task를 만들 때:", 1)[0]

    assert "runtime-sample:" in makefile
    assert "$(VENV_PYTHON) scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small" in makefile
    assert "make setup" in sample_section
    assert "make check-env" in sample_section
    assert "make runtime-sample" in sample_section.splitlines()
    assert sample_section.index("make setup") < sample_section.index("make check-env") < sample_section.index("make runtime-sample")
    assert "python3 scripts/run_runtime_sample.py" not in sample_section


def test_scripts_readme_recommends_repo_managed_validate_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    scripts_readme = (ROOT / "scripts/README.md").read_text(encoding="utf-8")
    recommended_section = scripts_readme.split("## 권장 실행 순서", 1)[1].split("## Runtime sample", 1)[0]

    assert "validate:" in makefile
    assert "$(VENV_PYTHON) scripts/validate_structure.py" in makefile
    assert "$(VENV_PYTHON) scripts/validate_policy.py" in makefile
    assert "$(VENV_PYTHON) scripts/validate_generated.py" in makefile
    assert "$(VENV_PYTHON) scripts/validate_sample_artifacts.py" in makefile
    validate_generated = (ROOT / "scripts/validate_generated.py").read_text(encoding="utf-8")
    assert "generate_adapters.py" in validate_generated
    assert "regeneration left adapters/generated clean" in validate_generated
    assert "make setup" in recommended_section
    assert "make check-env" in recommended_section
    assert "make validate" in recommended_section.splitlines()
    assert recommended_section.index("make setup") < recommended_section.index("make check-env") < recommended_section.index("make validate")
    assert "python3 scripts/validate_" not in scripts_readme
    assert "python3 scripts/generate_adapters.py" not in scripts_readme


def test_scripts_readme_runtime_sample_uses_repo_managed_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    scripts_readme = (ROOT / "scripts/README.md").read_text(encoding="utf-8")
    runtime_section = scripts_readme.split("## Runtime sample", 1)[1]

    assert "runtime-sample:" in makefile
    assert "$(VENV_PYTHON) scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small" in makefile
    assert "make setup" in runtime_section
    assert "make check-env" in runtime_section
    assert "make runtime-sample" in runtime_section.splitlines()
    assert runtime_section.index("make setup") < runtime_section.index("make check-env") < runtime_section.index("make runtime-sample")
    assert "--fixture-dir`는 task fixture 디렉터리를 가리켜야 하며, 파일 경로면 명시적 `ERROR:`로 실패한다." in runtime_section
    assert "python3 scripts/run_runtime_sample.py" not in runtime_section


def test_install_update_path_keeps_make_commands_in_checkout_context() -> None:
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    update_section = install.split("## 업데이트", 1)[1]

    assert "git -C /path/to/forgeflow pull" in update_section
    assert update_section.index("make -C /path/to/forgeflow setup") < update_section.index("make -C /path/to/forgeflow check-env") < update_section.index("make -C /path/to/forgeflow validate")
    assert "현재 shell 위치와 무관하게" in update_section
    assert "새 dependency가 추가된 release" in update_section


def test_install_local_runtime_section_points_to_setup_and_validate() -> None:
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    runtime_section = install.split("## 로컬 runtime 설치", 1)[1].split("## 실제 CLI 실행", 1)[0]

    assert "make setup" in runtime_section
    assert "make check-env" in runtime_section
    assert "make validate" in runtime_section
    assert runtime_section.index("make setup") < runtime_section.index("make check-env")
    assert runtime_section.index("make check-env") < runtime_section.index("make validate")


def test_adherence_eval_docs_use_make_target_after_environment_setup() -> None:
    readme = (ROOT / "evals/adherence/README.md").read_text(encoding="utf-8")
    command_block = readme.split("실행 명령:", 1)[1].split("현재 executable 체크:", 1)[0]

    assert "make setup" in command_block
    assert "make check-env" in command_block
    assert "make adherence-evals" in command_block
    assert command_block.index("make setup") < command_block.index("make check-env") < command_block.index("make adherence-evals")
    assert "python3 scripts/run_adherence_evals.py" not in command_block


def test_makefile_defines_monitor_summary_targets() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "monitor-summary:" in makefile
    assert "$(VENV_PYTHON) scripts/forgeflow_monitor.py --tasks .forgeflow/tasks --recent 10 --format md" in makefile
    assert "monitor-summary-json:" in makefile
    assert "$(VENV_PYTHON) scripts/forgeflow_monitor.py --tasks .forgeflow/tasks --recent 10 --format json" in makefile


def test_install_safe_sample_uses_repo_managed_runtime_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    sample_section = install.split("샘플 실행:", 1)[1].split("직접 task를 만들 때:", 1)[0]

    assert "runtime-sample:" in makefile
    assert "$(VENV_PYTHON) scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small" in makefile
    assert "make setup" in sample_section
    assert "make check-env" in sample_section
    assert "make runtime-sample" in sample_section.splitlines()
    assert sample_section.index("make setup") < sample_section.index("make check-env") < sample_section.index("make runtime-sample")
    assert "python3 scripts/run_runtime_sample.py" not in sample_section


def test_install_local_runtime_uses_repo_managed_targets() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

    assert "runtime-sample:" in makefile
    assert "make setup" in install
    assert "make check-env" in install
    assert "make runtime-sample" in install


def test_makefile_defines_orchestrator_help_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "orchestrator-help:" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py --help" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py run --help" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py advance --help" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py execute --help" in makefile


def test_makefile_defines_orchestrator_status_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "orchestrator-status:" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py status --task-dir examples/runtime-fixtures/small-doc-task" in makefile


def test_readme_uses_repo_managed_orchestrator_help_target_for_read_only_help() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "orchestrator-help:" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py --help" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py run --help" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py advance --help" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py execute --help" in makefile


def test_readme_uses_repo_managed_status_target_for_read_only_fixture_inspection() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "orchestrator-status:" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py status --task-dir examples/runtime-fixtures/small-doc-task" in makefile


def test_operator_shell_doc_uses_repo_managed_runtime_sample_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    doc = (ROOT / "docs/operator-shell.md").read_text(encoding="utf-8")
    sample_section = doc.split("## Safe sample command", 1)[1].split("## Canonical help", 1)[0]

    assert "runtime-sample:" in makefile
    assert "$(VENV_PYTHON) scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small" in makefile
    assert "make setup" in sample_section
    assert "make check-env" in sample_section
    assert "make runtime-sample" in sample_section.splitlines()
    assert sample_section.index("make setup") < sample_section.index("make check-env") < sample_section.index("make runtime-sample")
    assert "python3 scripts/run_runtime_sample.py" not in sample_section


def test_operator_shell_doc_uses_repo_managed_orchestrator_help_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    doc = (ROOT / "docs/operator-shell.md").read_text(encoding="utf-8")
    help_section = doc.split("## Canonical help", 1)[1].split("## Common commands", 1)[0]

    assert "orchestrator-help:" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py --help" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py run --help" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py advance --help" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py execute --help" in makefile
    assert "make setup" in help_section
    assert "make check-env" in help_section
    assert "make orchestrator-help" in help_section.splitlines()
    assert help_section.index("make setup") < help_section.index("make check-env") < help_section.index("make orchestrator-help")
    assert "python3 scripts/run_orchestrator.py" not in help_section


def test_operator_shell_common_commands_use_repo_managed_status_target_for_read_only_status() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    doc = (ROOT / "docs/operator-shell.md").read_text(encoding="utf-8")
    common_section = doc.split("## Common commands", 1)[1].split("## Route selection", 1)[0]

    phony_line = next(line for line in makefile.splitlines() if line.startswith(".PHONY:"))
    assert "orchestrator-status" in phony_line
    assert "orchestrator-status:" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py status --task-dir examples/runtime-fixtures/small-doc-task" in makefile
    assert "make setup" in common_section
    assert "make check-env" in common_section
    assert "make orchestrator-status" in common_section.splitlines()
    assert common_section.index("make setup") < common_section.index("make check-env") < common_section.index("make orchestrator-status")
    assert "# Inspect current artifacts and stage pointer. This read-only path is repo-managed." in common_section
    assert "# Fallback entries mutate task artifacts, so keep them explicit operator commands." in common_section
    assert "python3 scripts/run_orchestrator.py status" not in common_section
    assert "python3 scripts/run_orchestrator.py init" in common_section
    assert "python3 scripts/run_orchestrator.py start" in common_section
    assert "python3 scripts/run_orchestrator.py run" in common_section


def test_review_summary_decision_doc_uses_repo_managed_status_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    doc = (ROOT / "docs/review-summary-decision.md").read_text(encoding="utf-8")
    current_surface_section = doc.split("## Why", 1)[1].split("## When to reconsider", 1)[0]

    assert "orchestrator-status:" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py status --task-dir examples/runtime-fixtures/small-doc-task" in makefile
    assert "make setup" in current_surface_section
    assert "make check-env" in current_surface_section
    assert "make orchestrator-status" in current_surface_section.splitlines()
    assert current_surface_section.index("make setup") < current_surface_section.index("make check-env") < current_surface_section.index("make orchestrator-status")
    assert "For non-fixture task directories, operators can still run `status` directly" in current_surface_section
    assert "python3 scripts/run_orchestrator.py status" not in current_surface_section


def test_monitoring_summary_plan_points_users_to_make_targets() -> None:
    plan = (ROOT / "docs/plans/2026-04-24-forgeflow-monitor-summary.md").read_text(encoding="utf-8")
    usage_section = plan.split("### Task 4: Document usage", 1)[1].split("### Task 5: Verify and commit", 1)[0]

    assert "make setup" in usage_section
    assert "make check-env" in usage_section
    assert "make monitor-summary" in usage_section
    assert "make monitor-summary-json" in usage_section
    assert usage_section.index("make setup") < usage_section.index("make check-env") < usage_section.index("make monitor-summary")
    assert usage_section.index("make check-env") < usage_section.index("make monitor-summary-json")
    assert "python3 scripts/forgeflow_monitor.py" not in usage_section


def test_monitoring_summary_plan_json_test_command_uses_repo_managed_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    plan = (ROOT / "docs/plans/2026-04-24-forgeflow-monitor-summary.md").read_text(encoding="utf-8")
    task_section = plan.split("### Task 1: Add failing tests for JSON summary", 1)[1].split(
        "### Task 2: Add failing tests for Markdown and graceful fallback", 1
    )[0]

    assert "monitor-summary-json:" in makefile
    assert "$(VENV_PYTHON) scripts/forgeflow_monitor.py --tasks .forgeflow/tasks --recent 10 --format json" in makefile
    assert "make setup" in task_section
    assert "make check-env" in task_section
    command_lines = [line.strip() for line in task_section.splitlines()]
    assert "make monitor-summary-json" in command_lines
    assert task_section.index("make setup") < task_section.index("make check-env") < task_section.index("make monitor-summary-json")
    assert "python3 scripts/forgeflow_monitor.py" not in task_section


def test_engineering_discipline_plan_uses_repo_managed_help_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    plan = (ROOT / "docs/plans/2026-04-23-engineering-discipline-absorption-plan.md").read_text(encoding="utf-8")
    task_section = plan.split("## P0-3: Tighten operator shell examples", 1)[1].split("# P1 Tasks", 1)[0]
    verification_section = task_section.split("**Verification:**", 1)[1].split("**Exit Condition:**", 1)[0]

    assert "orchestrator-help:" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py --help" in makefile
    assert "$(VENV_PYTHON) scripts/run_orchestrator.py run --help" in makefile
    assert "- Run: `make orchestrator-help`" in verification_section.splitlines()
    assert "python3 scripts/run_orchestrator.py --help" not in verification_section
    assert "python3 scripts/run_orchestrator.py run --help" not in verification_section


def test_claude_hook_recovery_plan_uses_repo_managed_validation_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    plan = (ROOT / "docs/plans/2026-04-24-claude-hook-recovery.md").read_text(encoding="utf-8")
    verification_section = plan.split("**Verification:**", 1)[1].split("**Exit condition:**", 1)[0]

    assert "validate-claude-hooks:" in makefile
    assert "$(VENV_PYTHON) scripts/validate_claude_hooks.py" in makefile
    verification_lines = verification_section.splitlines()
    assert "make validate-claude-hooks" in verification_lines
    assert "make validate" in verification_lines
    assert verification_lines.index("make validate-claude-hooks") < verification_lines.index("make validate")
    assert "python3 scripts/validate_claude_hooks.py" not in verification_section


def test_ci_validation_job_creates_venv_before_make_validate() -> None:
    workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    repo_validation_job = workflow.split("  repo-validation:", 1)[1].split("  generated-drift:", 1)[0]

    assert "make setup" in repo_validation_job
    assert "make check-env" in repo_validation_job
    assert "make validate" in repo_validation_job
    assert repo_validation_job.index("make setup") < repo_validation_job.index("make check-env") < repo_validation_job.index("make validate")
    assert ".venv/bin/python -m pytest -q" in repo_validation_job


def test_ci_has_windows_smoke_job_for_powershell_wrappers() -> None:
    workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")

    assert "windows-smoke:" in workflow
    assert "runs-on: windows-latest" in workflow
    assert ".\\scripts\\setup.ps1" in workflow
    assert ".\\scripts\\validate.ps1" in workflow
    assert ".\\scripts\\run_orchestrator.ps1 init" in workflow


def test_ci_generated_drift_job_uses_repo_managed_venv_before_validation() -> None:
    workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    match = re.search(r"^  generated-drift:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:|\Z)", workflow, re.MULTILINE | re.DOTALL)
    assert match is not None
    generated_drift_job = match.group("body")

    assert "make setup" in generated_drift_job
    assert "make check-env" in generated_drift_job
    assert ".venv/bin/python scripts/validate_generated.py" in generated_drift_job
    assert "python -m pip install" not in generated_drift_job
    assert "python3 scripts/validate_generated.py" not in generated_drift_job
    assert generated_drift_job.index("make setup") < generated_drift_job.index("make check-env") < generated_drift_job.index(".venv/bin/python scripts/validate_generated.py")


def test_install_documents_project_team_preset_installer() -> None:
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

    assert "install_agent_presets.py" in install
    assert "--adapter codex --target /path/to/your-project --profile nextjs" in install


def test_environment_check_reports_missing_dependency_actionably() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_environment.py",
            "--module",
            "definitely_missing_forgeflow_dependency_xyz",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "Missing Python module: definitely_missing_forgeflow_dependency_xyz" in combined
    assert "Run: make setup" in combined


def test_environment_check_passes_for_declared_dependencies() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_environment.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ENVIRONMENT CHECK: PASS" in result.stdout
