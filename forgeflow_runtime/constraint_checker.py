"""Regex-based constraint / anti-pattern scanner for ForgeFlow quality gates.

Detects common code-quality issues (TODO/FIXME comments, hardcoded secrets,
print-debug statements, bare except blocks) and supports custom constraint
registries loaded from YAML.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Constraint:
    """A single anti-pattern rule."""

    id: str
    pattern: str
    reason: str
    suggestion: str
    category: str
    severity: str  # "error" | "warning"


@dataclass(frozen=True)
class Violation:
    """One matched constraint violation."""

    constraint_id: str
    file: str  # relative path
    line: int  # 1-indexed
    match: str  # matched text
    reason: str
    suggestion: str
    severity: str


@dataclass(frozen=True)
class ScanResult:
    """Aggregate result of a constraint scan."""

    violations: tuple[Violation, ...]
    files_scanned: int
    files_skipped: int
    duration_seconds: float


# ---------------------------------------------------------------------------
# Built-in constraints
# ---------------------------------------------------------------------------

DEFAULT_CONSTRAINTS: list[Constraint] = [
    Constraint(
        "no-todo",
        r"\bTODO\b",
        "TODO comment found",
        "Resolve or convert to issue ticket",
        "code-quality",
        "warning",
    ),
    Constraint(
        "no-fixme",
        r"\bFIXME\b",
        "FIXME comment found",
        "Fix the issue or document why it is deferred",
        "code-quality",
        "warning",
    ),
    Constraint(
        "no-hardcoded-secret",
        r'(?i)(password|secret|api_key|apikey|token)\s*=\s*["\'][^"\']{8,}["\']',
        "Possible hardcoded secret",
        "Use environment variables or secrets manager",
        "security",
        "error",
    ),
    Constraint(
        "no-print-debug",
        r"^\s*print\s*\(",
        "print() debugging statement",
        "Use logging module instead",
        "code-quality",
        "warning",
    ),
    Constraint(
        "no-empty-except",
        r"except\s*:\s*$",
        "Bare except block",
        "Specify exception type or at least log the error",
        "code-quality",
        "warning",
    ),
    Constraint(
        "no-empty-except-pass",
        r"except.*:\s*\n\s*pass\s*$",
        "Empty except block with pass",
        "Handle the exception or re-raise",
        "code-quality",
        "warning",
    ),
]

# Directories always skipped during scanning.
_DEFAULT_SKIP_DIRS: frozenset[str] = frozenset({
    "__pycache__",
    "node_modules",
    ".git",
    "vendor",
    "testdata",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
})

_BINARY_SIGNATURES = (
    b"\x00\x00",
    b"\xff\xd8\xff",
    b"\x89PNG",
    b"GIF8",
    b"\x7fELF",
    b"PK\x03\x04",
)


# ---------------------------------------------------------------------------
# Scanning helpers
# ---------------------------------------------------------------------------

def _is_binary(path: Path) -> bool:
    """Heuristic: check first bytes for common binary signatures."""
    try:
        with path.open("rb") as fh:
            header = fh.read(512)
    except OSError:
        return True
    if b"\x00" in header:
        return True
    for sig in _BINARY_SIGNATURES:
        if header.startswith(sig):
            return True
    return False


def _is_skip_dir(dir_name: str, extra_skip: frozenset[str]) -> bool:
    if dir_name.startswith("."):
        return True
    return dir_name in _DEFAULT_SKIP_DIRS | extra_skip


def _compile_constraint(c: Constraint) -> tuple[re.Pattern[str], Constraint]:
    return re.compile(c.pattern, re.MULTILINE), c


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_directory(
    directory: Path,
    constraints: list[Constraint] | None = None,
    *,
    extensions: list[str] | None = None,
    categories: list[str] | None = None,
    severities: list[str] | None = None,
    skip_dirs: list[str] | None = None,
    max_file_lines: int | None = None,
) -> ScanResult:
    """Scan *directory* for constraint violations.

    Parameters
    ----------
    directory:
        Root directory to walk.
    constraints:
        List of constraints to check.  Defaults to ``DEFAULT_CONSTRAINTS``.
    extensions:
        Only scan files with these suffixes (e.g. ``[".py", ".js"]``).
        ``None`` means all non-binary files.
    categories:
        Only apply constraints in these categories.  ``None`` means all.
    severities:
        Only apply constraints with these severities.  ``None`` means all.
    skip_dirs:
        Additional directory names to skip (on top of the built-in list).
    max_file_lines:
        If set, skip files longer than this many lines.
    """
    t0 = time.monotonic()

    if constraints is None:
        constraints = DEFAULT_CONSTRAINTS

    # Filter constraints
    if categories is not None:
        constraints = [c for c in constraints if c.category in categories]
    if severities is not None:
        constraints = [c for c in constraints if c.severity in severities]

    extra_skip = frozenset(skip_dirs) if skip_dirs else frozenset()
    ext_set = frozenset(extensions) if extensions else None

    compiled = [_compile_constraint(c) for c in constraints]
    violations: list[Violation] = []
    files_scanned = 0
    files_skipped = 0

    if not directory.is_dir():
        return ScanResult(
            violations=tuple(violations),
            files_scanned=0,
            files_skipped=0,
            duration_seconds=round(time.monotonic() - t0, 4),
        )

    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        if _is_binary(path):
            files_skipped += 1
            continue
        if ext_set is not None and path.suffix not in ext_set:
            files_skipped += 1
            continue
        # Check if any parent dir should be skipped
        rel = path.relative_to(directory)
        skip = False
        for part in rel.parts[:-1]:
            if _is_skip_dir(part, extra_skip):
                skip = True
                break
        if skip:
            files_skipped += 1
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            files_skipped += 1
            continue

        lines = text.splitlines()
        if max_file_lines is not None and len(lines) > max_file_lines:
            files_skipped += 1
            continue

        files_scanned += 1

        for lineno, line in enumerate(lines, start=1):
            for pat, constraint in compiled:
                m = pat.search(line)
                if m:
                    violations.append(
                        Violation(
                            constraint_id=constraint.id,
                            file=str(rel),
                            line=lineno,
                            match=m.group(),
                            reason=constraint.reason,
                            suggestion=constraint.suggestion,
                            severity=constraint.severity,
                        )
                    )

    return ScanResult(
        violations=tuple(violations),
        files_scanned=files_scanned,
        files_skipped=files_skipped,
        duration_seconds=round(time.monotonic() - t0, 4),
    )


def max_file_lines_check(directory: Path, max_lines: int) -> list[Violation]:
    """Return violations for every file exceeding *max_lines*."""
    violations: list[Violation] = []
    if not directory.is_dir():
        return violations

    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        if _is_binary(path):
            continue
        # Skip dirs
        rel = path.relative_to(directory)
        skip = False
        for part in rel.parts[:-1]:
            if _is_skip_dir(part, frozenset()):
                skip = True
                break
        if skip:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        line_count = len(text.splitlines())
        if line_count > max_lines:
            violations.append(
                Violation(
                    constraint_id="max-file-lines",
                    file=str(rel),
                    line=line_count,
                    match=f"File has {line_count} lines (max {max_lines})",
                    reason=f"File exceeds maximum allowed line count of {max_lines}",
                    suggestion="Split into smaller modules or reduce line count",
                    severity="warning",
                )
            )

    return violations


def load_constraint_registry(path: Path) -> list[Constraint]:
    """Load custom constraints from a YAML file.

    Expected format::

        constraints:
          - id: custom-rule
            pattern: "bad_pattern"
            reason: "Because..."
            suggestion: "Do this instead"
            category: "custom"
            severity: "warning"

    Returns an empty list if the file is missing or malformed.
    """
    if not path.exists():
        return []

    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except (yaml.YAMLError, OSError):
        return []

    raw_constraints = data.get("constraints", [])
    if not isinstance(raw_constraints, list):
        return []

    constraints: list[Constraint] = []
    for item in raw_constraints:
        if not isinstance(item, dict):
            continue
        try:
            constraints.append(
                Constraint(
                    id=str(item["id"]),
                    pattern=str(item["pattern"]),
                    reason=str(item.get("reason", "")),
                    suggestion=str(item.get("suggestion", "")),
                    category=str(item.get("category", "custom")),
                    severity=str(item.get("severity", "warning")),
                )
            )
        except (KeyError, TypeError):
            continue

    return constraints


def check_with_registry(
    directory: Path,
    registry_path: Path | None = None,
    *,
    extensions: list[str] | None = None,
    categories: list[str] | None = None,
    severities: list[str] | None = None,
    use_defaults: bool = True,
) -> ScanResult:
    """Combine default + registry constraints and scan *directory*."""
    constraints: list[Constraint] = []

    if use_defaults:
        constraints.extend(DEFAULT_CONSTRAINTS)

    if registry_path is not None:
        constraints.extend(load_constraint_registry(registry_path))

    return check_directory(
        directory,
        constraints=constraints if constraints else None,
        extensions=extensions,
        categories=categories,
        severities=severities,
    )
