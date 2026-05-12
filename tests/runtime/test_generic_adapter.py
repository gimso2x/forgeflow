"""Tests for the generic adapter target."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGETS_DIR = ROOT / "adapters" / "targets"
GENERATED_DIR = ROOT / "adapters" / "generated"
GENERATE_ADAPTERS_PATH = ROOT / "scripts" / "generate_adapters.py"


def _load_generate_adapters_module():
    spec = importlib.util.spec_from_file_location("generate_adapters", GENERATE_ADAPTERS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestGenericManifest:
    """Validate the generic adapter manifest."""

    def test_generic_manifest_exists(self):
        manifest_path = TARGETS_DIR / "generic" / "manifest.yaml"
        assert manifest_path.is_file(), "generic manifest.yaml must exist"

    def test_generic_manifest_validates(self):
        generate_adapters = _load_generate_adapters_module()
        manifest = generate_adapters.load_manifest(TARGETS_DIR / "generic" / "manifest.yaml")
        generate_adapters.validate_manifest(manifest, TARGETS_DIR / "generic" / "manifest.yaml")

    def test_generic_manifest_name(self):
        generate_adapters = _load_generate_adapters_module()
        manifest = generate_adapters.load_manifest(TARGETS_DIR / "generic" / "manifest.yaml")
        assert manifest["name"] == "generic"

    def test_generic_manifest_generates_forgeflow_md(self):
        generate_adapters = _load_generate_adapters_module()
        manifest = generate_adapters.load_manifest(TARGETS_DIR / "generic" / "manifest.yaml")
        assert manifest["generated_filename"] == "FORGEFLOW.md"

    def test_generic_manifest_has_all_required_roles(self):
        generate_adapters = _load_generate_adapters_module()
        manifest = generate_adapters.load_manifest(TARGETS_DIR / "generic" / "manifest.yaml")
        expected_roles = {"coordinator", "planner", "worker", "spec-reviewer", "quality-reviewer"}
        assert set(manifest["supports_roles"]) == expected_roles

    def test_generic_manifest_explains_it_is_a_template(self):
        generate_adapters = _load_generate_adapters_module()
        manifest = generate_adapters.load_manifest(TARGETS_DIR / "generic" / "manifest.yaml")
        constraints = " ".join(manifest["tooling_constraints"]).lower()
        assert "template" in constraints or "documentation" in constraints or "not a supported runtime adapter" in constraints


class TestGenericGenerated:
    """Validate the generated generic adapter file."""

    def test_generated_forgeflow_md_exists(self):
        assert (GENERATED_DIR / "generic" / "FORGEFLOW.md").is_file()

    def test_generated_forgeflow_md_mentions_forgeflow(self):
        content = (GENERATED_DIR / "generic" / "FORGEFLOW.md").read_text(encoding="utf-8")
        assert "ForgeFlow" in content

    def test_generated_forgeflow_md_includes_tooling_constraints(self):
        generate_adapters = _load_generate_adapters_module()
        manifest = generate_adapters.load_manifest(TARGETS_DIR / "generic" / "manifest.yaml")
        content = (GENERATED_DIR / "generic" / "FORGEFLOW.md").read_text(encoding="utf-8")
        for constraint in manifest["tooling_constraints"]:
            assert constraint in content

    def test_generate_adapters_check_passes_with_generic(self, tmp_path):
        """Run --check to verify generic is included and current."""
        generate_adapters = _load_generate_adapters_module()
        manifest = generate_adapters.load_manifest(TARGETS_DIR / "generic" / "manifest.yaml")
        generated_file = GENERATED_DIR / "generic" / "FORGEFLOW.md"
        assert generated_file.exists(), "generic adapter must be generated"
        content = generate_adapters.build_content("generic", manifest)
        assert generated_file.read_text(encoding="utf-8") == content, "generic adapter must be current"


class TestGenericDocs:
    """Validate the GENERIC.md guide."""

    def test_generic_md_exists(self):
        assert (TARGETS_DIR / "generic" / "GENERIC.md").is_file()

    def test_generic_md_mentions_supported_agents(self):
        content = (TARGETS_DIR / "generic" / "GENERIC.md").read_text(encoding="utf-8")
        for agent_name in ["Gemini", "Cursor", "Aider"]:
            assert agent_name in content, f"GENERIC.md must mention {agent_name}"

    def test_generic_md_includes_mapping_table(self):
        content = (TARGETS_DIR / "generic" / "GENERIC.md").read_text(encoding="utf-8")
        assert "ForgeFlow concept" in content
