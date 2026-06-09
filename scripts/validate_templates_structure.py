#!/usr/bin/env python3
"""Validate that all templates exist on disk and are documented in README.

Extracted from the Makefile validate-templates target (inline shell logic).
"""
import pathlib
import sys

root = pathlib.Path(".")

TEMPLATES = [
    "brief.md",
    "project-draft.md",
    "plan.md",
    "review-report.md",
    "implementation-notes.md",
    "input-source.md",
    "normalized-input.md",
    "eval-record.md",
    "roadmap.md",
    "checkpoint.md",
    "run-state.json",
    "ledger.md",
    "evolution-rule.md",
    "ship-summary.md",
    "fact-extraction.md",
    "telemetry-event.md",
    "metrics-dashboard.md",
    "evidence-manifest.md",
    "re-execution-conditions.md",
]

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

print("OK: All templates exist and are documented in README")
