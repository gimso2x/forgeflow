import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release.py"
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CODEX = ROOT / ".codex-plugin" / "plugin.json"
CURSOR = ROOT / ".cursor-plugin" / "plugin.json"


def run_release(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def test_release_script_dry_run_prints_ordered_checks_without_mutating_versions():
    before_plugin = json.loads(PLUGIN.read_text())
    before_marketplace = json.loads(MARKETPLACE.read_text())

    result = run_release("0.1.14", "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "Release plan for v0.1.14" in result.stdout
    assert "1. update plugin manifests version to 0.1.14" in result.stdout
    assert "2. update .claude-plugin/marketplace.json metadata.version to 0.1.14" in result.stdout
    assert "3. run pytest -q" in result.stdout
    assert "4. run make validate" in result.stdout
    assert "5. run make smoke-claude-plugin" in result.stdout
    assert "6. create git commit: chore: release v0.1.14" in result.stdout
    assert "7. create annotated tag: v0.1.14" in result.stdout
    assert json.loads(PLUGIN.read_text()) == before_plugin
    assert json.loads(MARKETPLACE.read_text()) == before_marketplace


def test_release_script_rejects_non_semver_versions():
    result = run_release("v0.1.14", "--dry-run")

    assert result.returncode != 0
    assert "version must be plain semver" in result.stderr


def test_release_script_can_update_versions_only_and_write_release_notes(tmp_path):
    notes = tmp_path / "notes.md"
    original_plugin = PLUGIN.read_text()
    original_marketplace = MARKETPLACE.read_text()
    original_codex = CODEX.read_text()
    original_cursor = CURSOR.read_text()

    try:
        result = run_release("0.1.14", "--write-only", "--notes-out", str(notes))

        assert result.returncode == 0, result.stderr
        assert json.loads(PLUGIN.read_text())["version"] == "0.1.14"
        assert json.loads(MARKETPLACE.read_text())["metadata"]["version"] == "0.1.14"
        assert json.loads(CODEX.read_text())["version"] == "0.1.14"
        assert json.loads(CURSOR.read_text())["version"] == "0.1.14"
        assert "## v0.1.14" in notes.read_text()
        assert "pytest -q" in notes.read_text()
        assert "make validate" in notes.read_text()
    finally:
        PLUGIN.write_text(original_plugin)
        MARKETPLACE.write_text(original_marketplace)
        CODEX.write_text(original_codex)
        CURSOR.write_text(original_cursor)
