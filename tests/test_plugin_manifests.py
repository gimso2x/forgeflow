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


def test_plugin_version_check_script_fails_fast_before_release():
    result = subprocess.run(
        [sys.executable, "scripts/check_plugin_versions.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert "plugin versions synchronized: 0.1.16" in result.stdout


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
