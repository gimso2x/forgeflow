#!/usr/bin/env python3
"""Lightweight heuristic scanner for policy smells.

Warning-only by default. Regex is useful for triage, not for pretending
heuristics can replace review judgment.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INCLUDE = ("*.py", "*.json", "*.yaml", "*.yml")
DEFAULT_EXCLUDE_PARTS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
DEFAULT_EXCLUDE_DIR_NAMES = {"policy", "prompts", "skills", "tests"}
DEFAULT_EXCLUDE_FILES = {"scripts/policy_scan.py"}


@dataclass(frozen=True)
class Rule:
    code: str
    description: str
    pattern: re.Pattern[str]


RULES = (
    Rule(
        code="silent_fallback",
        description="possible silent fallback wording",
        pattern=re.compile(
            r"\b(?:fallback to|silently fall back|default to legacy|if missing, use legacy)\b",
            re.IGNORECASE,
        ),
    ),
    Rule(
        code="dual_write",
        description="possible dual-write wording",
        pattern=re.compile(
            r"\b(?:also write to|write both|dual[- ]write|mirror to legacy)\b",
            re.IGNORECASE,
        ),
    ),
    Rule(
        code="shadow_path",
        description="possible alternate ownership path wording",
        pattern=re.compile(
            r"\b(?:legacy path|alternate path|shadow path|compat path)\b",
            re.IGNORECASE,
        ),
    ),
)


def _should_skip(path: Path, root: Path) -> bool:
    if any(part in DEFAULT_EXCLUDE_PARTS for part in path.parts):
        return True
    rel = str(path.relative_to(root))
    rel_parts = Path(rel).parts
    if any(part in DEFAULT_EXCLUDE_DIR_NAMES for part in rel_parts[:-1]):
        return True
    if rel in DEFAULT_EXCLUDE_FILES:
        return True
    return False


def _iter_files(root: Path, include: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for pattern in include:
        for path in root.rglob(pattern):
            if not path.is_file():
                continue
            if _should_skip(path, root):
                continue
            files.append(path)
    return sorted(set(files))


def scan_paths(root: Path, include: tuple[str, ...] = DEFAULT_INCLUDE) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in _iter_files(root, include):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(lines, start=1):
            for rule in RULES:
                if rule.pattern.search(line):
                    findings.append(
                        {
                            "path": str(path.relative_to(root)),
                            "line": lineno,
                            "code": rule.code,
                            "description": rule.description,
                            "text": line.strip(),
                        }
                    )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=str(DEFAULT_ROOT))
    parser.add_argument("--strict", action="store_true", help="exit non-zero when findings exist")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    findings = scan_paths(root)
    if not findings:
        print("policy-scan: no warning patterns found")
        return 0

    print(f"policy-scan: {len(findings)} warning(s) found")
    for finding in findings:
        print(f"WARN {finding['code']} {finding['path']}:{finding['line']} :: {finding['text']}")

    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
