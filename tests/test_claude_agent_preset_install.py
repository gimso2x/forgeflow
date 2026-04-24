import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/install_claude_agent_presets.py"
GLOBAL_AGENT = Path.home() / ".claude/agents/nextjs-team.json"


def run_installer(target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INSTALLER), "--target", str(target), *extra],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_installs_nextjs_agent_presets_into_project_only(tmp_path):
    target = tmp_path / "sample-next"
    target.mkdir()
    (target / "package.json").write_text(
        json.dumps({"scripts": {"dev": "next dev", "build": "next build", "lint": "eslint"}}, indent=2),
        encoding="utf-8",
    )
    before_global_exists = GLOBAL_AGENT.exists()

    result = run_installer(target, "--profile", "nextjs")

    assert result.returncode == 0, result.stderr
    agents_dir = target / ".claude/agents"
    assert (agents_dir / "forgeflow-coordinator.md").exists()
    assert (agents_dir / "forgeflow-nextjs-worker.md").exists()
    assert (agents_dir / "forgeflow-quality-reviewer.md").exists()
    assert not (Path.home() / ".claude/agents/nextjs-team.json").exists() or before_global_exists

    doc = target / "docs/forgeflow-team-init.md"
    text = doc.read_text(encoding="utf-8")
    assert "npm run lint" in text
    assert "npm run test" not in text
    assert "forgeflow-nextjs-worker.md" in text


def test_installer_rejects_home_claude_agents_target(tmp_path):
    dangerous = tmp_path / ".claude/agents"
    result = run_installer(dangerous, "--profile", "nextjs")

    assert result.returncode != 0
    assert "Refusing to install into a .claude/agents directory" in result.stderr


def test_installer_documents_only_existing_package_scripts(tmp_path):
    target = tmp_path / "app"
    target.mkdir()
    (target / "package.json").write_text(
        json.dumps({"scripts": {"dev": "next dev", "build": "next build"}}, indent=2),
        encoding="utf-8",
    )

    result = run_installer(target, "--profile", "nextjs")

    assert result.returncode == 0, result.stderr
    text = (target / "docs/forgeflow-team-init.md").read_text(encoding="utf-8")
    assert "npm run dev" in text
    assert "npm run build" in text
    assert "npm run lint" not in text
    assert "npm run test" not in text
