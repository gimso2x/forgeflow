import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERIC_INSTALLER = ROOT / "scripts/install_agent_presets.py"
CLAUDE_WRAPPER = ROOT / "scripts/install_claude_agent_presets.py"
GLOBAL_CLAUDE_AGENT = Path.home() / ".claude/agents/nextjs-team.json"
GLOBAL_CODEX_PRESETS = Path.home() / ".codex/forgeflow-presets"


def run_installer(installer: Path, target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(installer), "--target", str(target), *extra],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_package(target: Path, scripts: dict[str, str]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "package.json").write_text(json.dumps({"scripts": scripts}, indent=2), encoding="utf-8")


def test_generic_installer_installs_claude_nextjs_presets_into_project_only(tmp_path):
    target = tmp_path / "sample-next"
    write_package(target, {"dev": "next dev", "build": "next build", "lint": "eslint"})
    before_global_exists = GLOBAL_CLAUDE_AGENT.exists()

    result = run_installer(GENERIC_INSTALLER, target, "--adapter", "claude", "--profile", "nextjs")

    assert result.returncode == 0, result.stderr
    assert (target / ".claude/agents/forgeflow-coordinator.md").exists()
    assert (target / ".claude/agents/forgeflow-nextjs-worker.md").exists()
    assert (target / ".claude/agents/forgeflow-quality-reviewer.md").exists()
    assert not GLOBAL_CLAUDE_AGENT.exists() or before_global_exists

    text = (target / "docs/forgeflow-team-init.md").read_text(encoding="utf-8")
    assert "Adapter: `claude`" in text
    assert "npm run lint" in text
    assert "npm run test" not in text
    assert "forgeflow-nextjs-worker.md" in text


def test_generic_installer_installs_codex_nextjs_presets_into_project_only(tmp_path):
    target = tmp_path / "sample-next"
    write_package(target, {"dev": "next dev", "build": "next build", "lint": "eslint"})
    before_global_exists = GLOBAL_CODEX_PRESETS.exists()

    result = run_installer(GENERIC_INSTALLER, target, "--adapter", "codex", "--profile", "nextjs")

    assert result.returncode == 0, result.stderr
    assert (target / ".codex/forgeflow/forgeflow-coordinator.md").exists()
    assert (target / ".codex/forgeflow/forgeflow-nextjs-worker.md").exists()
    assert (target / ".codex/forgeflow/forgeflow-quality-reviewer.md").exists()
    assert not GLOBAL_CODEX_PRESETS.exists() or before_global_exists

    text = (target / "docs/forgeflow-team-init.md").read_text(encoding="utf-8")
    assert "Adapter: `codex`" in text
    assert "npm run lint" in text
    assert "npm run test" not in text
    assert "forgeflow-nextjs-worker.md" in text


def test_installer_rejects_adapter_config_directory_target(tmp_path):
    claude_target = tmp_path / ".claude/agents"
    codex_target = tmp_path / ".codex/forgeflow"

    claude_result = run_installer(GENERIC_INSTALLER, claude_target, "--adapter", "claude", "--profile", "nextjs")
    codex_result = run_installer(GENERIC_INSTALLER, codex_target, "--adapter", "codex", "--profile", "nextjs")

    assert claude_result.returncode != 0
    assert "pass the project root instead" in claude_result.stderr
    assert codex_result.returncode != 0
    assert "pass the project root instead" in codex_result.stderr


def test_installer_documents_only_existing_package_scripts(tmp_path):
    target = tmp_path / "app"
    write_package(target, {"dev": "next dev", "build": "next build"})

    result = run_installer(GENERIC_INSTALLER, target, "--adapter", "codex", "--profile", "nextjs")

    assert result.returncode == 0, result.stderr
    text = (target / "docs/forgeflow-team-init.md").read_text(encoding="utf-8")
    assert "npm run dev" in text
    assert "npm run build" in text
    assert "npm run lint" not in text
    assert "npm run test" not in text


def test_legacy_claude_installer_wrapper_still_works(tmp_path):
    target = tmp_path / "legacy"
    write_package(target, {"lint": "eslint"})

    result = run_installer(CLAUDE_WRAPPER, target, "--profile", "nextjs")

    assert result.returncode == 0, result.stderr
    assert (target / ".claude/agents/forgeflow-coordinator.md").exists()
    assert "Adapter: `claude`" in (target / "docs/forgeflow-team-init.md").read_text(encoding="utf-8")
