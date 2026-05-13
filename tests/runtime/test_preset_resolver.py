"""Tests for forgeflow_runtime.preset_resolver — PresetResolver + composition."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from forgeflow_runtime.preset_resolver import (
    CORE_PLACEHOLDER,
    COMPOSITION_SUFFIXES,
    PresetError,
    PresetResolver,
    make_preset_resolver,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def core_dir(tmp_path: Path) -> Path:
    """Create a minimal set of canonical prompts."""
    prompts = tmp_path / "core"
    prompts.mkdir()
    (prompts / "coordinator.md").write_text("# Coordinator\n\nCore coordinator prompt.")
    (prompts / "planner.md").write_text("# Planner\n\nCore planner prompt.")
    (prompts / "worker.md").write_text("# Worker\n\nCore worker prompt.")
    (prompts / "spec-reviewer.md").write_text("# Spec Reviewer\n\nCore spec reviewer.")
    (prompts / "quality-reviewer.md").write_text("# Quality Reviewer\n\nCore quality reviewer.")
    return prompts


@pytest.fixture()
def override_dir(tmp_path: Path) -> Path:
    """Create an empty override directory."""
    d = tmp_path / "presets"
    d.mkdir()
    return d


def _resolver(core_dir: Path, override_dir: Path | None = None) -> PresetResolver:
    return PresetResolver(core_dir=core_dir, override_dir=override_dir)


# ── Core-only (no overrides) ────────────────────────────────────────────────


class TestCoreOnly:
    """When no override_dir is given, core is returned unchanged."""

    def test_resolve_returns_core(self, core_dir: Path) -> None:
        r = _resolver(core_dir)
        result = r.resolve("coordinator")
        assert "# Coordinator" in result
        assert "Core coordinator prompt." in result

    def test_resolve_all_roles(self, core_dir: Path) -> None:
        r = _resolver(core_dir)
        for role in ("coordinator", "planner", "worker", "spec-reviewer", "quality-reviewer"):
            assert r.resolve(role)

    def test_unknown_role_raises(self, core_dir: Path) -> None:
        r = _resolver(core_dir)
        with pytest.raises(PresetError, match="unknown role"):
            r.resolve("nonexistent-role")

    def test_override_dir_none_no_overrides(self, core_dir: Path) -> None:
        r = _resolver(core_dir, override_dir=None)
        assert r.list_overrides() == []
        assert r.has_override("coordinator") is False

    def test_empty_override_dir_no_overrides(self, core_dir: Path, override_dir: Path) -> None:
        r = _resolver(core_dir, override_dir)
        assert r.list_overrides() == []
        assert r.has_override("coordinator") is False


# ── Replace strategy ────────────────────────────────────────────────────────


class TestReplaceStrategy:
    def test_replace_overrides_core(self, core_dir: Path, override_dir: Path) -> None:
        (override_dir / "coordinator.md").write_text("# Custom Coordinator\n\nFull replacement.")
        r = _resolver(core_dir, override_dir)
        result = r.resolve("coordinator")
        assert "Custom Coordinator" in result
        assert "Core coordinator" not in result

    def test_replace_is_entire_override(self, core_dir: Path, override_dir: Path) -> None:
        content = "REPLACED ENTIRELY"
        (override_dir / "worker.md").write_text(content)
        r = _resolver(core_dir, override_dir)
        assert r.resolve("worker") == content


# ── Append strategy ─────────────────────────────────────────────────────────


class TestAppendStrategy:
    def test_append_adds_after_core(self, core_dir: Path, override_dir: Path) -> None:
        (override_dir / "coordinator.append.md").write_text("APPENDED EXTRA")
        r = _resolver(core_dir, override_dir)
        result = r.resolve("coordinator")
        assert result.startswith("# Coordinator")
        assert result.endswith("APPENDED EXTRA")
        assert "Core coordinator prompt." in result

    def test_append_separator(self, core_dir: Path, override_dir: Path) -> None:
        (override_dir / "planner.append.md").write_text("EXTRA")
        r = _resolver(core_dir, override_dir)
        result = r.resolve("planner")
        assert "Core planner prompt.\n\nEXTRA" in result


# ── Prepend strategy ────────────────────────────────────────────────────────


class TestPrependStrategy:
    def test_prepend_adds_before_core(self, core_dir: Path, override_dir: Path) -> None:
        (override_dir / "coordinator.prepend.md").write_text("PREPENDED HEADER")
        r = _resolver(core_dir, override_dir)
        result = r.resolve("coordinator")
        assert result.startswith("PREPENDED HEADER")
        assert "Core coordinator prompt." in result


# ── Wrap strategy ───────────────────────────────────────────────────────────


class TestWrapStrategy:
    def test_wrap_inserts_core_into_placeholder(
        self, core_dir: Path, override_dir: Path
    ) -> None:
        wrap_content = f"BEFORE\n{CORE_PLACEHOLDER}\nAFTER"
        (override_dir / "coordinator.wrap.md").write_text(wrap_content)
        r = _resolver(core_dir, override_dir)
        result = r.resolve("coordinator")
        assert result.startswith("BEFORE\n")
        assert "Core coordinator prompt." in result
        assert result.endswith("\nAFTER")

    def test_wrap_without_placeholder_raises(
        self, core_dir: Path, override_dir: Path
    ) -> None:
        (override_dir / "planner.wrap.md").write_text("NO PLACEHOLDER HERE")
        r = _resolver(core_dir, override_dir)
        with pytest.raises(PresetError, match="placeholder"):
            r.resolve("planner")


# ── Priority: more specific suffix wins over plain replace ──────────────────


class TestPriority:
    def test_wrap_beats_replace(self, core_dir: Path, override_dir: Path) -> None:
        (override_dir / "coordinator.md").write_text("REPLACE CONTENT")
        (override_dir / "coordinator.wrap.md").write_text(
            f"WRAP\n{CORE_PLACEHOLDER}\nENDWRAP"
        )
        r = _resolver(core_dir, override_dir)
        result = r.resolve("coordinator")
        # wrap wins — contains both WRAP markers
        assert "WRAP" in result
        assert "ENDWRAP" in result
        assert "REPLACE CONTENT" not in result

    def test_append_beats_replace(self, core_dir: Path, override_dir: Path) -> None:
        (override_dir / "planner.md").write_text("REPLACE")
        (override_dir / "planner.append.md").write_text("APPENDED")
        r = _resolver(core_dir, override_dir)
        result = r.resolve("planner")
        assert "Core planner prompt." in result
        assert "APPENDED" in result
        assert "REPLACE" not in result


# ── has_override / list_overrides ────────────────────────────────────────────


class TestOverrideDiscovery:
    def test_has_override_true(self, core_dir: Path, override_dir: Path) -> None:
        (override_dir / "coordinator.append.md").write_text("extra")
        r = _resolver(core_dir, override_dir)
        assert r.has_override("coordinator") is True
        assert r.has_override("planner") is False

    def test_list_overrides(self, core_dir: Path, override_dir: Path) -> None:
        (override_dir / "coordinator.append.md").write_text("a")
        (override_dir / "worker.prepend.md").write_text("b")
        r = _resolver(core_dir, override_dir)
        assert r.list_overrides() == ["coordinator", "worker"]


# ── make_preset_resolver factory ────────────────────────────────────────────


class TestFactory:
    def test_factory_no_project(self) -> None:
        r = make_preset_resolver()
        assert r is not None
        # Should be able to resolve at least coordinator from real repo
        result = r.resolve("coordinator")
        assert "# Coordinator" in result

    def test_factory_with_nonexistent_project(self, tmp_path: Path) -> None:
        r = make_preset_resolver(tmp_path / "nope")
        # No override dir, still works
        assert r.list_overrides() == []

    def test_factory_with_presets_dir(self, tmp_path: Path) -> None:
        presets = tmp_path / ".forgeflow" / "presets"
        presets.mkdir(parents=True)
        (presets / "coordinator.append.md").write_text("PROJECT EXTRA")
        r = make_preset_resolver(tmp_path)
        assert r.has_override("coordinator") is True


# ── Integration with generator.py ───────────────────────────────────────────


class TestGeneratorIntegration:
    def test_generator_uses_preset_resolver(self, tmp_path: Path) -> None:
        """Verify generator._load_role_prompt goes through PresetResolver."""
        from forgeflow_runtime.generator import (
            _load_role_prompt,
            get_preset_resolver,
            set_preset_resolver,
        )

        # Save original
        original = get_preset_resolver()

        try:
            # Create a resolver with override
            core = tmp_path / "core"
            core.mkdir()
            (core / "coordinator.md").write_text("CORE")
            override = tmp_path / "presets"
            override.mkdir()
            (override / "coordinator.append.md").write_text("OVERRIDDEN")
            set_preset_resolver(_resolver(core, override))

            result = _load_role_prompt("coordinator")
            assert "CORE" in result
            assert "OVERRIDDEN" in result
        finally:
            set_preset_resolver(original)
