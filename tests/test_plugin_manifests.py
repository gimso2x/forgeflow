import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / ".claude-plugin" / "plugin.json"
CODEX = ROOT / ".codex-plugin" / "plugin.json"
CURSOR = ROOT / ".cursor-plugin" / "plugin.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_codex_and_cursor_plugin_manifests_exist_and_match_core_metadata():
    claude = load(CLAUDE)
    codex = load(CODEX)
    cursor = load(CURSOR)

    for manifest in (codex, cursor):
        assert manifest["name"] == "forgeflow"
        assert manifest["version"] == claude["version"]
        assert manifest["repository"] == claude["repository"]
        assert manifest["license"] == claude["license"]
        assert "artifact" in manifest["description"].lower()
        assert "codex" in manifest["keywords"]
        assert "cursor" in manifest["keywords"]


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


def test_cursor_manifest_declares_plugin_surfaces():
    manifest = load(CURSOR)

    assert manifest["displayName"] == "ForgeFlow"
    assert manifest["skills"] == "./skills/"
    assert manifest["agents"] == "./adapters/targets/claude/presets/agents/"
    assert manifest["commands"] == "./skills/"
    assert manifest["interface"]["category"] == "Coding"
