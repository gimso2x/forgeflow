#!/usr/bin/env python3
"""Validate release-version sync and skill schema-version documentation."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

VERSIONED_JSON_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (".claude-plugin/plugin.json", ("version",)),
    (".codex-plugin/plugin.json", ("version",)),
    (".cursor-plugin/plugin.json", ("version",)),
    ("gemini-extension.json", ("version",)),
    (".claude-plugin/marketplace.json", ("metadata", "version")),
)

SCHEMA_VERSION_FRAGMENTS = (
    "Per-skill frontmatter `version`",
    "skill schema",
    "릴리즈 `VERSION`과 별개",
)


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def frontmatter_version(relative_path: str) -> str:
    lines = read_text(relative_path).splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        if line.strip() == "---":
            return ""
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return ""


def json_string_field(relative_path: str, keys: tuple[str, ...]) -> str:
    value = json.loads(read_text(relative_path))
    for key in keys:
        if not isinstance(value, dict):
            return ""
        value = value.get(key, "")
    return value if isinstance(value, str) else ""


def has_schema_version_contract(text: str) -> bool:
    return all(fragment in text for fragment in SCHEMA_VERSION_FRAGMENTS)


def main() -> int:
    failures: list[str] = []
    expected = read_text("VERSION").strip()

    if not expected:
        failures.append("VERSION: release version must be non-empty")

    def check(label: str, actual: str) -> None:
        if actual != expected:
            shown = actual or "<missing>"
            failures.append(f"{label}: expected {expected}, got {shown}")

    if expected:
        check("SKILL.md", frontmatter_version("SKILL.md"))
        for relative_path, keys in VERSIONED_JSON_FIELDS:
            label = relative_path
            if keys != ("version",):
                label = f"{relative_path} {'.'.join(keys)}"
            check(label, json_string_field(relative_path, keys))

        changelog = read_text("CHANGELOG.md")
        if f"## [{expected}]" not in changelog:
            failures.append(f"CHANGELOG.md: missing ## [{expected}] section")

    readme = read_text("README.md")
    if re.search(r"^(현재 릴리즈|Current release):", readme, re.MULTILINE):
        failures.append("README.md: remove hardcoded current release line")
    if "VERSION" not in readme:
        failures.append("README.md: release policy must reference VERSION")
    if not has_schema_version_contract(readme):
        failures.append(
            "README.md: must document public skill frontmatter version as a "
            "skill schema version separate from release VERSION"
        )

    root_skill = read_text("SKILL.md")
    if not has_schema_version_contract(root_skill):
        failures.append(
            "SKILL.md: must document per-skill frontmatter version as a "
            "skill schema version separate from release VERSION"
        )

    if failures:
        print("ERROR: Version consistency check failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(
        f"OK: Release versions match VERSION={expected} "
        "and skill schema version contract is documented"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
