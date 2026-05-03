"""Lightweight Mode: SKILL.md-only fallback when the full runtime is unavailable.

Provides a graduated enforcement model (HARD / SOFT / HYBRID) that degrades
gracefully when forgeflow runtime dependencies are missing, allowing agents
to operate from SKILL.md guidance alone.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------

class EnforcementMode(Enum):
    """How strictly the runtime enforces gates and stage transitions."""

    HARD = "hard"
    SOFT = "soft"
    HYBRID = "hybrid"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RuntimeAvailability:
    """Snapshot of the runtime environment's readiness."""

    runtime_available: bool
    python_version: str | None
    missing_modules: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LightweightConfig:
    """Top-level configuration for lightweight-mode behaviour."""

    mode: EnforcementMode = EnforcementMode.HARD
    skill_md_paths: list[str] = field(default_factory=list)
    stages_enabled: list[str] = field(
        default_factory=lambda: ["clarify", "plan", "execute", "review"],
    )
    fallback_to_soft: bool = True


# ---------------------------------------------------------------------------
# Runtime probe
# ---------------------------------------------------------------------------

_CORE_MODULES = [
    "forgeflow_runtime.gate_evaluation",
    "forgeflow_runtime.stage_transition",
    "forgeflow_runtime.orchestrator",
]


def check_runtime_availability() -> RuntimeAvailability:
    """Probe the environment and report whether the runtime is usable."""
    missing: list[str] = []
    for mod_name in _CORE_MODULES:
        try:
            __import__(mod_name, fromlist=["_"])
        except Exception:
            missing.append(mod_name)

    return RuntimeAvailability(
        runtime_available=len(missing) == 0,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        missing_modules=missing,
    )


# ---------------------------------------------------------------------------
# Mode resolution
# ---------------------------------------------------------------------------

def resolve_effective_mode(
    config: LightweightConfig,
    availability: RuntimeAvailability,
) -> EnforcementMode:
    """Determine the *effective* enforcement mode given environment state."""
    if not availability.runtime_available and config.fallback_to_soft:
        if config.mode == EnforcementMode.HYBRID:
            return EnforcementMode.HYBRID
        return EnforcementMode.SOFT
    return config.mode


# ---------------------------------------------------------------------------
# SKILL.md helpers
# ---------------------------------------------------------------------------

def load_skill_md(path: str) -> str:
    """Read a SKILL.md file; return empty string when absent."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return ""


def build_lightweight_prompt(skill_paths: list[str], task_context: str) -> str:
    """Concatenate SKILL.md contents with task context for soft enforcement."""
    parts: list[str] = []
    for p in skill_paths:
        content = load_skill_md(p)
        if content:
            parts.append(content)
    parts.append(f"--- Task Context ---\n{task_context}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------

def should_use_gate(mode: EnforcementMode, complexity: str) -> bool:
    """Decide whether a runtime gate should fire for a given complexity."""
    if mode == EnforcementMode.HARD:
        return True
    if mode == EnforcementMode.SOFT:
        return False
    # HYBRID: only gate medium and above
    return complexity in ("medium", "large", "large_high_risk")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def format_mode_report(
    config: LightweightConfig,
    availability: RuntimeAvailability,
    effective: EnforcementMode,
) -> str:
    """Return a human-readable summary of the current mode configuration."""
    lines: list[str] = [
        f"Enforcement mode: {effective.value}",
        f"Configured mode:  {config.mode.value}",
        f"Runtime available: {availability.runtime_available}",
        f"Python version:    {availability.python_version}",
        f"Stages enabled:    {', '.join(config.stages_enabled)}",
        f"SKILL.md paths:    {len(config.skill_md_paths)} file(s)",
    ]
    if not availability.runtime_available:
        lines.append(
            f"Missing modules:  {', '.join(availability.missing_modules) or 'none detected'}",
        )
    gate_active = should_use_gate(effective, "medium")
    lines.append(f"Gates active:     {gate_active}")
    return "\n".join(lines)
