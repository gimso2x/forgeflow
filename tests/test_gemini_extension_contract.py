from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gemini_extension_manifest_points_at_generated_context() -> None:
    manifest = json.loads((ROOT / "gemini-extension.json").read_text(encoding="utf-8"))

    assert manifest["name"] == "forgeflow"
    assert manifest["description"] == "An artifact-first workflow contract plus a lightweight enforcement runtime for Gemini CLI"
    assert manifest["contextFileName"] == "GEMINI.md"
    assert (ROOT / manifest["contextFileName"]).exists()
    root_gemini = (ROOT / "GEMINI.md").read_text(encoding="utf-8")
    assert "@./adapters/generated/gemini/GEMINI.md" in root_gemini
    assert "@./skills/SKILLS.md" in root_gemini
    for skill in ["forgeflow", "init", "clarify", "plan", "milestone", "execute", "review", "ship", "finish"]:
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


def test_gemini_extension_documents_artifact_ignore_and_plan_fallback() -> None:
    generated = (ROOT / "adapters/generated/gemini/GEMINI.md").read_text(encoding="utf-8")

    assert "If Gemini file-read tools report `.forgeflow/tasks/...` as ignored" in generated
    assert "`.forgeflow/tasks/<task-id>/` is the authoritative task artifact directory" in generated
    assert "If Gemini internal JSON/classifier routing fails during `/forgeflow:plan`" in generated
    assert "`low -> small`, `medium -> medium`, `high -> high`, otherwise `small`" in generated
    assert "gemini --skip-trust --prompt --yolo <prompt>" in generated


def test_gemini_real_adapter_uses_skip_trust_for_untrusted_smoke_repos() -> None:
    from forgeflow_runtime.executor import GeminiCLIAdapter, RunTaskRequest

    command = GeminiCLIAdapter().build_command(
        RunTaskRequest(
            prompt="hello",
            role="worker",
            stage="execute",
            task_dir=ROOT,
            task_id="test-task",
            token_budget_input=1000,
            token_budget_output=1000,
            adapter_target="gemini",
        )
    )

    assert command[1:4] == ["--skip-trust", "--prompt", "--yolo"]


def test_gemini_project_local_preset_remains_optional() -> None:
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

    assert "project-local 설치를 추가" in install
    assert "--adapter gemini" in install
    assert "--install-gemini-md" in install
