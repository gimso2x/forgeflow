from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gemini_extension_manifest_points_at_generated_context() -> None:
    manifest = json.loads((ROOT / "gemini-extension.json").read_text(encoding="utf-8"))

    assert manifest["name"] == "forgeflow"
    assert manifest["description"] == "ForgeFlow runtime methodology and adapter guidance for Gemini CLI"
    assert manifest["contextFileName"] == "GEMINI.md"
    assert (ROOT / manifest["contextFileName"]).exists()
    root_gemini = (ROOT / "GEMINI.md").read_text(encoding="utf-8")
    assert "@./adapters/generated/gemini/GEMINI.md" in root_gemini
    assert "@./skills/SKILLS.md" in root_gemini
    assert "@./skills/using-superpowers/SKILL.md" in root_gemini
    assert "@./skills/using-superpowers/references/gemini-tools.md" in root_gemini
    assert (ROOT / "skills/using-superpowers/SKILL.md").exists()
    assert (ROOT / "skills/using-superpowers/references/gemini-tools.md").exists()
    for skill in ["forgeflow", "init", "clarify", "plan", "execute", "review", "ship", "finish"]:
        assert f"@./skills/{skill}/SKILL.md" in root_gemini
    assert (ROOT / "adapters/generated/gemini/GEMINI.md").exists()


def test_gemini_extension_docs_use_native_extension_commands() -> None:
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    generated = (ROOT / "adapters/generated/gemini/GEMINI.md").read_text(encoding="utf-8")

    assert "gemini extensions install https://github.com/gimso2x/forgeflow" in install
    assert "gemini extensions update forgeflow" in install
    assert "gemini extensions link /home/ubuntu/work/forgeflow" in install
    assert "gemini extensions install https://github.com/gimso2x/forgeflow" in generated
    assert "gemini extensions update forgeflow" in generated


def test_gemini_project_local_preset_remains_optional() -> None:
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

    assert "project-local 설치를 추가" in install
    assert "--adapter gemini" in install
    assert "--install-gemini-md" in install
