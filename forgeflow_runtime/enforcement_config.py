"""Enforcement strength selection for forgeflow pipelines.

Provides configurable enforcement levels (HARD / SOFT / HYBRID), per-stage
enable flags, and gate policies.  A minimal YAML-like parser (no pyyaml)
reads config from plain text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------

class EnforcementLevel(str, Enum):
    HARD = "hard"
    SOFT = "soft"
    HYBRID = "hybrid"


_DEFAULT_STAGES = ["clarify", "plan", "execute", "review"]


@dataclass(frozen=True)
class GateConfig:
    """Policy controlling gate behaviour."""

    require_artifact: bool = True
    allow_skip_below: str | None = None
    max_complexity_for_skip: str | None = None


@dataclass(frozen=True)
class StageConfig:
    """Per-stage configuration."""

    name: str
    enabled: bool = True
    gates_enabled: bool = True
    timeout_seconds: int = 300


@dataclass(frozen=True)
class ProjectEnforcement:
    """Top-level enforcement configuration for a project."""

    level: EnforcementLevel
    stages: list[StageConfig] = field(default_factory=list)
    gates: GateConfig = field(default_factory=GateConfig)
    project_root: str | None = None


# ---------------------------------------------------------------------------
# Minimal YAML-like parser
# ---------------------------------------------------------------------------

_BOOL_MAP: dict[str, bool] = {
    "true": True,
    "false": False,
    "yes": True,
    "no": False,
    "1": True,
    "0": False,
}


def _parse_bool(value: str) -> bool:
    return _BOOL_MAP[value.strip().lower()]


def parse_enforcement_config(text: str) -> ProjectEnforcement:
    """Parse a minimal YAML-like enforcement config into *ProjectEnforcement*.

    Supported sections: ``enforcement``, ``stages``, ``gates``.
    """
    level: EnforcementLevel = EnforcementLevel.HARD
    stage_names: list[str] = []
    gate_kwargs: dict[str, Any] = {}
    stages_seen = False

    current_section: str | None = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Detect top-level section headers (no leading whitespace in raw line)
        if raw_line[0] not in (" ", "\t") and re.match(r"^[a-z_]+:", stripped):
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()

            if key == "enforcement":
                level = EnforcementLevel(value.lower())
                current_section = None
            elif key == "stages":
                current_section = "stages"
                stages_seen = True
            elif key == "gates":
                current_section = "gates"
            else:
                current_section = None
            continue

        # Indented list items under stages
        if current_section == "stages" and stripped.startswith("- "):
            stage_names.append(stripped[2:].strip())
            continue

        # Key-value pairs under gates
        if current_section == "gates" and ":" in stripped:
            gkey, _, gval = stripped.partition(":")
            gkey = gkey.strip()
            gval = gval.strip()
            if gkey in ("require_artifact",):
                gate_kwargs[gkey] = _parse_bool(gval)
            elif gkey in ("allow_skip_below", "max_complexity_for_skip"):
                gate_kwargs[gkey] = gval if gval else None

    # Build stage configs
    if stages_seen:
        stages = [StageConfig(name=n) for n in stage_names]
    else:
        stages = [StageConfig(name=n) for n in _DEFAULT_STAGES]

    gates = GateConfig(**gate_kwargs) if gate_kwargs else GateConfig()

    return ProjectEnforcement(level=level, stages=stages, gates=gates)


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def is_stage_enabled(config: ProjectEnforcement, stage_name: str) -> bool:
    """Return *True* if *stage_name* is present and enabled in *config*."""
    for stage in config.stages:
        if stage.name == stage_name:
            return stage.enabled
    return False


def effective_enforcement_for_task(
    config: ProjectEnforcement,
    complexity: str,
) -> EnforcementLevel:
    """Return the effective enforcement level for a given *complexity*.

    * HARD → always HARD
    * SOFT → always SOFT
    * HYBRID → small→SOFT, medium/large→HARD
    """
    if config.level in (EnforcementLevel.HARD, EnforcementLevel.SOFT):
        return config.level
    # HYBRID
    if complexity == "small":
        return EnforcementLevel.SOFT
    return EnforcementLevel.HARD


# ---------------------------------------------------------------------------
# Validation & reporting
# ---------------------------------------------------------------------------

def validate_config(config: ProjectEnforcement) -> list[str]:
    """Return a list of validation errors (empty ⇒ valid)."""
    errors: list[str] = []
    enabled_count = sum(1 for s in config.stages if s.enabled)
    if enabled_count == 0:
        errors.append("At least one stage must be enabled")
    if not isinstance(config.level, EnforcementLevel):
        errors.append(f"Invalid enforcement level: {config.level!r}")
    return errors


def format_enforcement_report(config: ProjectEnforcement) -> str:
    """Return a human-readable summary of the enforcement config."""
    lines: list[str] = []
    lines.append(f"Enforcement: {config.level.value}")
    lines.append("Stages:")
    for stage in config.stages:
        marker = "✓" if stage.enabled else "✗"
        lines.append(f"  {marker} {stage.name} (gates={'on' if stage.gates_enabled else 'off'}, timeout={stage.timeout_seconds}s)")
    lines.append(f"Gates: require_artifact={config.gates.require_artifact}, "
                 f"allow_skip_below={config.gates.allow_skip_below}, "
                 f"max_complexity_for_skip={config.gates.max_complexity_for_skip}")
    return "\n".join(lines)
