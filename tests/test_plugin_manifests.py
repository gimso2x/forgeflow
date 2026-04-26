import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / ".claude-plugin" / "plugin.json"
CODEX = ROOT / ".codex-plugin" / "plugin.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_supported_plugin_manifests_exist_and_match_core_metadata():
    claude = load(CLAUDE)
    codex = load(CODEX)

    for manifest in (codex,):
        assert manifest["name"] == "forgeflow"
        assert manifest["version"] == claude["version"]
        assert manifest["repository"] == claude["repository"]
        assert manifest["license"] == claude["license"]
        assert "artifact" in manifest["description"].lower()
        assert "codex" in manifest["keywords"]


def test_cursor_plugin_manifest_is_not_supported():
    assert not (ROOT / ".cursor-plugin" / "plugin.json").exists()


def test_supported_plugin_metadata_does_not_advertise_cursor_plugin_support():
    marketplace = load(ROOT / ".claude-plugin" / "marketplace.json")
    manifests = [load(CLAUDE), load(CODEX)]

    for manifest in manifests:
        assert "cursor" not in manifest["keywords"]
    for plugin in marketplace["plugins"]:
        assert "cursor" not in plugin.get("tags", [])


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    scripts_dir = str(path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_plugin_version_check_reuses_release_supported_manifest_list():
    release = _load_script("release")
    checker = _load_script("check_plugin_versions")

    assert checker.SUPPORTED_PLUGIN_MANIFESTS is release.SUPPORTED_PLUGIN_MANIFESTS


def test_plugin_version_check_reports_missing_supported_manifest():
    checker = _load_script("check_plugin_versions")

    errors = checker.supported_manifest_errors([ROOT / ".codex-plugin" / "missing-plugin.json"])

    assert errors == [".codex-plugin/missing-plugin.json: supported plugin manifest is missing"]


def test_plugin_version_check_reports_supported_manifest_homepage_drift():
    checker = _load_script("check_plugin_versions")
    manifests = {
        Path(".claude-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
        Path(".codex-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "homepage": "https://example.invalid/stale",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
    }
    marketplace = {"name": "forgeflow", "metadata": {"version": "0.1.16"}, "plugins": [{"name": "forgeflow"}]}

    errors = checker.plugin_metadata_errors(manifests, marketplace)

    assert errors == [
        ".codex-plugin/plugin.json: homepage 'https://example.invalid/stale' != 'https://github.com/gimso2x/forgeflow'"
    ]


def test_plugin_version_check_reports_unsupported_cursor_manifest_if_it_reappears(tmp_path):
    checker = _load_script("check_plugin_versions")
    unsupported = tmp_path / ".cursor-plugin" / "plugin.json"
    unsupported.parent.mkdir()
    unsupported.write_text('{"name": "forgeflow"}\n', encoding="utf-8")

    errors = checker.unsupported_manifest_errors([unsupported])

    assert errors == [f"{unsupported}: unsupported plugin manifest must be removed"]


def test_plugin_version_check_reports_marketplace_name_drift():
    checker = _load_script("check_plugin_versions")
    manifests = {
        Path(".claude-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
        Path(".codex-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
    }
    marketplace = {
        "name": "forgeflow-stale",
        "metadata": {"version": "0.1.16"},
        "plugins": [{"name": "forgeflow-stale"}],
    }

    errors = checker.plugin_metadata_errors(manifests, marketplace)

    assert errors == [
        ".claude-plugin/marketplace.json: name 'forgeflow-stale' != 'forgeflow'",
        ".claude-plugin/marketplace.json: plugins[0].name 'forgeflow-stale' != 'forgeflow'",
    ]


def test_plugin_version_check_reports_marketplace_owner_url_drift():
    checker = _load_script("check_plugin_versions")
    manifests = {
        Path(".claude-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "author": {"name": "gimso2x", "url": "https://github.com/gimso2x"},
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
        Path(".codex-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "author": {"name": "gimso2x", "url": "https://github.com/gimso2x"},
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
    }
    marketplace = {
        "name": "forgeflow",
        "owner": {"name": "gimso2x", "url": "https://example.invalid/stale"},
        "metadata": {"version": "0.1.16"},
        "plugins": [{"name": "forgeflow"}],
    }

    errors = checker.plugin_metadata_errors(manifests, marketplace)

    assert errors == [
        ".claude-plugin/marketplace.json: owner.url 'https://example.invalid/stale' != 'https://github.com/gimso2x'"
    ]


def test_plugin_version_check_reports_unsupported_cursor_manifest_keyword():
    checker = _load_script("check_plugin_versions")
    manifests = {
        Path(".claude-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
            "keywords": ["Cursor"],
        },
        Path(".codex-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
    }
    marketplace = {"name": "forgeflow", "metadata": {"version": "0.1.16"}, "plugins": [{"name": "forgeflow"}]}

    errors = checker.plugin_metadata_errors(manifests, marketplace)

    assert errors == [".claude-plugin/plugin.json: keywords includes unsupported 'cursor'"]


def test_plugin_version_check_reports_unsupported_cursor_marketplace_tag():
    checker = _load_script("check_plugin_versions")
    manifests = {
        Path(".claude-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
        Path(".codex-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
    }
    marketplace = {
        "name": "forgeflow",
        "metadata": {"version": "0.1.16"},
        "plugins": [{"name": "forgeflow", "tags": ["codex", "Cursor"]}],
    }

    errors = checker.plugin_metadata_errors(manifests, marketplace)

    assert errors == [".claude-plugin/marketplace.json: plugins[0].tags includes unsupported 'cursor'"]


def test_plugin_version_check_strips_cursor_metadata_whitespace():
    checker = _load_script("check_plugin_versions")
    manifests = {
        Path(".claude-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
            "keywords": [" Cursor "],
        },
        Path(".codex-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
    }
    marketplace = {
        "name": "forgeflow",
        "metadata": {"version": "0.1.16"},
        "plugins": [{"name": "forgeflow", "tags": [" cursor "]}],
    }

    errors = checker.plugin_metadata_errors(manifests, marketplace)

    assert errors == [
        ".claude-plugin/plugin.json: keywords includes unsupported 'cursor'",
        ".claude-plugin/marketplace.json: plugins[0].tags includes unsupported 'cursor'",
    ]


def test_plugin_version_check_reports_marketplace_source_drift():
    checker = _load_script("check_plugin_versions")
    manifests = {
        Path(".claude-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
        Path(".codex-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
    }
    marketplace = {
        "name": "forgeflow",
        "metadata": {"version": "0.1.16"},
        "plugins": [{"name": "forgeflow", "source": "../.cursor-plugin"}],
    }

    errors = checker.plugin_metadata_errors(manifests, marketplace)

    assert errors == [".claude-plugin/marketplace.json: plugins[0].source '../.cursor-plugin' != './'"]


def test_plugin_version_check_reports_marketplace_plugin_version_drift():
    checker = _load_script("check_plugin_versions")
    manifests = {
        Path(".claude-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
        Path(".codex-plugin/plugin.json"): {
            "name": "forgeflow",
            "version": "0.1.16",
            "repository": "https://github.com/gimso2x/forgeflow",
            "license": "MIT",
        },
    }
    marketplace = {
        "name": "forgeflow",
        "metadata": {"version": "0.1.16"},
        "plugins": [{"name": "forgeflow", "version": "0.1.15"}],
    }

    errors = checker.plugin_metadata_errors(manifests, marketplace)

    assert errors == [".claude-plugin/marketplace.json: plugins[0].version '0.1.15' != '0.1.16'"]


def test_plugin_version_check_script_fails_fast_before_release():
    result = subprocess.run(
        [sys.executable, "scripts/check_plugin_versions.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert f"plugin versions synchronized: {load(CLAUDE)['version']}" in result.stdout


def test_codex_manifest_declares_skills_and_interface_metadata():
    manifest = load(CODEX)

    assert manifest["skills"] == "./skills/"
    interface = manifest["interface"]
    assert interface["displayName"] == "ForgeFlow"
    assert interface["category"] == "Coding"
    assert "Read" in interface["capabilities"]
    assert "Write" in interface["capabilities"]
    assert interface["defaultPrompt"]
    assert "artifact" in interface["longDescription"].lower()
