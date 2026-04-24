import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERIC_INSTALLER = ROOT / "scripts/install_agent_presets.py"
CLAUDE_WRAPPER = ROOT / "scripts/install_claude_agent_presets.py"
GLOBAL_CLAUDE_AGENT = Path.home() / ".claude/agents/nextjs-team.json"
GLOBAL_CODEX_PRESETS = Path.home() / ".codex/forgeflow-presets"
GLOBAL_CURSOR_RULES = Path.home() / ".cursor/rules"


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


def test_generic_installer_installs_cursor_nextjs_rules_into_project_only(tmp_path):
    target = tmp_path / "sample-next"
    write_package(target, {"dev": "next dev", "build": "next build", "lint": "eslint"})
    before_global_exists = GLOBAL_CURSOR_RULES.exists()

    result = run_installer(GENERIC_INSTALLER, target, "--adapter", "cursor", "--profile", "nextjs")

    assert result.returncode == 0, result.stderr
    assert (target / ".cursor/rules/forgeflow-coordinator.mdc").exists()
    assert (target / ".cursor/rules/forgeflow-nextjs-worker.mdc").exists()
    assert (target / ".cursor/rules/forgeflow-quality-reviewer.mdc").exists()
    assert not GLOBAL_CURSOR_RULES.exists() or before_global_exists

    text = (target / "docs/forgeflow-team-init.md").read_text(encoding="utf-8")
    assert "Adapter: `cursor`" in text
    assert "npm run lint" in text
    assert "npm run test" not in text
    assert "forgeflow-nextjs-worker.mdc" in text


def test_installer_rejects_adapter_config_directory_target(tmp_path):
    claude_target = tmp_path / ".claude/agents"
    codex_target = tmp_path / ".codex/forgeflow"
    cursor_target = tmp_path / ".cursor/rules"

    claude_result = run_installer(GENERIC_INSTALLER, claude_target, "--adapter", "claude", "--profile", "nextjs")
    codex_result = run_installer(GENERIC_INSTALLER, codex_target, "--adapter", "codex", "--profile", "nextjs")
    cursor_result = run_installer(GENERIC_INSTALLER, cursor_target, "--adapter", "cursor", "--profile", "nextjs")

    assert claude_result.returncode != 0
    assert "pass the project root instead" in claude_result.stderr
    assert codex_result.returncode != 0
    assert "pass the project root instead" in codex_result.stderr
    assert cursor_result.returncode != 0
    assert "pass the project root instead" in cursor_result.stderr


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



def test_installer_can_generate_starter_docs_without_placeholders(tmp_path):
    target = tmp_path / "app"
    write_package(target, {"dev": "next dev", "build": "next build", "lint": "eslint", "test": "vitest"})

    result = run_installer(
        GENERIC_INSTALLER,
        target,
        "--adapter",
        "claude",
        "--profile",
        "nextjs",
        "--with-starter-docs",
    )

    assert result.returncode == 0, result.stderr
    for name in ["PRD.md", "ARCHITECTURE.md", "ADR.md", "UI_GUIDE.md"]:
        doc = target / "docs" / name
        assert doc.exists(), name
        text = doc.read_text(encoding="utf-8")
        assert "ForgeFlow" in text
        assert "{{" not in text
        assert "}}" not in text
        assert "{프로젝트명}" not in text

    init = (target / "docs/forgeflow-team-init.md").read_text(encoding="utf-8")
    assert "## Starter docs" in init
    assert "docs/PRD.md" in init
    assert "docs/ARCHITECTURE.md" in init


def test_installer_does_not_overwrite_existing_starter_docs(tmp_path):
    target = tmp_path / "app"
    write_package(target, {"build": "next build"})
    existing = target / "docs" / "PRD.md"
    existing.parent.mkdir(parents=True)
    existing.write_text("# Existing product doc\nDo not overwrite this.", encoding="utf-8")

    result = run_installer(
        GENERIC_INSTALLER,
        target,
        "--adapter",
        "codex",
        "--profile",
        "nextjs",
        "--with-starter-docs",
    )

    assert result.returncode == 0, result.stderr
    assert existing.read_text(encoding="utf-8") == "# Existing product doc\nDo not overwrite this."
    assert (target / "docs/ARCHITECTURE.md").exists()


def test_team_init_document_exposes_prompt_and_review_contract(tmp_path):
    target = tmp_path / "app"
    write_package(target, {"build": "next build", "lint": "eslint", "test": "vitest run"})

    result = run_installer(
        GENERIC_INSTALLER,
        target,
        "--adapter",
        "cursor",
        "--profile",
        "nextjs",
        "--with-starter-docs",
    )

    assert result.returncode == 0, result.stderr
    text = (target / "docs/forgeflow-team-init.md").read_text(encoding="utf-8")
    assert "## Active role prompts" in text
    assert "forgeflow-coordinator" in text
    assert "forgeflow-nextjs-worker" in text
    assert "forgeflow-quality-reviewer" in text
    assert "## Review contract" in text
    assert "independent quality review" in text
    assert "## Failure handling" in text
    assert "## Recommended first run" in text
    assert "/forgeflow:clarify" in text



def test_claude_installer_can_install_basic_safety_hook_bundle(tmp_path):
    target = tmp_path / "app"
    write_package(target, {"build": "next build"})

    result = run_installer(
        GENERIC_INSTALLER,
        target,
        "--adapter",
        "claude",
        "--profile",
        "nextjs",
        "--hook-bundles",
        "basic-safety",
    )

    assert result.returncode == 0, result.stderr
    assert (target / ".claude/hooks/forgeflow/basic_safety_guard.py").exists()
    settings = json.loads((target / ".claude/settings.json").read_text(encoding="utf-8"))
    pretool = settings["hooks"]["PreToolUse"][0]
    assert pretool["matcher"] == "Bash"
    assert "basic_safety_guard.py" in pretool["hooks"][0]["command"]

    init = (target / "docs/forgeflow-team-init.md").read_text(encoding="utf-8")
    assert "## Installed hook/safety bundles" in init
    assert "basic-safety" in init
    assert "project-local opt-in" in init


def test_hook_bundles_are_claude_only(tmp_path):
    target = tmp_path / "app"
    write_package(target, {"build": "next build"})

    result = run_installer(
        GENERIC_INSTALLER,
        target,
        "--adapter",
        "codex",
        "--profile",
        "nextjs",
        "--hook-bundles",
        "basic-safety",
    )

    assert result.returncode != 0
    assert "Claude adapter only" in result.stderr


def test_installer_does_not_install_hooks_by_default(tmp_path):
    target = tmp_path / "app"
    write_package(target, {"build": "next build"})

    result = run_installer(GENERIC_INSTALLER, target, "--adapter", "claude", "--profile", "nextjs")

    assert result.returncode == 0, result.stderr
    assert not (target / ".claude/settings.json").exists()
    assert not (target / ".claude/hooks/forgeflow/basic_safety_guard.py").exists()
