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
    assert "scripts/check_environment.py" in makefile


def test_readme_quickstart_starts_with_first_clone_setup() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "### 1. Set up dependencies" in readme
    assert "make setup" in readme
    assert "make check-env" in readme
    assert readme.index("## Installation") < readme.index("## What ForgeFlow does")
    assert readme.index("make setup") < readme.index("make validate")
    assert "No hidden local environment is assumed" in readme


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
