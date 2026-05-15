"""Tests for scripts/release.py and scripts/check_versions.py."""
from __future__ import annotations

import importlib
import json
import sys
import textwrap
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Import helpers – scripts/ is not a package, so we add it to sys.path
# ---------------------------------------------------------------------------

SCRIPTS_DIR = str(Path(__file__).resolve().parents[2] / "scripts")


@pytest.fixture(autouse=True)
def _ensure_scripts_on_path():
    """Make scripts/ importable for every test in this module."""
    if SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, SCRIPTS_DIR)
    yield
    # Cleanup: remove any modules we imported so fixtures don't leak across tests
    for name in list(sys.modules):
        if name in ("release", "check_versions"):
            del sys.modules[name]


def _import_release():
    return importlib.import_module("release")


def _import_check_versions():
    return importlib.import_module("check_versions")


# ===================================================================
# release.py tests
# ===================================================================


class TestValidateVersion:
    """validate_version() accepts valid semver and rejects bad input."""

    def test_valid_semver(self):
        release = _import_release()
        # Should not raise
        release.validate_version("0.1.0")
        release.validate_version("1.0.0")
        release.validate_version("2.3.14")
        release.validate_version("10.20.30")
        release.validate_version("0.0.1")
        release.validate_version("1.0.0-alpha")
        release.validate_version("1.0.0-alpha.1")
        release.validate_version("1.0.0+build.123")

    def test_rejects_leading_v(self):
        release = _import_release()
        with pytest.raises(ValueError, match="plain semver"):
            release.validate_version("v0.1.0")

    def test_rejects_garbage(self):
        release = _import_release()
        with pytest.raises(ValueError):
            release.validate_version("not-a-version")

    def test_rejects_empty(self):
        release = _import_release()
        with pytest.raises(ValueError):
            release.validate_version("")

    def test_rejects_partial(self):
        release = _import_release()
        with pytest.raises(ValueError):
            release.validate_version("1.2")

    def test_rejects_v_prefix_with_prerelease(self):
        release = _import_release()
        with pytest.raises(ValueError):
            release.validate_version("v1.0.0-alpha")


class TestSEMVER_RE:
    """SEMVER_RE matches standard semver patterns."""

    def test_matches_basic(self):
        release = _import_release()
        assert release.SEMVER_RE.match("0.1.0")
        assert release.SEMVER_RE.match("1.0.0")
        assert release.SEMVER_RE.match("99.99.99")

    def test_matches_prerelease(self):
        release = _import_release()
        assert release.SEMVER_RE.match("1.0.0-alpha")
        assert release.SEMVER_RE.match("1.0.0-alpha.1")
        assert release.SEMVER_RE.match("1.0.0-beta.2")

    def test_matches_build_metadata(self):
        release = _import_release()
        # The simplified regex supports one optional [-+...] segment
        assert release.SEMVER_RE.match("1.0.0+build.1")
        assert release.SEMVER_RE.match("1.0.0-alpha")

    def test_rejects_v_prefix(self):
        release = _import_release()
        assert release.SEMVER_RE.match("v0.1.0") is None

    def test_rejects_non_semver(self):
        release = _import_release()
        assert release.SEMVER_RE.match("abc") is None
        assert release.SEMVER_RE.match("1.2") is None
        assert release.SEMVER_RE.match("") is None


