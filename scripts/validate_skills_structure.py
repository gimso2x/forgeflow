#!/usr/bin/env python3
"""Validate skills directory structure, frontmatter, inventory, and root SKILL.md linkage.

Extracted from the Makefile validate-skills inline shell logic (#155).
Steps 1-8 correspond to the original Makefile checks.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(".")
SKILLS_ROOT = ROOT / "skills"
ROOT_SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"


def _frontmatter_field(skill_path: pathlib.Path, field: str) -> str:
    """Extract a top-level frontmatter field value from a markdown file."""
    text = skill_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    failures: list[str] = []

    # Steps 1-5: iterate skill directories
    for skill_dir in sorted(SKILLS_ROOT.iterdir()):
        if not skill_dir.is_dir():
            continue
        name = skill_dir.name
        if name.startswith("_"):
            continue

        skill_file = skill_dir / "SKILL.md"

        # Step 1: SKILL.md must exist
        if not skill_file.is_file():
            failures.append(f"Missing SKILL.md in skills/{name}/")
            continue

        # Step 2: frontmatter name must match directory name
        actual_name = _frontmatter_field(skill_file, "name")
        if actual_name != name:
            failures.append(
                f"skills/{name}/SKILL.md name must be {name} (got {actual_name or '<missing>'})"
            )

        # Step 3: description must be non-empty
        text = skill_file.read_text(encoding="utf-8")
        if not re.search(r"^description: .+", text, re.MULTILINE):
            failures.append(
                f"skills/{name}/SKILL.md must define a non-empty description in frontmatter"
            )

        # Step 4: validate_prompt: | must exist
        if "validate_prompt: |" not in text:
            failures.append(
                f"skills/{name}/SKILL.md must define validate_prompt: | in frontmatter"
            )

    # Step 5: delegate to validate_skills_inventory.py
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_skills_inventory.py")],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        failures.append(f"validate_skills_inventory.py failed: {result.stdout.strip()} {result.stderr.strip()}")

    # Step 6: root SKILL.md must point to skills/forgeflow/SKILL.md
    if ROOT_SKILL.is_file():
        root_text = ROOT_SKILL.read_text(encoding="utf-8")
        if "skills/forgeflow/SKILL.md" not in root_text:
            failures.append("root SKILL.md must point to the canonical forgeflow skill")
        # Step 7: root SKILL.md must have 'Claude marketplace entry'
        if "Claude marketplace entry" not in root_text:
            failures.append(
                "root SKILL.md must stay a marketplace summary, not the canonical contract"
            )
    else:
        failures.append("root SKILL.md is missing")

    # Step 8: README must document validation targets
    if README.is_file():
        readme_text = README.read_text(encoding="utf-8")
        if "make validate-skills" not in readme_text:
            failures.append(
                "README local validation docs must include focused skills validation"
            )
        if "root SKILL.md marketplace summary" not in readme_text:
            failures.append(
                "README local validation docs must mention root SKILL marketplace summary coverage"
            )
    else:
        failures.append("README.md is missing")

    if failures:
        for f in failures:
            print(f"ERROR: {f}")
        return 1

    print(
        "OK: All public skills have SKILL.md with name, description, validate_prompt, "
        "inventory coverage, and root marketplace summary linkage"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
