import argparse
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


def load_release_script():
    spec = importlib.util.spec_from_file_location("release_script", SCRIPT)
    assert spec and spec.loader
    release_script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release_script)
    return release_script


def test_release_script_dry_run_prints_ordered_checks_without_mutating_versions():
    before_plugin = json.loads(PLUGIN.read_text())
    before_marketplace = json.loads(MARKETPLACE.read_text())

    result = run_release("0.1.14", "--dry-run", "--allow-docs-only")

    assert result.returncode == 0, result.stderr
    assert "Release plan for v0.1.14" in result.stdout
    assert "1. update plugin manifests version to 0.1.14" in result.stdout
    assert "2. update .claude-plugin/marketplace.json metadata.version to 0.1.14" in result.stdout
    assert "3. run python scripts/check_plugin_versions.py" in result.stdout
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
        result = run_release("0.1.14", "--write-only", "--notes-out", str(notes), "--allow-docs-only")

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
    release_script = load_release_script()

    paths = [str(path.relative_to(ROOT)) for path in release_script.SUPPORTED_PLUGIN_MANIFESTS]

    assert paths == [".claude-plugin/plugin.json", ".codex-plugin/plugin.json"]


def test_release_script_stages_only_supported_plugin_manifests():
    release_script = load_release_script()

    paths = release_script.release_files_to_stage()

    assert ".claude-plugin/plugin.json" in paths
    assert ".codex-plugin/plugin.json" in paths
    assert ".claude-plugin/marketplace.json" in paths
    assert len(paths) == 3


def test_release_script_rejects_preexisting_staged_changes(tmp_path):
    marker = ROOT / "release-unrelated-staged.tmp"
    try:
        marker.write_text("do not ship me", encoding="utf-8")
        subprocess.run(["git", "add", str(marker.relative_to(ROOT))], cwd=ROOT, check=True)

        result = run_release("0.1.14", "--skip-checks", "--no-tag", "--allow-docs-only")

        assert result.returncode != 0
        assert "pre-existing staged changes" in result.stderr
    finally:
        subprocess.run(["git", "reset", "--", str(marker.relative_to(ROOT))], cwd=ROOT, check=False, capture_output=True)
        marker.unlink(missing_ok=True)


def test_release_script_stages_relative_notes_out_path(tmp_path):
    release_script = load_release_script()

    paths = release_script.release_files_to_stage(Path("release-notes-test.md"))

    assert "release-notes-test.md" in paths


def test_release_script_classifies_docs_only_paths():
    release_script = load_release_script()

    assert release_script.is_docs_only_path(Path("docs/release.md")) is True
    assert release_script.is_docs_only_path(Path("README.md")) is True
    assert release_script.is_docs_only_path(Path("src/app.py")) is False


def test_release_script_rejects_docs_only_release_without_override(monkeypatch):
    release_script = load_release_script()
    args = argparse.Namespace(
        version="0.1.14",
        dry_run=False,
        write_only=False,
        skip_checks=False,
        no_commit=False,
        no_tag=False,
        notes_out=None,
        allow_docs_only=False,
    )

    monkeypatch.setattr(release_script, "parse_args", lambda: args)
    monkeypatch.setattr(release_script, "latest_release_tag", lambda: "v0.1.13")
    monkeypatch.setattr(release_script, "changed_paths_since", lambda tag: [Path("docs/release-policy.md")])

    result = release_script.main()

    assert result == 2


def test_release_script_allows_docs_only_release_with_override(monkeypatch):
    release_script = load_release_script()
    args = argparse.Namespace(
        version="0.1.14",
        dry_run=True,
        write_only=False,
        skip_checks=False,
        no_commit=False,
        no_tag=False,
        notes_out=None,
        allow_docs_only=True,
    )

    monkeypatch.setattr(release_script, "parse_args", lambda: args)
    monkeypatch.setattr(release_script, "latest_release_tag", lambda: "v0.1.13")
    monkeypatch.setattr(release_script, "changed_paths_since", lambda tag: [Path("docs/release-policy.md")])

    result = release_script.main()

    assert result == 0
