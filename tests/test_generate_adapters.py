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
        "generated_filename": "HARNESS_CURSOR.md",
        "recommended_location": ".cursor/rules/forgeflow.mdc",
        "surface_style": "cursor-rules-markdown",
        "handoff_format": "artifacts-plus-chat-summary",
    }

    content = generate_adapters.build_content("cursor", manifest)

    assert "## Installation guidance" in content
    assert "- generated_filename: HARNESS_CURSOR.md" in content
    assert "- recommended_location: .cursor/rules/forgeflow.mdc" in content
    assert "## Target operating notes" in content
    assert "- surface_style: cursor-rules-markdown" in content
    assert "- handoff_format: artifacts-plus-chat-summary" in content
    assert "Copy this generated adapter into `.cursor/rules/forgeflow.mdc`" in content
