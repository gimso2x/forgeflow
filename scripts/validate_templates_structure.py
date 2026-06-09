#!/usr/bin/env python3
"""Validate that all templates exist on disk and are documented in README.

Also verifies Makefile TEMPLATES list matches scripts/template_manifest.py.
"""
from __future__ import annotations

import pathlib
import re
import sys

from template_manifest import TEMPLATES

root = pathlib.Path(".")

readme_text = (root / "README.md").read_text(encoding="utf-8")

for t in TEMPLATES:
    tmpl_path = root / "templates" / t
    if not tmpl_path.exists():
        print(f"ERROR: Missing template templates/{t}")
        sys.exit(1)
    if t not in readme_text:
        print(f"ERROR: README must document template {t}")
        sys.exit(1)

if "make validate-templates validate-template-refs" not in readme_text:
    print("ERROR: README local validation docs must include focused template validation bundle")
    sys.exit(1)

makefile_text = (root / "Makefile").read_text(encoding="utf-8")
makefile_match = re.search(
    r"^TEMPLATES := \\?\n((?:\t[^\n]+\n)+)",
    makefile_text,
    re.MULTILINE,
)
if not makefile_match:
    print("ERROR: Makefile TEMPLATES block not found")
    sys.exit(1)

makefile_templates = re.findall(r"\t(\S+\.md|\S+\.json)", makefile_match.group(1))
if makefile_templates != TEMPLATES:
    print("ERROR: Makefile TEMPLATES list diverges from scripts/template_manifest.py")
    only_make = sorted(set(makefile_templates) - set(TEMPLATES))
    only_manifest = sorted(set(TEMPLATES) - set(makefile_templates))
    if only_make:
        print(f"  - Makefile only: {', '.join(only_make)}")
    if only_manifest:
        print(f"  - manifest only: {', '.join(only_manifest)}")
    sys.exit(1)

print("OK: All templates exist and are documented in README")
