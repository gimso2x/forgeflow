import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GENERATE_ADAPTERS_PATH = ROOT / "scripts" / "generate_adapters.py"


def _load_generate_adapters_module():
    spec = importlib.util.spec_from_file_location("generate_adapters", GENERATE_ADAPTERS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validate_manifest_requires_target_specific_metadata() -> None:
    generate_adapters = _load_generate_adapters_module()
    manifest = {
        "name": "claude",
        "runtime_type": "cli-agent",
        "input_mode": "prompt-and-files",
        "output_mode": "markdown-and-files",
        "supports_roles": ["coordinator", "worker"],
        "supports_generated_files": True,
        "tooling_constraints": ["generated artifacts must not redefine canonical semantics"],
    }

    with pytest.raises(ValueError, match="missing required keys"):
        generate_adapters.validate_manifest(manifest, ROOT / "adapters" / "targets" / "claude" / "manifest.yaml")


def test_validate_manifest_rejects_missing_runtime_realism_fields() -> None:
    generate_adapters = _load_generate_adapters_module()
    manifest = {
        "name": "claude",
        "runtime_type": "cli-agent",
        "input_mode": "prompt-and-files",
        "output_mode": "markdown-and-files",
        "supports_roles": ["coordinator", "planner", "worker", "spec-reviewer", "quality-reviewer"],
        "supports_generated_files": True,
        "tooling_constraints": [
            "prompt surface may be CLAUDE.md style",
            "generated artifacts must not redefine canonical semantics",
        ],
        "generated_filename": "CLAUDE.md",
        "recommended_location": "./CLAUDE.md",
        "surface_style": "root-instruction-file",
        "handoff_format": "artifacts-plus-terminal-summary",
        "installation_steps": [
            "Copy the generated adapter to ./CLAUDE.md at the repo root.",
            "Keep Claude-specific helper notes in surrounding docs, not by changing ForgeFlow semantics.",
        ],
        "recovery_delivery_note": "Claude may deliver recovery through optional adapter hooks plus generated instructions.",
    }

    with pytest.raises(ValueError, match=r"missing required keys \['session_persistence', 'workspace_boundary', 'review_delivery'\]"):
        generate_adapters.validate_manifest(manifest, ROOT / "adapters" / "targets" / "claude" / "manifest.yaml")


def test_validate_manifest_rejects_missing_installation_steps() -> None:
    generate_adapters = _load_generate_adapters_module()
    manifest = {
        "name": "cursor",
        "runtime_type": "editor-agent",
        "input_mode": "rules-and-context",
        "output_mode": "files-and-chat",
        "supports_roles": ["planner", "worker", "spec-reviewer", "quality-reviewer"],
        "supports_generated_files": True,
        "tooling_constraints": [
            "rules surface may require .mdc or cursor-specific placement",
            "generated artifacts must not redefine canonical semantics",
        ],
        "generated_filename": "HARNESS_CURSOR.md",
        "recommended_location": ".cursor/rules/forgeflow.mdc",
        "surface_style": "cursor-rules-markdown",
        "handoff_format": "artifacts-plus-chat-summary",
        "session_persistence": "rule-file persists across chat sessions until regenerated",
        "workspace_boundary": "project rules live under .cursor/rules and guide editor-native runs",
        "review_delivery": "chat summary plus artifact file updates inside the workspace",
        "recovery_delivery_note": "Cursor delivers recovery through .cursor/rules guidance, not hooks.",
    }

    with pytest.raises(ValueError, match=r"missing required keys \['installation_steps'\]"):
        generate_adapters.validate_manifest(manifest, ROOT / "adapters" / "targets" / "cursor" / "manifest.yaml")


def test_generated_filename_comes_from_manifest() -> None:
    generate_adapters = _load_generate_adapters_module()

    manifest = {
        "generated_filename": "CUSTOM_CURSOR.md",
    }

    assert generate_adapters.file_for_target("cursor", manifest) == "CUSTOM_CURSOR.md"


def test_build_content_includes_target_specific_install_and_handoff_sections() -> None:
    generate_adapters = _load_generate_adapters_module()
    manifest = {
        "name": "cursor",
        "runtime_type": "editor-agent",
        "input_mode": "rules-and-context",
        "output_mode": "files-and-chat",
        "supports_roles": ["planner", "worker", "spec-reviewer", "quality-reviewer"],
        "supports_generated_files": True,
        "tooling_constraints": [
            "rules surface may require .mdc or cursor-specific placement",
            "generated artifacts must not redefine canonical semantics",
        ],
        "installation_steps": [
            "Place the generated content in .cursor/rules/forgeflow.mdc.",
            "Keep ForgeFlow workflow semantics in this rule file and avoid per-chat rewrites.",
        ],
        "generated_filename": "HARNESS_CURSOR.md",
        "recommended_location": ".cursor/rules/forgeflow.mdc",
        "surface_style": "cursor-rules-markdown",
        "handoff_format": "artifacts-plus-chat-summary",
        "session_persistence": "rule-file persists across chat sessions until regenerated",
        "workspace_boundary": "project rules live under .cursor/rules and guide editor-native runs",
        "review_delivery": "chat summary plus artifact file updates inside the workspace",
        "recovery_delivery_note": "Cursor delivers recovery through .cursor/rules guidance, not hooks.",
    }

    content = generate_adapters.build_content("cursor", manifest)

    assert "## Installation guidance" in content
    assert "- generated_filename: HARNESS_CURSOR.md" in content
    assert "- recommended_location: .cursor/rules/forgeflow.mdc" in content
    assert "## Installation steps" in content
    assert "1. Place the generated content in .cursor/rules/forgeflow.mdc." in content
    assert "2. Keep ForgeFlow workflow semantics in this rule file and avoid per-chat rewrites." in content
    assert "## Target operating notes" in content
    assert "- surface_style: cursor-rules-markdown" in content
    assert "- handoff_format: artifacts-plus-chat-summary" in content
    assert "## Runtime realism contract" in content
    assert "- session_persistence: rule-file persists across chat sessions until regenerated" in content
    assert "- workspace_boundary: project rules live under .cursor/rules and guide editor-native runs" in content
    assert "- review_delivery: chat summary plus artifact file updates inside the workspace" in content
    assert "Copy this generated adapter into `.cursor/rules/forgeflow.mdc`" in content
