"""Tests for the MCP/tool-use abstraction layer (Phase 1: declare, don't enforce)."""
from __future__ import annotations

import pytest

from forgeflow_runtime.tool_policy import (
    ADAPTER_PROFILES,
    AdapterCapability,
    ToolCapability,
    ToolPolicy,
    adapter_profile,
    all_stage_policies,
    match_adapter,
    tool_policy_for_stage,
)


class TestToolCapability:
    def test_all_capabilities_are_distinct(self):
        values = [c.value for c in ToolCapability]
        assert len(values) == len(set(values))

    def test_expected_capabilities_exist(self):
        expected = {"filesystem", "shell", "web_search", "github", "artifact_io"}
        actual = {c.value for c in ToolCapability}
        assert actual == expected


class TestToolPolicy:
    def test_frozen(self):
        policy = ToolPolicy(required=[ToolCapability.FILESYSTEM], optional=[])
        with pytest.raises(AttributeError):
            policy.required = []  # type: ignore[misc]

    def test_constraints_default_empty(self):
        policy = ToolPolicy(required=[], optional=[])
        assert policy.constraints == {}


class TestAdapterCapability:
    def test_supports_returns_true_for_present_caps(self):
        cap = AdapterCapability(
            name="test",
            capabilities=[ToolCapability.FILESYSTEM, ToolCapability.SHELL],
        )
        assert cap.supports(ToolCapability.FILESYSTEM)
        assert cap.supports(ToolCapability.FILESYSTEM, ToolCapability.SHELL)

    def test_supports_returns_false_for_missing_caps(self):
        cap = AdapterCapability(
            name="test",
            capabilities=[ToolCapability.FILESYSTEM],
        )
        assert not cap.supports(ToolCapability.SHELL)
        assert not cap.supports(ToolCapability.FILESYSTEM, ToolCapability.GITHUB)

    def test_default_values(self):
        cap = AdapterCapability(name="test", capabilities=[])
        assert cap.max_token_input == 128_000
        assert cap.max_token_output == 16_384
        assert cap.supports_streaming is False
        assert cap.invocation_style == "subprocess"


class TestStagePolicies:
    @pytest.mark.parametrize("stage", ["clarify", "plan", "work", "review", "ship"])
    def test_all_standard_stages_have_policies(self, stage):
        policy = tool_policy_for_stage(stage)
        assert isinstance(policy, ToolPolicy)
        assert ToolCapability.ARTIFACT_IO in policy.required

    def test_unknown_stage_raises(self):
        with pytest.raises(KeyError, match="no tool policy"):
            tool_policy_for_stage("nonexistent")

    def test_work_requires_filesystem_shell_artifact(self):
        policy = tool_policy_for_stage("work")
        assert ToolCapability.FILESYSTEM in policy.required
        assert ToolCapability.SHELL in policy.required
        assert ToolCapability.ARTIFACT_IO in policy.required

    def test_review_has_read_only_constraint(self):
        policy = tool_policy_for_stage("review")
        assert "filesystem" in policy.constraints

    def test_ship_requires_github(self):
        policy = tool_policy_for_stage("ship")
        assert ToolCapability.GITHUB in policy.required

    def test_all_stage_policies_returns_all(self):
        policies = all_stage_policies()
        assert set(policies.keys()) == {"clarify", "plan", "work", "review", "ship"}


class TestAdapterProfiles:
    def test_claude_profile_exists(self):
        profile = adapter_profile("claude")
        assert profile.name == "claude"
        assert ToolCapability.FILESYSTEM in profile.capabilities

    def test_codex_profile_has_web_search(self):
        profile = adapter_profile("codex")
        assert ToolCapability.WEB_SEARCH in profile.capabilities

    def test_generic_profile_is_minimal(self):
        profile = adapter_profile("generic")
        assert set(profile.capabilities) == {ToolCapability.FILESYSTEM, ToolCapability.ARTIFACT_IO}

    def test_antigravity_profile_exists(self):
        profile = adapter_profile("antigravity")
        assert profile.name == "antigravity"

    def test_unknown_adapter_raises(self):
        with pytest.raises(KeyError, match="no adapter profile"):
            adapter_profile("nonexistent")

    def test_all_adapters_support_artifact_io(self):
        for name, profile in ADAPTER_PROFILES.items():
            assert ToolCapability.ARTIFACT_IO in profile.capabilities, (
                f"{name} must support ARTIFACT_IO"
            )


class TestMatchAdapter:
    def test_preferred_adapter_satisfies_policy(self):
        policy = ToolPolicy(
            required=[ToolCapability.FILESYSTEM, ToolCapability.ARTIFACT_IO],
            optional=[],
        )
        name, profile = match_adapter(policy, preferred="claude")
        assert name == "claude"

    def test_fallback_when_preferred_doesnt_match(self):
        policy = ToolPolicy(
            required=[ToolCapability.SHELL],
            optional=[],
        )
        # generic doesn't have SHELL, so fallback to first that does
        name, profile = match_adapter(policy, preferred="generic")
        assert name != "generic"
        assert ToolCapability.SHELL in profile.capabilities

    def test_no_match_raises(self):
        # Create a policy requiring a capability no adapter has
        # by directly constructing a policy with all 5 capabilities
        # (codex has all 5, so we need to temporarily remove it)
        from forgeflow_runtime import tool_policy as tp
        original = tp.ADAPTER_PROFILES.copy()
        try:
            tp.ADAPTER_PROFILES.clear()
            # Only register an adapter missing SHELL
            tp.ADAPTER_PROFILES["limited"] = AdapterCapability(
                name="limited",
                capabilities=[ToolCapability.FILESYSTEM, ToolCapability.ARTIFACT_IO],
            )
            policy = ToolPolicy(required=[ToolCapability.SHELL], optional=[])
            with pytest.raises(ValueError, match="no adapter satisfies"):
                match_adapter(policy)
        finally:
            tp.ADAPTER_PROFILES.update(original)

    def test_null_preferred_falls_back(self):
        policy = ToolPolicy(
            required=[ToolCapability.FILESYSTEM],
            optional=[],
        )
        name, _ = match_adapter(policy, preferred=None)
        assert name in ADAPTER_PROFILES