class TestUpdateVersions:
    """update_versions() writes new version into all version source files."""

    @staticmethod
    def _setup_mock_repo(tmp_path: Path) -> dict:
        """Create a mock repo tree and return a dict of paths for assertion."""
        # .claude-plugin/plugin.json
        claude_plugin_dir = tmp_path / ".claude-plugin"
        claude_plugin_dir.mkdir()
        claude_plugin_json = claude_plugin_dir / "plugin.json"
        claude_plugin_json.write_text(json.dumps({"name": "claude-plugin", "version": "0.0.1"}))

        # .codex-plugin/plugin.json
        codex_plugin_dir = tmp_path / ".codex-plugin"
        codex_plugin_dir.mkdir()
        codex_plugin_json = codex_plugin_dir / "plugin.json"
        codex_plugin_json.write_text(json.dumps({"name": "codex-plugin", "version": "0.0.1"}))

        # adapters/targets/codex/plugin.json
        codex_adapter_dir = tmp_path / "adapters" / "targets" / "codex"
        codex_adapter_dir.mkdir(parents=True)
        codex_adapter_json = codex_adapter_dir / "plugin.json"
        codex_adapter_json.write_text(json.dumps({"name": "codex-adapter", "version": "0.0.1"}))

        # marketplace.json
        marketplace_json = claude_plugin_dir / "marketplace.json"
        marketplace_json.write_text(json.dumps({"metadata": {"version": "0.0.1"}}))

        # pyproject.toml
        pyproject_toml = tmp_path / "pyproject.toml"
        pyproject_toml.write_text(textwrap.dedent("""\
            [project]
            name = "forgeflow"
            version = "0.0.1"
        """))

        # README.md
        readme_md = tmp_path / "README.md"
        readme_md.write_text("# ForgeFlow\n\n현재 릴리즈는 **v0.0.1**\n")

        return {
            "claude_plugin_json": claude_plugin_json,
            "codex_plugin_json": codex_plugin_json,
            "codex_adapter_json": codex_adapter_json,
            "marketplace_json": marketplace_json,
            "pyproject_toml": pyproject_toml,
            "readme_md": readme_md,
        }

    def test_updates_all_files(self, tmp_path):
        paths = self._setup_mock_repo(tmp_path)
        release = _import_release()

        new_version = "1.2.3"

        # Monkeypatch module-level constants to point at tmp_path
        release.ROOT = tmp_path
        release.CLAUDE_PLUGIN_JSON = paths["claude_plugin_json"]
        release.CODEX_PLUGIN_JSON = paths["codex_plugin_json"]
        release.CODEX_ADAPTER_PLUGIN_JSON = paths["codex_adapter_json"]
        release.MARKETPLACE_JSON = paths["marketplace_json"]
        release.PYPROJECT_TOML = paths["pyproject_toml"]
        release.README_MD = paths["readme_md"]
        release.PLUGIN_VERSION_JSONS = [
            paths["claude_plugin_json"],
            paths["codex_plugin_json"],
            paths["codex_adapter_json"],
        ]

        release.update_versions(new_version)

        # Check plugin JSONs
        for key in ("claude_plugin_json", "codex_plugin_json", "codex_adapter_json"):
            data = json.loads(paths[key].read_text())
            assert data["version"] == new_version, f"{key} not updated"

        # Check marketplace.json
        marketplace = json.loads(paths["marketplace_json"].read_text())
        assert marketplace["metadata"]["version"] == new_version

        # Check pyproject.toml
        toml_text = paths["pyproject_toml"].read_text()
        assert f'version = "{new_version}"' in toml_text

        # Check README.md
        readme_text = paths["readme_md"].read_text()
        assert f"v{new_version}" in readme_text
        assert "v0.0.1" not in readme_text


