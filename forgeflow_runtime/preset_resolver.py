"""Preset resolver — layered prompt override system.

Loads canonical (core) prompts from ``prompts/canonical/`` and optionally
merges them with project-level overrides discovered in
``.forgeflow/presets/``.

Composition strategies
----------------------
- **replace**  (``planner.md``)          → override replaces core entirely
- **append**   (``planner.append.md``)   → override appended after core
- **prepend**  (``planner.prepend.md``)  → override prepended before core
- **wrap**     (``planner.wrap.md``)     → ``{CORE_TEMPLATE}`` placeholder replaced with core

When no override exists the core prompt is returned unchanged, preserving
100 % backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

# ── Constants ────────────────────────────────────────────────────────────────

ROLE_TO_FILENAME: dict[str, str] = {
    "coordinator": "coordinator.md",
    "planner": "planner.md",
    "worker": "worker.md",
    "spec-reviewer": "spec-reviewer.md",
    "quality-reviewer": "quality-reviewer.md",
}

COMPOSITION_SUFFIXES: dict[str, str] = {
    ".append.md": "append",
    ".prepend.md": "prepend",
    ".wrap.md": "wrap",
}

CORE_PLACEHOLDER = "{CORE_TEMPLATE}"


# ── Data structures ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PresetLayer:
    """A single layer in the preset resolution stack."""

    name: str       # "override" | "core"
    path: Path
    strategy: str   # "replace" | "append" | "prepend" | "wrap" | "core"
    priority: int   # higher = wins


class PresetError(Exception):
    """Raised when preset resolution fails (missing core, bad wrap, etc.)."""


# ── Resolver ─────────────────────────────────────────────────────────────────

class PresetResolver:
    """Resolve the final prompt for a role by merging core + override layers.

    Parameters
    ----------
    core_dir:
        Path to ``prompts/canonical/``.
    override_dir:
        Path to ``.forgeflow/presets/``.  ``None`` means no overrides
        (pure core mode).
    """

    def __init__(self, core_dir: Path, override_dir: Path | None = None) -> None:
        self._core_dir = core_dir
        self._override_dir = override_dir

    # ── Public API ───────────────────────────────────────────────────────

    def resolve(self, role: str) -> str:
        """Return the final prompt for *role*, merging core + override."""
        core = self._load_core(role)
        override_data = self._find_override(role)
        if override_data is None:
            return core
        override_text, strategy = override_data
        return self._compose(core, override_text, strategy)

    def resolve_template(self, template_name: str) -> str:
        """Resolve a non-role template (e.g. ADR.md, ARCHITECTURE.md).

        Looks for ``<template_name>`` in the core templates directory and
        applies the same override strategy if a matching preset exists.
        """
        core_path = self._core_dir / template_name
        if not core_path.exists():
            raise PresetError(f"core template not found: {core_path}")

        core = core_path.read_text(encoding="utf-8").strip()
        override_data = self._find_override_by_filename(template_name)
        if override_data is None:
            return core
        override_text, strategy = override_data
        return self._compose(core, override_text, strategy)

    def has_override(self, role: str) -> bool:
        """Check whether *role* has an override preset."""
        return self._find_override(role) is not None

    def list_overrides(self) -> list[str]:
        """List roles that have overrides."""
        if self._override_dir is None or not self._override_dir.is_dir():
            return []
        roles: list[str] = []
        for role in ROLE_TO_FILENAME:
            if self._find_override(role) is not None:
                roles.append(role)
        return sorted(roles)

    # ── Internal ─────────────────────────────────────────────────────────

    def _load_core(self, role: str) -> str:
        filename = ROLE_TO_FILENAME.get(role)
        if filename is None:
            raise PresetError(f"unknown role: {role}")
        path = self._core_dir / filename
        if not path.exists():
            raise PresetError(f"core prompt missing for role {role}: {path}")
        return path.read_text(encoding="utf-8").strip()

    def _find_override(self, role: str) -> tuple[str, str] | None:
        """Find an override for *role*.  Returns (content, strategy) or None."""
        filename = ROLE_TO_FILENAME.get(role)
        if filename is None:
            return None
        return self._find_override_by_filename(filename)

    def _find_override_by_filename(self, filename: str) -> tuple[str, str] | None:
        """Find override by canonical filename.  Returns (content, strategy)."""
        if self._override_dir is None or not self._override_dir.is_dir():
            return None

        # Priority: wrap > prepend > append > replace
        # (more specific suffixes checked first)
        for suffix, strategy in COMPOSITION_SUFFIXES.items():
            override_name = filename.replace(".md", suffix)
            override_path = self._override_dir / override_name
            if override_path.is_file():
                return (
                    override_path.read_text(encoding="utf-8").strip(),
                    strategy,
                )

        # Plain replace (exact filename match)
        replace_path = self._override_dir / filename
        if replace_path.is_file():
            return (
                replace_path.read_text(encoding="utf-8").strip(),
                "replace",
            )

        return None

    @staticmethod
    def _compose(core: str, override: str, strategy: str) -> str:
        """Merge *core* and *override* according to *strategy*."""
        if strategy == "replace":
            return override
        if strategy == "append":
            return core + "\n\n" + override
        if strategy == "prepend":
            return override + "\n\n" + core
        if strategy == "wrap":
            if CORE_PLACEHOLDER not in override:
                raise PresetError(
                    f"wrap strategy requires {CORE_PLACEHOLDER!r} placeholder "
                    f"in override, but it was not found"
                )
            return override.replace(CORE_PLACEHOLDER, core)
        raise PresetError(f"unknown composition strategy: {strategy}")


def make_preset_resolver(project_dir: Path | None = None) -> PresetResolver:
    """Factory: build a PresetResolver with sensible defaults.

    *core_dir* is always ``<repo_root>/prompts/canonical/``.
    *override_dir* is ``<project_dir>/.forgeflow/presets/`` when *project_dir*
    is given and the directory exists, otherwise ``None``.
    """
    repo_root = Path(__file__).resolve().parents[1]
    core_dir = repo_root / "prompts" / "canonical"

    override_dir: Path | None = None
    if project_dir is not None:
        candidate = project_dir / ".forgeflow" / "presets"
        if candidate.is_dir():
            override_dir = candidate

    return PresetResolver(core_dir=core_dir, override_dir=override_dir)
