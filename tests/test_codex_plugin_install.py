import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_codex_plugin.py"


def run_installer(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            "--plugin-parent",
            str(tmp_path / "plugins"),
            "--marketplace-path",
            str(tmp_path / ".agents/plugins/marketplace.json"),
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_codex_plugin_installer_copies_plugin_and_writes_marketplace(tmp_path):
    result = run_installer(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "/forgeflow:clarify" in result.stdout
    assert "/forgeflow:init" in result.stdout
    plugin_root = tmp_path / "plugins" / "forgeflow"
    marketplace_path = tmp_path / ".agents/plugins/marketplace.json"
    assert (plugin_root / ".codex-plugin/plugin.json").exists()
    assert (plugin_root / "skills/forgeflow/SKILL.md").exists()
    assert not (plugin_root / ".git").exists()
    assert not (plugin_root / ".venv").exists()

    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    entry = marketplace["plugins"][0]
    assert entry["name"] == "forgeflow"
    assert entry["source"] == {"source": "local", "path": "./plugins/forgeflow"}
    assert entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert entry["category"] == "Coding"


def test_codex_plugin_installer_refuses_existing_copy_without_force(tmp_path):
    first = run_installer(tmp_path)
    second = run_installer(tmp_path)

    assert first.returncode == 0, first.stderr
    assert second.returncode != 0
    assert "already exists" in second.stderr


def test_codex_plugin_installer_force_replaces_copy_and_marketplace_entry(tmp_path):
    first = run_installer(tmp_path)
    marketplace_path = tmp_path / ".agents/plugins/marketplace.json"
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    marketplace["plugins"][0]["category"] = "Stale"
    marketplace_path.write_text(json.dumps(marketplace, indent=2) + "\n", encoding="utf-8")

    second = run_installer(tmp_path, "--force")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    assert marketplace["plugins"][0]["category"] == "Coding"


def test_codex_plugin_installer_dry_run_reports_force_overwrites_without_writing(tmp_path):
    first = run_installer(tmp_path)
    marketplace_path = tmp_path / ".agents/plugins/marketplace.json"
    marketplace_before = marketplace_path.read_text(encoding="utf-8")
    sentinel = tmp_path / "plugins" / "forgeflow" / "LOCAL_CUSTOMIZATION.md"
    sentinel.write_text("keep me\n", encoding="utf-8")

    result = run_installer(tmp_path, "--dry-run")

    assert first.returncode == 0, first.stderr
    assert result.returncode == 0, result.stderr
    assert "DRY-RUN: no files were changed" in result.stdout
    assert "would fail: target exists" in result.stdout
    assert "re-run with --dry-run --force" in result.stdout
    assert sentinel.exists()
    assert marketplace_path.read_text(encoding="utf-8") == marketplace_before

    result = run_installer(tmp_path, "--force", "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "DRY-RUN: no files were changed" in result.stdout
    assert "would replace plugin copy" in result.stdout
    assert "overwrite scope" in result.stdout
    assert "--force would remove" in result.stdout
    assert sentinel.exists()
    assert marketplace_path.read_text(encoding="utf-8") == marketplace_before


def test_codex_plugin_installer_can_update_marketplace_without_copy(tmp_path):
    plugin_root = tmp_path / "plugins" / "forgeflow"
    (plugin_root / ".codex-plugin").mkdir(parents=True)
    (plugin_root / "skills").mkdir()
    (plugin_root / ".codex-plugin/plugin.json").write_text('{"name": "forgeflow"}\n', encoding="utf-8")

    result = run_installer(tmp_path, "--skip-copy")

    assert result.returncode == 0, result.stderr
    marketplace = json.loads((tmp_path / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
    assert marketplace["plugins"][0]["name"] == "forgeflow"
