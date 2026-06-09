#!/usr/bin/env python3
"""Validate ship safety phrases and dogfooding doc linkage/guards."""
from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(".")


def _check_ship_safety() -> int:
    ship_skill = ROOT / "skills" / "ship" / "SKILL.md"
    if not ship_skill.exists():
        print("ERROR: skills/ship/SKILL.md not found")
        return 1

    text = ship_skill.read_text(encoding="utf-8")
    checks = [
        ("Do not remove or discard yet",
         "ship skill must preserve worktrees before option-specific confirmation"),
        ("Type 'discard' to confirm.",
         "ship skill must require exact discard confirmation"),
        ("Never delete unrelated dirty working tree files",
         "ship skill must protect unrelated dirty working tree files"),
    ]
    failures = 0
    for phrase, message in checks:
        if phrase not in text:
            print(f"ERROR: {message}")
            failures += 1

    if failures:
        return 1

    print("OK: Ship skill protects worktrees and destructive cleanup")
    return 0


def _check_dogfooding_docs() -> int:
    failures = 0

    readme = ROOT / "README.md"
    readme_text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    if "[docs/dogfooding.md](docs/dogfooding.md)" not in readme_text:
        print("ERROR: README must link tracked .forgeflow fixture guidance")
        failures += 1

    dogfooding = ROOT / "docs" / "dogfooding.md"
    if not dogfooding.exists():
        print("ERROR: docs/dogfooding.md not found")
        return 1

    text = dogfooding.read_text(encoding="utf-8")
    phrases = [
        ("intentionally tracked",
         "dogfooding docs must say tracked task folders are intentional"),
        ("Normal consumer projects should keep",
         "dogfooding docs must distinguish consumer project behavior"),
        ("Do not run broad cleanup commands",
         "dogfooding docs must forbid broad destructive cleanup"),
        ("inspect `git status --short --ignored` first",
         "dogfooding docs must require ignored-status inspection before cleanup"),
    ]
    for phrase, message in phrases:
        if phrase not in text:
            print(f"ERROR: {message}")
            failures += 1

    if failures:
        return 1

    print("OK: Dogfooding fixture docs are linked and guarded")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate ship safety and dogfooding doc guards")
    parser.add_argument("--ship-safety", action="store_true",
                        help="Check ship SKILL.md safety phrases")
    parser.add_argument("--dogfooding", action="store_true",
                        help="Check dogfooding docs linkage and guards")
    args = parser.parse_args()

    # Run both by default when neither flag is specified
    run_ship = args.ship_safety or (not args.ship_safety and not args.dogfooding)
    run_dog = args.dogfooding or (not args.ship_safety and not args.dogfooding)

    rc = 0
    if run_ship:
        rc |= _check_ship_safety()
    if run_dog:
        rc |= _check_dogfooding_docs()
    return rc


if __name__ == "__main__":
    sys.exit(main())
