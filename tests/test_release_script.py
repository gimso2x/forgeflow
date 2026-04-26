import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release.py"
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CODEX = ROOT / ".codex-plugin" / "plugin.json"


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
    assert "3. run scripts/check_plugin_versions.py" in result.stdout
    assert "4. run pytest -q" in result.stdout
    assert "5. run make validate" in result.stdout
    assert "6. run make smoke-claude-plugin" in result.stdout
    assert "7. create git commit: chore: release v0.1.14" in result.stdout
    assert "8. create annotated tag: v0.1.14" in result.stdout
    assert "git commit -am" not in SCRIPT.read_text(encoding="utf-8")
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

    try:
        result = run_release("0.1.14", "--write-only", "--notes-out", str(notes))

        assert result.returncode == 0, result.stderr
        assert json.loads(PLUGIN.read_text())["version"] == "0.1.14"
        assert json.loads(MARKETPLACE.read_text())["metadata"]["version"] == "0.1.14"
        assert json.loads(CODEX.read_text())["version"] == "0.1.14"
        assert "## v0.1.14" in notes.read_text()
        assert "pytest -q" in notes.read_text()
        assert "make validate" in notes.read_text()
    finally:
        PLUGIN.write_text(original_plugin)
        MARKETPLACE.write_text(original_marketplace)
        CODEX.write_text(original_codex)


def test_release_script_declares_supported_plugin_manifests_once():
    spec = importlib.util.spec_from_file_location("release_script", SCRIPT)
    assert spec and spec.loader
    release_script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release_script)

    paths = [str(path.relative_to(ROOT)) for path in release_script.SUPPORTED_PLUGIN_MANIFESTS]

    assert paths == [".claude-plugin/plugin.json", ".codex-plugin/plugin.json"]


def test_release_script_stages_only_supported_plugin_manifests():
    spec = importlib.util.spec_from_file_location("release_script", SCRIPT)
    assert spec and spec.loader
    release_script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release_script)

    paths = release_script.release_files_to_stage()

    assert ".claude-plugin/plugin.json" in paths
    assert ".codex-plugin/plugin.json" in paths
    assert ".cursor-plugin/plugin.json" not in paths


def test_release_script_rejects_preexisting_staged_changes(tmp_path):
    marker = ROOT / "release-unrelated-staged.tmp"
    try:
        marker.write_text("do not ship me", encoding="utf-8")
        subprocess.run(["git", "add", str(marker.relative_to(ROOT))], cwd=ROOT, check=True)

        result = run_release("0.1.14", "--skip-checks", "--no-tag")

        assert result.returncode != 0
        assert "pre-existing staged changes" in result.stderr
    finally:
        subprocess.run(["git", "reset", "--", str(marker.relative_to(ROOT))], cwd=ROOT, check=False, capture_output=True)
        marker.unlink(missing_ok=True)


def test_release_script_stages_relative_notes_out_path(tmp_path):
    spec = importlib.util.spec_from_file_location("release_script", SCRIPT)
    assert spec and spec.loader
    release_script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release_script)

    paths = release_script.release_files_to_stage(Path("release-notes-test.md"))

    assert "release-notes-test.md" in paths
