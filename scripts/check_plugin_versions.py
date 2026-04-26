#!/usr/bin/env python3
"""Fail fast when supported plugin release metadata drifts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from release import MARKETPLACE_JSON as MARKETPLACE
from release import PLUGIN_JSON as CLAUDE_PLUGIN
from release import SUPPORTED_PLUGIN_MANIFESTS

ROOT = Path(__file__).resolve().parents[1]
UNSUPPORTED_PLUGIN_MANIFESTS = [ROOT / ".cursor-plugin" / "plugin.json"]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def unsupported_manifest_errors(paths: list[Path]) -> list[str]:
    return [f"{_display_path(path)}: unsupported plugin manifest must be removed" for path in paths if path.exists()]


def supported_manifest_errors(paths: list[Path]) -> list[str]:
    return [f"{_display_path(path)}: supported plugin manifest is missing" for path in paths if not path.exists()]


def plugin_metadata_errors(manifests: dict[Path, dict], marketplace: dict) -> list[str]:
    claude = manifests[CLAUDE_PLUGIN] if CLAUDE_PLUGIN in manifests else manifests[Path(".claude-plugin/plugin.json")]
    expected_name = claude["name"]
    expected_version = claude["version"]
    expected_homepage = claude.get("homepage", claude["repository"])
    expected_repository = claude["repository"]
    expected_license = claude["license"]

    errors: list[str] = []
    for path, manifest in manifests.items():
        rel = _display_path(path)
        if manifest.get("name") != expected_name:
            errors.append(f"{rel}: name {manifest.get('name')!r} != {expected_name!r}")
        if manifest.get("version") != expected_version:
            errors.append(f"{rel}: version {manifest.get('version')!r} != {expected_version!r}")
        if manifest.get("homepage", expected_homepage) != expected_homepage:
            errors.append(f"{rel}: homepage {manifest.get('homepage')!r} != {expected_homepage!r}")
        if manifest.get("repository") != expected_repository:
            errors.append(f"{rel}: repository {manifest.get('repository')!r} != {expected_repository!r}")
        if manifest.get("license") != expected_license:
            errors.append(f"{rel}: license {manifest.get('license')!r} != {expected_license!r}")

    marketplace_rel = _display_path(MARKETPLACE)
    marketplace_name = marketplace.get("name")
    if marketplace_name != expected_name:
        errors.append(f"{marketplace_rel}: name {marketplace_name!r} != {expected_name!r}")
    for index, plugin in enumerate(marketplace.get("plugins", [])):
        plugin_name = plugin.get("name")
        if plugin_name != expected_name:
            errors.append(f"{marketplace_rel}: plugins[{index}].name {plugin_name!r} != {expected_name!r}")

    marketplace_version = marketplace.get("metadata", {}).get("version")
    if marketplace_version != expected_version:
        errors.append(f"{marketplace_rel}: metadata.version {marketplace_version!r} != {expected_version!r}")
    return errors


def main() -> int:
    support_errors = [
        *unsupported_manifest_errors(UNSUPPORTED_PLUGIN_MANIFESTS),
        *supported_manifest_errors(SUPPORTED_PLUGIN_MANIFESTS),
    ]
    if support_errors:
        for error in support_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    manifests = {path: load_json(path) for path in SUPPORTED_PLUGIN_MANIFESTS}
    marketplace = load_json(MARKETPLACE)
    expected_version = manifests[CLAUDE_PLUGIN]["version"]
    errors = plugin_metadata_errors(manifests, marketplace)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"plugin versions synchronized: {expected_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
