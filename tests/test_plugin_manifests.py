import json
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
