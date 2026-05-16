import subprocess
import sys
import tomllib
from pathlib import Path

from tests.runtime.cli_helpers import ROOT


def test_pyproject_exposes_forgeflow_console_scripts() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    project = data["project"]
    assert project["name"] == "forgeflow-runtime"
    assert project["requires-python"] == ">=3.11"
    scripts = project["scripts"]
    assert scripts["forgeflow"] == "scripts.run_orchestrator:main"
    assert scripts["forgeflow-runtime"] == "scripts.run_orchestrator:main"


def test_console_script_target_can_run_orchestrator_help() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "from scripts.run_orchestrator import main; raise SystemExit(main())", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ForgeFlow stage-machine orchestrator" in result.stdout
    assert "execute" in result.stdout
    assert "exec-stage" in result.stdout


def test_editable_install_exposes_forgeflow_entrypoint(tmp_path: Path) -> None:
    venv_dir = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    python = venv_dir / "bin" / "python"
    forgeflow = venv_dir / "bin" / "forgeflow"

    install = subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "-e",
            str(ROOT),
            "--no-build-isolation",
            "--disable-pip-version-check",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert install.returncode == 0, install.stderr
    assert forgeflow.exists()

    result = subprocess.run(
        [str(forgeflow), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ForgeFlow stage-machine orchestrator" in result.stdout
    assert "Operator shell examples:" in result.stdout
