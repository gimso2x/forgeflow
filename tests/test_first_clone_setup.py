from __future__ import annotations

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
    assert "$(PYTHON) -m venv $(VENV)" in makefile
    assert "$(VENV_PYTHON) -m pip install" in makefile
    assert "check-env" in makefile
    assert "$(VENV_PYTHON) scripts/check_environment.py" in makefile
    assert "$(VENV_PYTHON) scripts/validate_structure.py" in makefile
    assert "$(VENV_PYTHON) -m pytest tests/test_first_clone_setup.py -q" in makefile


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


def test_readme_quickstart_starts_with_first_clone_setup() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "### 1. Set up dependencies" in readme
    assert "make setup" in readme
    assert "make check-env" in readme
    assert readme.index("## Installation") < readme.index("## What ForgeFlow does")
    assert readme.index("make setup") < readme.index("make validate")
    assert "No hidden local environment is assumed" in readme


def test_install_update_path_rechecks_first_clone_dependencies_before_validation() -> None:
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    update_section = install.split("## 업데이트", 1)[1]

    assert "git -C /path/to/forgeflow pull" in update_section
    assert update_section.index("make -C /path/to/forgeflow setup") < update_section.index("make -C /path/to/forgeflow check-env") < update_section.index("make -C /path/to/forgeflow validate")
    assert "현재 shell 위치와 무관하게" in update_section
    assert "새 dependency가 추가된 release" in update_section


def test_readme_update_path_keeps_make_commands_in_checkout_context() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    update_section = readme.split("### Updating an existing checkout", 1)[1].split("## What ForgeFlow does", 1)[0]

    assert "git -C /path/to/forgeflow pull" in update_section
    assert update_section.index("make -C /path/to/forgeflow setup") < update_section.index("make -C /path/to/forgeflow check-env") < update_section.index("make -C /path/to/forgeflow validate")
    assert "current shell location" in update_section
    assert "new release adds dependencies" in update_section


def test_readme_validation_section_points_fresh_clones_to_setup_gate() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    validation_section = readme.split("## Validation", 1)[1].split("## Naming", 1)[0]

    assert "make validate" in validation_section
    assert "fresh clone" in validation_section
    assert "make setup" in validation_section
    assert "make check-env" in validation_section
    assert validation_section.index("make setup") < validation_section.index("make check-env") < validation_section.index("make validate")


def test_adherence_eval_docs_use_make_target_after_environment_setup() -> None:
    readme = (ROOT / "evals/adherence/README.md").read_text(encoding="utf-8")
    command_block = readme.split("실행 명령:", 1)[1].split("현재 executable 체크:", 1)[0]

    assert "make setup" in command_block
    assert "make check-env" in command_block
    assert "make adherence-evals" in command_block
    assert command_block.index("make setup") < command_block.index("make check-env") < command_block.index("make adherence-evals")
    assert "python3 scripts/run_adherence_evals.py" not in command_block


def test_readme_monitoring_summary_uses_repo_managed_make_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    monitor_section = readme.split("### Local monitoring summary", 1)[1].split("### Local runtime install", 1)[0]

    assert "monitor-summary:" in makefile
    assert "$(VENV_PYTHON) scripts/forgeflow_monitor.py --tasks .forgeflow/tasks --recent 10 --format md" in makefile
    assert "monitor-summary-json:" in makefile
    assert "$(VENV_PYTHON) scripts/forgeflow_monitor.py --tasks .forgeflow/tasks --recent 10 --format json" in makefile
    assert "make setup" in monitor_section
    assert "make check-env" in monitor_section
    monitor_lines = monitor_section.splitlines()
    assert "make monitor-summary" in monitor_lines
    assert "make monitor-summary-json" in monitor_lines
    assert monitor_section.index("make setup") < monitor_section.index("make check-env") < monitor_section.index("make monitor-summary")
    assert monitor_section.index("make check-env") < monitor_section.index("make monitor-summary-json")
    assert "python3 scripts/forgeflow_monitor.py" not in monitor_section


def test_readme_safe_sample_uses_repo_managed_runtime_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    sample_section = readme.split("### 5. Run the safe sample", 1)[1].split("### 6. Start your own task", 1)[0]

    assert "runtime-sample:" in makefile
    assert "$(VENV_PYTHON) scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small" in makefile
    assert "make setup" in sample_section
    assert "make check-env" in sample_section
    assert "make runtime-sample" in sample_section.splitlines()
    assert sample_section.index("make setup") < sample_section.index("make check-env") < sample_section.index("make runtime-sample")
    assert "python3 scripts/run_runtime_sample.py" not in sample_section


def test_readme_operator_shell_uses_repo_managed_runtime_sample_target() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    operator_section = readme.split("## Operator shell", 1)[1].split("## Using ForgeFlow in Codex", 1)[0]

    assert "make setup" in operator_section
    assert "make check-env" in operator_section
    assert "make runtime-sample" in operator_section.splitlines()
    assert operator_section.index("make setup") < operator_section.index("make check-env") < operator_section.index("make runtime-sample")
    assert "python3 scripts/run_runtime_sample.py" not in operator_section


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


def test_ci_validation_job_creates_venv_before_make_validate() -> None:
    workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    repo_validation_job = workflow.split("  repo-validation:", 1)[1].split("  generated-drift:", 1)[0]

    assert "make setup" in repo_validation_job
    assert "make check-env" in repo_validation_job
    assert "make validate" in repo_validation_job
    assert repo_validation_job.index("make setup") < repo_validation_job.index("make check-env") < repo_validation_job.index("make validate")
    assert ".venv/bin/python -m pytest -q" in repo_validation_job


def test_readme_documents_project_team_preset_installer() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "### Project team presets" in readme
    assert "python3 scripts/install_agent_presets.py --adapter claude --target /path/to/your-project --profile nextjs" in readme
    assert "python3 scripts/install_agent_presets.py --adapter codex --target /path/to/your-project --profile nextjs" in readme
    assert "python3 scripts/install_agent_presets.py --adapter cursor --target /path/to/your-project --profile nextjs" in readme
    assert "python3 scripts/install_claude_agent_presets.py --target /path/to/your-project --profile nextjs" in readme
    assert ".claude/agents/forgeflow-coordinator.md" in readme
    assert ".codex/forgeflow/forgeflow-coordinator.md" in readme
    assert ".cursor/rules/forgeflow-coordinator.mdc" in readme
    assert "The installer reads `package.json` and documents only scripts that actually exist." in readme
    assert readme.index("### Manual adapter install") < readme.index("### Project team presets") < readme.index("### Local runtime install")


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