class TestReleaseFilesToStage:
    """release_files_to_stage() returns expected file list."""

    def test_returns_expected_files(self, tmp_path):
        # Create mock files so .exists() works for README
        claude_dir = tmp_path / ".claude-plugin"
        claude_dir.mkdir()
        codex_dir = tmp_path / ".codex-plugin"
        codex_dir.mkdir()
        codex_adapter_dir = tmp_path / "adapters" / "targets" / "codex"
        codex_adapter_dir.mkdir(parents=True)

        claude_plugin = claude_dir / "plugin.json"
        claude_plugin.write_text("{}")
        codex_plugin = codex_dir / "plugin.json"
        codex_plugin.write_text("{}")
        codex_adapter_plugin = codex_adapter_dir / "plugin.json"
        codex_adapter_plugin.write_text("{}")
        marketplace = claude_dir / "marketplace.json"
        marketplace.write_text("{}")
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("")
        readme = tmp_path / "README.md"
        readme.write_text("")

        release = _import_release()
        release.ROOT = tmp_path
        release.CLAUDE_PLUGIN_JSON = claude_plugin
        release.CODEX_PLUGIN_JSON = codex_plugin
        release.CODEX_ADAPTER_PLUGIN_JSON = codex_adapter_plugin
        release.MARKETPLACE_JSON = marketplace
        release.PYPROJECT_TOML = pyproject
        release.README_MD = readme
        release.SUPPORTED_PLUGIN_MANIFESTS = [claude_plugin, codex_plugin]

        result = release.release_files_to_stage()

        # Should include all version source files
        result_str = " ".join(result)
        assert "plugin.json" in result_str
        assert "pyproject.toml" in result_str
        assert "README.md" in result_str
        assert "marketplace.json" in result_str

    def test_includes_pyproject_and_readme(self, tmp_path):
        claude_dir = tmp_path / ".claude-plugin"
        claude_dir.mkdir()
        codex_dir = tmp_path / ".codex-plugin"
        codex_dir.mkdir()
        codex_adapter_dir = tmp_path / "adapters" / "targets" / "codex"
        codex_adapter_dir.mkdir(parents=True)

        claude_plugin = claude_dir / "plugin.json"
        claude_plugin.write_text("{}")
        codex_plugin = codex_dir / "plugin.json"
        codex_plugin.write_text("{}")
        codex_adapter_plugin = codex_adapter_dir / "plugin.json"
        codex_adapter_plugin.write_text("{}")
        marketplace = claude_dir / "marketplace.json"
        marketplace.write_text("{}")
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("")
        readme = tmp_path / "README.md"
        readme.write_text("")

        release = _import_release()
        release.ROOT = tmp_path
        release.CLAUDE_PLUGIN_JSON = claude_plugin
        release.CODEX_PLUGIN_JSON = codex_plugin
        release.CODEX_ADAPTER_PLUGIN_JSON = codex_adapter_plugin
        release.MARKETPLACE_JSON = marketplace
        release.PYPROJECT_TOML = pyproject
        release.README_MD = readme
        release.SUPPORTED_PLUGIN_MANIFESTS = [claude_plugin, codex_plugin]

        result = release.release_files_to_stage()
        assert "pyproject.toml" in result
        assert "README.md" in result


class TestReleasePlan:
    """release_plan() includes pyproject.toml and README in the plan text."""

    def test_mentions_pyproject(self):
        release = _import_release()
        plan = release.release_plan("2.0.0")
        assert "pyproject.toml" in plan

    def test_mentions_readme(self):
        release = _import_release()
        plan = release.release_plan("2.0.0")
        assert "README" in plan

    def test_includes_version(self):
        release = _import_release()
        plan = release.release_plan("3.1.4")
        assert "v3.1.4" in plan

    def test_mentions_plugin_manifests(self):
        release = _import_release()
        plan = release.release_plan("1.0.0")
        assert "plugin" in plan.lower()
        assert "marketplace" in plan.lower()

    def test_mentions_git_commit_and_tag(self):
        release = _import_release()
        plan = release.release_plan("1.0.0")
        assert "commit" in plan.lower()
        assert "tag" in plan.lower()


# ===================================================================
# check_versions.py tests
# ===================================================================


class TestReadVersionJson:
    """read_version_json() extracts version from a JSON file."""

    def test_reads_version(self, tmp_path):
        cv = _import_check_versions()
        p = tmp_path / "plugin.json"
        p.write_text(json.dumps({"version": "1.2.3", "name": "test"}))
        assert cv.read_version_json(p) == "1.2.3"


class TestReadVersionPyproject:
    """read_version_pyproject() extracts version from pyproject.toml."""

    def test_reads_version(self, tmp_path):
        cv = _import_check_versions()
        p = tmp_path / "pyproject.toml"
        p.write_text('[project]\nname = "foo"\nversion = "4.5.6"\n')
        assert cv.read_version_pyproject(p) == "4.5.6"

    def test_returns_not_found_when_missing(self, tmp_path):
        cv = _import_check_versions()
        p = tmp_path / "pyproject.toml"
        p.write_text('[project]\nname = "foo"\n')
        assert cv.read_version_pyproject(p) == "<not found>"


