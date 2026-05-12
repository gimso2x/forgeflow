"""Tool-use capability declarations and stage-to-policy mapping.

This module defines the abstraction layer between ForgeFlow's stage
execution and agent tool capabilities.  It is purely declarative —
no behavior change to existing adapters.

Phase 1: Declare, don't enforce.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field


class ToolCapability(enum.Enum):
    """Categories of tool access a stage may need."""

    FILESYSTEM = "filesystem"
    SHELL = "shell"
    WEB_SEARCH = "web_search"
    GITHUB = "github"
    ARTIFACT_IO = "artifact_io"


@dataclass(frozen=True)
class ToolPolicy:
    """Tool requirements for a single stage."""

    required: list[ToolCapability]
    optional: list[ToolCapability]
    constraints: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterCapability:
    """Capability profile for an adapter target."""

    name: str
    capabilities: list[ToolCapability]
    max_token_input: int = 128_000
    max_token_output: int = 16_384
    supports_streaming: bool = False
    invocation_style: str = "subprocess"

    def supports(self, *caps: ToolCapability) -> bool:
        cap_set = set(self.capabilities)
        return all(c in cap_set for c in caps)


# ---------------------------------------------------------------------------
# Stage → ToolPolicy mapping
# ---------------------------------------------------------------------------

_STAGE_POLICIES: dict[str, ToolPolicy] = {
    "clarify": ToolPolicy(
        required=[ToolCapability.FILESYSTEM, ToolCapability.ARTIFACT_IO],
        optional=[ToolCapability.SHELL, ToolCapability.WEB_SEARCH],
        constraints={"filesystem": "read-only-preferred"},
    ),
    "plan": ToolPolicy(
        required=[ToolCapability.FILESYSTEM, ToolCapability.ARTIFACT_IO],
        optional=[ToolCapability.SHELL, ToolCapability.WEB_SEARCH, ToolCapability.GITHUB],
    ),
    "work": ToolPolicy(
        required=[
            ToolCapability.FILESYSTEM,
            ToolCapability.SHELL,
            ToolCapability.ARTIFACT_IO,
        ],
        optional=[ToolCapability.WEB_SEARCH, ToolCapability.GITHUB],
        constraints={"filesystem": "task-dir-and-workspace"},
    ),
    "review": ToolPolicy(
        required=[ToolCapability.FILESYSTEM, ToolCapability.ARTIFACT_IO],
        optional=[ToolCapability.GITHUB, ToolCapability.SHELL],
        constraints={"filesystem": "read-only-for-source"},
    ),
    "ship": ToolPolicy(
        required=[ToolCapability.FILESYSTEM, ToolCapability.ARTIFACT_IO, ToolCapability.GITHUB],
        optional=[ToolCapability.SHELL],
        constraints={"filesystem": "workspace-only"},
    ),
}


def tool_policy_for_stage(stage: str) -> ToolPolicy:
    """Return the tool policy for a named stage.

    Raises KeyError for unknown stages.
    """
    if stage not in _STAGE_POLICIES:
        raise KeyError(f"no tool policy defined for stage: {stage}")
    return _STAGE_POLICIES[stage]


def all_stage_policies() -> dict[str, ToolPolicy]:
    """Return a copy of the full stage→policy mapping."""
    return dict(_STAGE_POLICIES)


# ---------------------------------------------------------------------------
# Adapter capability profiles (Phase 1: declarative only)
# ---------------------------------------------------------------------------

ADAPTER_PROFILES: dict[str, AdapterCapability] = {
    "claude": AdapterCapability(
        name="claude",
        capabilities=[
            ToolCapability.FILESYSTEM,
            ToolCapability.SHELL,
            ToolCapability.ARTIFACT_IO,
            ToolCapability.GITHUB,
        ],
        max_token_input=200_000,
        max_token_output=32_768,
        supports_streaming=True,
        invocation_style="subprocess",
    ),
    "codex": AdapterCapability(
        name="codex",
        capabilities=[
            ToolCapability.FILESYSTEM,
            ToolCapability.SHELL,
            ToolCapability.ARTIFACT_IO,
            ToolCapability.WEB_SEARCH,
            ToolCapability.GITHUB,
        ],
        max_token_input=128_000,
        max_token_output=16_384,
        supports_streaming=False,
        invocation_style="subprocess",
    ),
    "antigravity": AdapterCapability(
        name="antigravity",
        capabilities=[
            ToolCapability.FILESYSTEM,
            ToolCapability.ARTIFACT_IO,
            ToolCapability.WEB_SEARCH,
        ],
        max_token_input=128_000,
        max_token_output=16_384,
        supports_streaming=False,
        invocation_style="subprocess",
    ),
    "generic": AdapterCapability(
        name="generic",
        capabilities=[
            ToolCapability.FILESYSTEM,
            ToolCapability.ARTIFACT_IO,
        ],
        max_token_input=128_000,
        max_token_output=16_384,
        supports_streaming=False,
        invocation_style="subprocess",
    ),
}


def adapter_profile(name: str) -> AdapterCapability:
    """Return the capability profile for a named adapter.

    Raises KeyError for unknown adapters.
    """
    if name not in ADAPTER_PROFILES:
        raise KeyError(f"no adapter profile for: {name}")
    return ADAPTER_PROFILES[name]


def match_adapter(
    policy: ToolPolicy,
    preferred: str | None = None,
    *,
    use_real: bool = False,
) -> tuple[str, AdapterCapability]:
    """Find an adapter that satisfies the given tool policy.

    If *preferred* is given and it satisfies the policy, return it.
    Otherwise, fall back to the first adapter that has all required
    capabilities.

    Returns (adapter_name, profile).  Raises ValueError if nothing matches.
    """
    required = set(policy.required)

    # Try preferred first
    if preferred is not None:
        profile = ADAPTER_PROFILES.get(preferred)
        if profile is not None and profile.supports(*policy.required):
            return preferred, profile

    # Fallback: first adapter that satisfies all required caps
    for name, profile in ADAPTER_PROFILES.items():
        if profile.supports(*policy.required):
            return name, profile

    raise ValueError(
        f"no adapter satisfies required capabilities: "
        f"{[c.value for c in policy.required]}"
    )
