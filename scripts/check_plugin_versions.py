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


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    claude = load_json(CLAUDE_PLUGIN)
    expected_name = claude["name"]
    expected_version = claude["version"]
    expected_repository = claude["repository"]
    expected_license = claude["license"]

    errors: list[str] = []
    for path in SUPPORTED_PLUGIN_MANIFESTS:
        manifest = load_json(path)
        rel = path.relative_to(ROOT)
        if manifest.get("name") != expected_name:
            errors.append(f"{rel}: name {manifest.get('name')!r} != {expected_name!r}")
        if manifest.get("version") != expected_version:
            errors.append(f"{rel}: version {manifest.get('version')!r} != {expected_version!r}")
        if manifest.get("repository") != expected_repository:
            errors.append(f"{rel}: repository {manifest.get('repository')!r} != {expected_repository!r}")
        if manifest.get("license") != expected_license:
            errors.append(f"{rel}: license {manifest.get('license')!r} != {expected_license!r}")

    marketplace = load_json(MARKETPLACE)
    marketplace_version = marketplace.get("metadata", {}).get("version")
    if marketplace_version != expected_version:
        errors.append(f"{MARKETPLACE.relative_to(ROOT)}: metadata.version {marketplace_version!r} != {expected_version!r}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"plugin versions synchronized: {expected_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
