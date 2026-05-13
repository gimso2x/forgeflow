#!/usr/bin/env python3
"""Migrate project-local evolution data to global storage.

Copies rules, audit logs, proposals, promotion decisions, and promoted rules
from <project>/.forgeflow/evolution/ to ~/.forgeflow/evolution/.

Usage:
    python3 scripts/migrate_evolution_global.py /path/to/project [--dry-run]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from forgeflow_runtime.evolution.paths import global_evolution_dir


SUBDIRS = [
    "rules",
    "retired-rules",
    "proposals",
    "proposal-approvals",
    "promotion-decisions",
    "promoted-rules",
]

SINGLE_FILES = ["audit-log.jsonl"]


def migrate(project_root: Path, *, dry_run: bool = False) -> list[str]:
    src = project_root / ".forgeflow" / "evolution"
    if not src.is_dir():
        print(f"No project-local evolution directory at {src}")
        return []

    dst = global_evolution_dir()
    migrated: list[str] = []

    for subdir in SUBDIRS:
        s = src / subdir
        if not s.is_dir():
            continue
        d = dst / subdir
        for f in sorted(s.iterdir()):
            target = d / f.name
            if target.exists():
                print(f"  SKIP (exists): {target}")
                continue
            if dry_run:
                print(f"  WOULD COPY: {f} -> {target}")
            else:
                d.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)
                print(f"  COPIED: {f.name} -> {target}")
            migrated.append(f.name)

    for fname in SINGLE_FILES:
        s = src / fname
        if not s.is_file():
            continue
        target = dst / fname
        if target.exists():
            # Append lines instead of overwriting
            if dry_run:
                print(f"  WOULD APPEND: {s} -> {target}")
            else:
                existing = target.read_text(encoding="utf-8")
                new = s.read_text(encoding="utf-8")
                if existing and not existing.endswith("\n"):
                    existing += "\n"
                target.write_text(existing + new, encoding="utf-8")
                print(f"  APPENDED: {fname} -> {target}")
            migrated.append(fname)
        else:
            if dry_run:
                print(f"  WOULD COPY: {s} -> {target}")
            else:
                dst.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, target)
                print(f"  COPIED: {fname} -> {target}")
            migrated.append(fname)

    return migrated


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate project-local evolution data to global storage")
    parser.add_argument("project_root", type=Path, help="Path to the project root")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    args = parser.parse_args()

    root = args.project_root.resolve()
    if not (root / ".forgeflow" / "evolution").is_dir():
        print(f"No evolution data found at {root / '.forgeflow' / 'evolution'}")
        sys.exit(1)

    print(f"Source:  {root / '.forgeflow' / 'evolution'}")
    print(f"Target:  {global_evolution_dir()}")
    print()

    migrated = migrate(root, dry_run=args.dry_run)
    print(f"\nTotal: {len(migrated)} items {'would be ' if args.dry_run else ''}migrated")


if __name__ == "__main__":
    main()
