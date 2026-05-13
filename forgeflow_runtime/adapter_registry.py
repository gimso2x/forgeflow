"""Adapter registry — auto-discovers adapters from manifest.yaml files.

Scans ``adapters/targets/<name>/manifest.yaml`` and exposes a typed registry.
No external dependencies — ships a minimal YAML subset parser for flat manifests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Minimal YAML subset parser (flat scalars + string lists only)
# ---------------------------------------------------------------------------

def _parse_yaml_manifest(text: str) -> dict[str, object]:
    """Parse the subset of YAML used by adapter manifests.

    Supports:
    - ``key: value``  (scalar)
    - ``key:`` followed by indented ``  - item`` (string list)
    - Comments (``#``) and blank lines are ignored.

    This deliberately does **not** handle nested mappings beyond one level,
    quotes, multiline scalars, or anchors — manifest.yaml doesn't need them.
    """
    result: dict[str, object] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Top-level key: value
        m = re.match(r"^(\w[\w_-]*)\s*:\s*(.*?)\s*$", line)
        if m:
            key, val = m.group(1), m.group(2)
            if val:
                result[key] = val
            else:
                # List block — collect subsequent indented list items
                items: list[str] = []
                i += 1
                while i < len(lines):
                    inner = lines[i]
                    inner_stripped = inner.strip()
                    if not inner_stripped or inner_stripped.startswith("#"):
                        i += 1
                        continue
                    item_m = re.match(r"^\s+-\s+(.+)$", inner)
                    if item_m:
                        items.append(item_m.group(1).strip())
                        i += 1
                    else:
                        break
                result[key] = items
                continue  # already advanced i
        i += 1
    return result


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AdapterInfo:
    """Parsed metadata for a single adapter target."""

    name: str
    manifest_path: Path
    runtime_type: str
    generated_filename: str
    recommended_location: str
    surface_style: str
    handoff_format: str
    supports_roles: tuple[str, ...]
    agents_dir: Path | None
    hooks_dir: Path | None
    rules_dir: Path | None


@dataclass
class AdapterRegistry:
    """Auto-discovers adapter targets by scanning manifest.yaml files."""

    targets_dir: Path
    _adapters: dict[str, AdapterInfo] = field(default_factory=dict, repr=False, init=False)

    def __post_init__(self) -> None:
        self._scan()

    # -- public API ----------------------------------------------------------

    def get(self, name: str) -> AdapterInfo:
        """Look up an adapter by name.  Raises ``KeyError`` if not found."""
        try:
            return self._adapters[name]
        except KeyError:
            available = ", ".join(sorted(self._adapters)) or "(none)"
            raise KeyError(f"unknown adapter {name!r}; available: {available}") from None

    def list_adapters(self) -> list[str]:
        """Return sorted list of registered adapter names."""
        return sorted(self._adapters)

    def agent_prompt_path(self, adapter_name: str, role: str) -> Path | None:
        """Resolve the path to an agent prompt file for *role* under *adapter*.

        File naming convention: ``agents/forgeflow-<role>.md``
        """
        info = self.get(adapter_name)
        if role not in info.supports_roles:
            return None
        if info.agents_dir is None:
            return None
        return info.agents_dir / f"forgeflow-{role}.md"

    def has_adapter(self, name: str) -> bool:
        return name in self._adapters

    # -- internals -----------------------------------------------------------

    def _scan(self) -> None:
        if not self.targets_dir.is_dir():
            return
        for subdir in sorted(self.targets_dir.iterdir()):
            if not subdir.is_dir():
                continue
            manifest_path = subdir / "manifest.yaml"
            if not manifest_path.exists():
                continue
            try:
                info = self._parse_manifest(subdir.name, manifest_path)
                if not info.name or not info.runtime_type:
                    continue
            except Exception:
                # Skip malformed manifests silently — they may be WIP adapters
                continue
            self._adapters[info.name] = info

    @staticmethod
    def _parse_manifest(dir_name: str, manifest_path: Path) -> AdapterInfo:
        raw = _parse_yaml_manifest(manifest_path.read_text(encoding="utf-8"))
        name = raw.get("name", dir_name)
        supports_roles = tuple(raw.get("supports_roles", []))
        adapter_dir = manifest_path.parent

        agents_dir = adapter_dir / "agents"
        hooks_dir = adapter_dir / "hooks"
        rules_dir = adapter_dir / "rules"

        return AdapterInfo(
            name=str(name),
            manifest_path=manifest_path,
            runtime_type=str(raw.get("runtime_type", "")),
            generated_filename=str(raw.get("generated_filename", "")),
            recommended_location=str(raw.get("recommended_location", "")),
            surface_style=str(raw.get("surface_style", "")),
            handoff_format=str(raw.get("handoff_format", "")),
            supports_roles=supports_roles,
            agents_dir=agents_dir if agents_dir.is_dir() else None,
            hooks_dir=hooks_dir if hooks_dir.is_dir() else None,
            rules_dir=rules_dir if rules_dir.is_dir() else None,
        )
