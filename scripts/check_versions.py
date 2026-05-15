#!/usr/bin/env python3
"""Check that all version sources are consistent.

Exit 0 if all versions match, exit 1 with a report if they differ.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CLAUDE_PLUGIN_JSON = ROOT / ".claude-plugin" / "plugin.json"
CODEX_PLUGIN_JSON = ROOT / ".codex-plugin" / "plugin.json"
CODEX_ADAPTER_PLUGIN_JSON = ROOT / "adapters" / "targets" / "codex" / "plugin.json"
GEMINI_EXTENSION_JSON = ROOT / "gemini-extension.json"
MARKETPLACE_JSON = ROOT / ".claude-plugin" / "marketplace.json"
PYPROJECT_TOML = ROOT / "pyproject.toml"
README_MD = ROOT / "README.md"


def read_version_json(path: Path) -> str:
    return json.loads(path.read_text(encoding="utf-8"))["version"]


def read_version_pyproject(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        return "<not found>"
    return m.group(1)


def read_version_readme(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"현재 릴리즈(?:는|:) \*\*v([^*]+)\*\*", text)
    if not m:
        return None
    return m.group(1)


def main() -> int:
    sources: dict[str, str] = {}

    sources[".claude-plugin/plugin.json"] = read_version_json(CLAUDE_PLUGIN_JSON)
    sources[".codex-plugin/plugin.json"] = read_version_json(CODEX_PLUGIN_JSON)
    sources["adapters/targets/codex/plugin.json"] = read_version_json(CODEX_ADAPTER_PLUGIN_JSON)
    sources["gemini-extension.json"] = read_version_json(GEMINI_EXTENSION_JSON)
    sources["pyproject.toml"] = read_version_pyproject(PYPROJECT_TOML)

    readme_ver = read_version_readme(README_MD)
    if readme_ver:
        sources["README"] = readme_ver

    # marketplace metadata.version (optional)
    if MARKETPLACE_JSON.exists():
        marketplace = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
        mv = marketplace.get("metadata", {}).get("version")
        if mv:
            sources["marketplace.json metadata.version"] = mv

    versions = set(sources.values())

    if len(versions) == 1:
        ver = versions.pop()
        print(f"✓ All {len(sources)} version sources agree: {ver}")
        return 0

    print("✗ Version drift detected!")
    max_label = max(len(k) for k in sources)
    for label, version in sorted(sources.items()):
        print(f"  {label:<{max_label}}  →  {version}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
