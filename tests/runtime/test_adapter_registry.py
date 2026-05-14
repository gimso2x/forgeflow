"""Tests for forgeflow_runtime.adapter_registry — AdapterRegistry + YAML parser."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from forgeflow_runtime.adapter_registry import (
    AdapterInfo,
    AdapterRegistry,
    _parse_yaml_manifest,
)


# ---------------------------------------------------------------------------
# YAML parser tests
# ---------------------------------------------------------------------------

class TestParseYamlManifest:
    def test_scalar_key_value(self) -> None:
        text = "name: claude\nruntime_type: cli-agent\n"
        result = _parse_yaml_manifest(text)
        assert result == {"name": "claude", "runtime_type": "cli-agent"}

    def test_string_list(self) -> None:
        text = "supports_roles:\n  - coordinator\n  - planner\n  - worker\n"
        result = _parse_yaml_manifest(text)
        assert result == {"supports_roles": ["coordinator", "planner", "worker"]}

    def test_mixed_scalars_and_lists(self) -> None:
        text = textwrap.dedent("""\
            name: codex
            runtime_type: cli-agent
            supports_roles:
              - coordinator
              - worker
            generated_filename: CODEX.md
        """)
        result = _parse_yaml_manifest(text)
        assert result["name"] == "codex"
        assert result["supports_roles"] == ["coordinator", "worker"]
        assert result["generated_filename"] == "CODEX.md"

    def test_comments_and_blank_lines_ignored(self) -> None:
        text = "# top comment\n\nname: test\n# inline comment\nvalue: 42\n"
        result = _parse_yaml_manifest(text)
        assert result == {"name": "test", "value": "42"}

    def test_empty_string(self) -> None:
        assert _parse_yaml_manifest("") == {}

    def test_list_with_no_items(self) -> None:
        text = "supports_roles:\nname: foo\n"
        result = _parse_yaml_manifest(text)
        assert result["supports_roles"] == []
        assert result["name"] == "foo"


# ---------------------------------------------------------------------------
# AdapterRegistry tests (fixtures)
# ---------------------------------------------------------------------------

@pytest.fixture()
def targets_dir(tmp_path: Path) -> Path:
    """Create a minimal adapter targets directory."""
    targets = tmp_path / "targets"
    targets.mkdir()

    # Adapter A — with agents dir
    a_dir = targets / "adapter-a"
    a_dir.mkdir()
    (a_dir / "manifest.yaml").write_text(textwrap.dedent("""\
        name: adapter-a
        runtime_type: cli-agent
        input_mode: prompt-and-files
        output_mode: markdown-and-files
        supports_roles:
          - coordinator
          - planner
          - worker
        supports_generated_files: true
        generated_filename: A.md
        recommended_location: ./A.md
        surface_style: root-instruction-file
        handoff_format: artifacts-plus-terminal-summary
    """), encoding="utf-8")
    agents_a = a_dir / "agents"
    agents_a.mkdir()
    (agents_a / "forgeflow-coordinator.md").write_text("# coord", encoding="utf-8")
    (agents_a / "forgeflow-planner.md").write_text("# plan", encoding="utf-8")

    # Adapter B — minimal, no agents dir
    b_dir = targets / "adapter-b"
    b_dir.mkdir()
    (b_dir / "manifest.yaml").write_text(textwrap.dedent("""\
        name: adapter-b
        runtime_type: ide-agent
        generated_filename: B.md
        recommended_location: ./B.md
        surface_style: root-instruction-file
        handoff_format: artifacts-plus-chat-summary
    """), encoding="utf-8")

    return targets


@pytest.fixture()
def empty_targets_dir(tmp_path: Path) -> Path:
    d = tmp_path / "empty_targets"
    d.mkdir()
    return d


@pytest.fixture()
def registry(targets_dir: Path) -> AdapterRegistry:
    return AdapterRegistry(targets_dir)


# ---------------------------------------------------------------------------
# AdapterRegistry — discovery
# ---------------------------------------------------------------------------

class TestAdapterRegistryDiscovery:
    def test_list_adapters_sorted(self, registry: AdapterRegistry) -> None:
        assert registry.list_adapters() == ["adapter-a", "adapter-b"]

    def test_empty_targets_dir(self, empty_targets_dir: Path) -> None:
        reg = AdapterRegistry(empty_targets_dir)
        assert reg.list_adapters() == []

    def test_nonexistent_targets_dir(self, tmp_path: Path) -> None:
        reg = AdapterRegistry(tmp_path / "nope")
        assert reg.list_adapters() == []

    def test_skips_dir_without_manifest(self, targets_dir: Path) -> None:
        (targets_dir / "orphan").mkdir()
        reg = AdapterRegistry(targets_dir)
        assert "orphan" not in reg.list_adapters()

    def test_skips_malformed_manifest(self, targets_dir: Path) -> None:
        bad_dir = targets_dir / "broken"
        bad_dir.mkdir()
        (bad_dir / "manifest.yaml").write_text(":::invalid:::\n", encoding="utf-8")
        reg = AdapterRegistry(targets_dir)
        assert "broken" not in reg.list_adapters()


# ---------------------------------------------------------------------------
# AdapterRegistry — lookup
# ---------------------------------------------------------------------------

class TestAdapterRegistryLookup:
    def test_get_existing(self, registry: AdapterRegistry) -> None:
        info = registry.get("adapter-a")
        assert isinstance(info, AdapterInfo)
        assert info.name == "adapter-a"
        assert info.runtime_type == "cli-agent"

    def test_get_missing_raises_key_error(self, registry: AdapterRegistry) -> None:
        with pytest.raises(KeyError, match="unknown adapter"):
            registry.get("nonexistent")

    def test_has_adapter(self, registry: AdapterRegistry) -> None:
        assert registry.has_adapter("adapter-a") is True
        assert registry.has_adapter("nope") is False


# ---------------------------------------------------------------------------
# AdapterRegistry — parsed fields
# ---------------------------------------------------------------------------

class TestAdapterRegistryFields:
    def test_supports_roles_parsed(self, registry: AdapterRegistry) -> None:
        info = registry.get("adapter-a")
        assert info.supports_roles == ("coordinator", "planner", "worker")

    def test_generated_filename(self, registry: AdapterRegistry) -> None:
        assert registry.get("adapter-a").generated_filename == "A.md"
        assert registry.get("adapter-b").generated_filename == "B.md"

    def test_agents_dir_set_when_exists(self, registry: AdapterRegistry) -> None:
        info = registry.get("adapter-a")
        assert info.agents_dir is not None
        assert info.agents_dir.is_dir()

    def test_agents_dir_none_when_missing(self, registry: AdapterRegistry) -> None:
        info = registry.get("adapter-b")
        assert info.agents_dir is None


# ---------------------------------------------------------------------------
# AdapterRegistry — agent_prompt_path
# ---------------------------------------------------------------------------

class TestAdapterRegistryAgentPromptPath:
    def test_existing_role(self, registry: AdapterRegistry) -> None:
        path = registry.agent_prompt_path("adapter-a", "planner")
        assert path is not None
        assert path.name == "forgeflow-planner.md"

    def test_nonexistent_role_returns_none(self, registry: AdapterRegistry) -> None:
        assert registry.agent_prompt_path("adapter-a", "dreamer") is None

    def test_no_agents_dir_returns_none(self, registry: AdapterRegistry) -> None:
        assert registry.agent_prompt_path("adapter-b", "coordinator") is None

    def test_unknown_adapter_raises(self, registry: AdapterRegistry) -> None:
        with pytest.raises(KeyError):
            registry.agent_prompt_path("ghost", "coordinator")


# ---------------------------------------------------------------------------
# Integration: real adapters/targets/
# ---------------------------------------------------------------------------

class TestRealAdapterTargets:
    """Verify the registry works against the actual repo adapters."""

    @pytest.fixture()
    def real_registry(self) -> AdapterRegistry:
        repo_root = Path(__file__).resolve().parents[2]
        return AdapterRegistry(repo_root / "adapters" / "targets")

    def test_discovers_all_adapters(self, real_registry: AdapterRegistry) -> None:
        assert set(real_registry.list_adapters()) == {
            "antigravity", "claude", "codex", "gemini", "generic",
        }

    @pytest.mark.parametrize("name,filename", [
        ("claude", "CLAUDE.md"),
        ("codex", "CODEX.md"),
        ("gemini", "GEMINI.md"),
        ("generic", "FORGEFLOW.md"),
        ("antigravity", "AGENTS.md"),
    ])
    def test_generated_filenames(
        self, real_registry: AdapterRegistry, name: str, filename: str,
    ) -> None:
        assert real_registry.get(name).generated_filename == filename

    def test_claude_agent_prompt_path(self, real_registry: AdapterRegistry) -> None:
        path = real_registry.agent_prompt_path("claude", "planner")
        assert path is not None
        assert path.exists()

    def test_all_adapters_support_coordinator(
        self, real_registry: AdapterRegistry,
    ) -> None:
        for name in real_registry.list_adapters():
            info = real_registry.get(name)
            assert "coordinator" in info.supports_roles, f"{name} missing coordinator"
