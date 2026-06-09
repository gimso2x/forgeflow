#!/usr/bin/env python3
"""Validate skills/SKILLS.md inventory links and version table sync with SKILL.md frontmatter."""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(".")
SKILLS_ROOT = ROOT / "skills"
INVENTORY = SKILLS_ROOT / "SKILLS.md"
FRONTMATTER_VERSION_RE = re.compile(r"^version:\s*(.+)$", re.MULTILINE)
TABLE_ROW_RE = re.compile(
    r"\[`([^`]+)`\]\(([^)]+/SKILL\.md)\)\s*\|\s*([^|]+?)\s*\|",
)


def frontmatter_version(skill_path: pathlib.Path) -> str:
    text = skill_path.read_text(encoding="utf-8")
    match = FRONTMATTER_VERSION_RE.search(text.split("---", 2)[1] if text.startswith("---") else text)
    if not match:
        return ""
    return match.group(1).strip().strip('"').strip("'")


def main() -> int:
    failures: list[str] = []
    inventory = INVENTORY.read_text(encoding="utf-8")
    active = sorted(
        d.name for d in SKILLS_ROOT.iterdir() if d.is_dir() and not d.name.startswith("_")
    )
    targets = re.findall(r"\(([^)]+/SKILL\.md)\)", inventory)
    linked_names = sorted(
        pathlib.PurePosixPath(target).parts[0]
        for target in targets
        if (SKILLS_ROOT / target).is_file()
    )
    missing = sorted(set(active) - set(linked_names))
    stale = sorted(
        target
        for target in targets
        if not (SKILLS_ROOT / target).is_file()
        or pathlib.PurePosixPath(target).parts[0] not in active
    )
    if missing or stale:
        failures.append("skills/SKILLS.md inventory drift")
        if missing:
            failures.append(f"- missing active skills: {missing}")
        if stale:
            failures.append(f"- stale skill links: {stale}")

    for name, rel_path, table_version in TABLE_ROW_RE.findall(inventory):
        skill_path = SKILLS_ROOT / rel_path
        if not skill_path.is_file():
            continue
        actual = frontmatter_version(skill_path)
        expected = table_version.strip()
        if actual and expected and actual != expected:
            failures.append(
                f"skills/SKILLS.md version drift for {name}: table={expected!r} frontmatter={actual!r}"
            )

    if failures:
        print("ERROR: skills inventory validation failed")
        for failure in failures:
            print(failure if failure.startswith("-") else f"- {failure}")
        return 1
    print(f"OK: skills/SKILLS.md lists {len(active)} active skills with synced versions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
