#!/usr/bin/env python3
"""Validate repo-local path references in AI-facing context docs.

This is intentionally smaller than the external ai-readiness scorer: it blocks
untrusted repo-local references without treating install-target examples,
vendored upstream notes, or generated adapter output as canonical context.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CONTEXT_FILE_NAMES = {"README.md", "AGENTS.md", "CLAUDE.md", "CODEX.md"}
IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    "target",
    "__pycache__",
}
IGNORED_CONTEXT_PREFIXES = (
    "adapters/generated/",
    "docs/upstream/",
)
EXAMPLE_REF_PREFIXES = (
    "/path/to/",
    "path/to/",
    "project/",
)
EXAMPLE_REF_EXACT = {
    "./CLAUDE.md",
    "./CODEX.md",
    "docs/forgeflow-team-init.md",
    ".claude/settings.json",
    ".claude/hooks/forgeflow/basic_safety_guard.py",
    ".claude/agents/forgeflow-coordinator.md",
    ".codex/forgeflow/forgeflow-coordinator.md",
    ".codex/rules/forgeflow-nextjs-worker.mdc",
}
EXAMPLE_REF_CONTAINS = (
    ".forgeflow/tasks/my-task-001/",
)

PATH_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_./<>{}~-])"
    r"((?:\./|/|\.[A-Za-z0-9_-]+/|[A-Za-z0-9_]+/)"
    r"[A-Za-z0-9_./-]+\."
    r"(?:json|yaml|yml|toml|tsx|jsx|py|ts|js|md|sql|html|css|sh|go|rs|java|kt|rb|php))"
    r"(?![A-Za-z0-9_./-])"
)


@dataclass(frozen=True)
class BrokenReference:
    file: str
    line: int
    reference: str

    def render(self) -> str:
        return f"{self.file}:{self.line}: {self.reference}"


def iter_context_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in IGNORED_DIRS and not dirname.startswith(".")
        ]
        for filename in filenames:
            if filename not in CONTEXT_FILE_NAMES:
                continue
            path = Path(dirpath) / filename
            rel = path.relative_to(root).as_posix()
            if rel.startswith(IGNORED_CONTEXT_PREFIXES):
                continue
            yield path


def is_example_reference(reference: str) -> bool:
    normalized = reference.removeprefix("./")
    if reference in EXAMPLE_REF_EXACT or normalized in EXAMPLE_REF_EXACT:
        return True
    if normalized.startswith(EXAMPLE_REF_PREFIXES):
        return True
    return any(marker in normalized for marker in EXAMPLE_REF_CONTAINS)


def reference_exists(root: Path, context_file: Path, reference: str) -> bool:
    if reference.startswith("/"):
        # Absolute sample paths are not repo-local evidence.
        return is_example_reference(reference)

    normalized = reference.removeprefix("./")
    candidates = [root / normalized, context_file.parent / reference]
    return any(candidate.exists() for candidate in candidates)


def find_broken_references(root: Path) -> list[BrokenReference]:
    broken: list[BrokenReference] = []
    for context_file in sorted(iter_context_files(root)):
        text = context_file.read_text(encoding="utf-8", errors="ignore")
        seen: set[str] = set()
        for match in PATH_REF_RE.finditer(text):
            reference = match.group(1)
            if "://" in text[max(0, match.start() - 16) : match.start()] or (
                reference.startswith("//") and match.start() > 0 and text[match.start() - 1] == ":"
            ):
                continue
            if reference in seen or is_example_reference(reference):
                continue
            seen.add(reference)
            if reference_exists(root, context_file, reference):
                continue
            line = text.count("\n", 0, match.start()) + 1
            broken.append(
                BrokenReference(
                    file=context_file.relative_to(root).as_posix(),
                    line=line,
                    reference=reference,
                )
            )
    return broken


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Repository root to validate")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    broken = find_broken_references(root)
    if broken:
        print("CONTEXT PATH VALIDATION: FAIL")
        for item in broken:
            print(f"- {item.render()}")
        return 1

    print("CONTEXT PATH VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