class TestReadVersionReadme:
    """read_version_readme() extracts version from the Korean release line."""

    def test_reads_version(self, tmp_path):
        cv = _import_check_versions()
        p = tmp_path / "README.md"
        p.write_text("# ForgeFlow\n\n현재 릴리즈는 **v7.8.9**\n")
        assert cv.read_version_readme(p) == "7.8.9"

    def test_returns_none_when_absent(self, tmp_path):
        cv = _import_check_versions()
        p = tmp_path / "README.md"
        p.write_text("# ForgeFlow\nNo version info here.\n")
        assert cv.read_version_readme(p) is None


class TestCheckVersionsMain:
    """main() exits 0 when all versions match, exits 1 on drift."""

    @staticmethod
    def _setup_mock_repo(tmp_path: Path, version: str, drift_file: str | None = None):
        """Create a mock repo and monkeypatch check_versions module paths.

        If drift_file is set, that file gets a different version to force drift.
        """
        cv = _import_check_versions()

        claude_dir = tmp_path / ".claude-plugin"
        claude_dir.mkdir()
        codex_dir = tmp_path / ".codex-plugin"
        codex_dir.mkdir()
        codex_adapter_dir = tmp_path / "adapters" / "targets" / "codex"
        codex_adapter_dir.mkdir(parents=True)

        claude_plugin = claude_dir / "plugin.json"
        codex_plugin = codex_dir / "plugin.json"
        codex_adapter_plugin = codex_adapter_dir / "plugin.json"

        for p in (claude_plugin, codex_plugin, codex_adapter_plugin):
            v = "0.0.0" if (drift_file and str(p) == drift_file) else version
            p.write_text(json.dumps({"version": v}))

        marketplace = claude_dir / "marketplace.json"
        mv = "0.0.0" if drift_file == "marketplace" else version
        marketplace.write_text(json.dumps({"metadata": {"version": mv}}))

        gemini_extension = tmp_path / "gemini-extension.json"
        gv = "0.0.0" if drift_file == "gemini-extension" else version
        gemini_extension.write_text(json.dumps({"version": gv}))

        pyproject = tmp_path / "pyproject.toml"
        pv = "0.0.0" if drift_file == "pyproject" else version
        pyproject.write_text(f'[project]\nname = "forgeflow"\nversion = "{pv}"\n')

        readme = tmp_path / "README.md"
        rv = "0.0.0" if drift_file == "readme" else version
        readme.write_text(f"# ForgeFlow\n\n현재 릴리즈는 **v{rv}**\n")

        # Monkeypatch module paths
        cv.ROOT = tmp_path
        cv.CLAUDE_PLUGIN_JSON = claude_plugin
        cv.CODEX_PLUGIN_JSON = codex_plugin
        cv.CODEX_ADAPTER_PLUGIN_JSON = codex_adapter_plugin
        cv.GEMINI_EXTENSION_JSON = gemini_extension
        cv.MARKETPLACE_JSON = marketplace
        cv.PYPROJECT_TOML = pyproject
        cv.README_MD = readme

        return cv

    def test_all_matching_exits_zero(self, tmp_path):
        cv = self._setup_mock_repo(tmp_path, "1.0.0")
        assert cv.main() == 0

    def test_version_drift_exits_one(self, tmp_path):
        cv = self._setup_mock_repo(tmp_path, "1.0.0", drift_file="pyproject")
        assert cv.main() == 1

    def test_drift_reports_difference(self, tmp_path, capsys):
        cv = self._setup_mock_repo(tmp_path, "1.0.0", drift_file="pyproject")
        cv.main()
        captured = capsys.readouterr()
        assert "drift" in captured.out.lower()

    def test_readme_drift_exits_one(self, tmp_path):
        cv = self._setup_mock_repo(tmp_path, "2.0.0", drift_file="readme")
        assert cv.main() == 1

    def test_marketplace_drift_exits_one(self, tmp_path):
        cv = self._setup_mock_repo(tmp_path, "2.0.0", drift_file="marketplace")
        assert cv.main() == 1
