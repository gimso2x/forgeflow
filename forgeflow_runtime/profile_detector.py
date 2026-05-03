"""Auto-detect project profile from filesystem layout.

Scans a project directory to determine language, framework, package manager,
test/CI presence, project category, and recommended QA strategy.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class ProfileCategory(Enum):
    APP = "APP"
    SERVICE = "SERVICE"
    LIBRARY = "LIBRARY"
    MONOREPO = "MONOREPO"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TechStack:
    language: str
    framework: str | None = None
    package_manager: str | None = None
    has_tests: bool = False
    has_ci: bool = False


@dataclass(frozen=True)
class ProjectProfile:
    category: ProfileCategory
    tech_stack: TechStack
    qa_strategy: list[str]
    confidence: float


# ---------------------------------------------------------------------------
# QA strategy defaults per category
# ---------------------------------------------------------------------------

_QA_STRATEGY: dict[ProfileCategory, list[str]] = {
    ProfileCategory.APP: [
        "ui-button-event", "modal-popup", "confirm-dialog",
        "alert-dialog", "browser-console-clean",
    ],
    ProfileCategory.SERVICE: ["api-flow", "browser-console-clean"],
    ProfileCategory.LIBRARY: ["api-flow"],
    ProfileCategory.MONOREPO: ["api-flow", "browser-console-clean"],
    ProfileCategory.UNKNOWN: [],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _first_match(globs: list[str], root: Path) -> Path | None:
    """Return the first existing path matching any of *globs* under *root*."""
    for pattern in globs:
        found = list(root.glob(pattern))
        if found:
            return found[0]
    return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


def _detect_language(root: Path) -> str:
    lang_map: list[tuple[list[str], str]] = [
        (["*.py"], "Python"),
        (["*.ts", "*.tsx"], "TypeScript"),
        (["*.go"], "Go"),
        (["*.rs"], "Rust"),
        (["*.java"], "Java"),
    ]
    for globs, lang in lang_map:
        if _first_match(globs, root):
            return lang
    return "Unknown"


def _detect_framework(root: Path) -> str | None:
    if (root / "manage.py").exists():
        return "Django"
    if (root / "app.py").exists():
        reqs = _read_text(root / "requirements.txt") + _read_text(root / "pyproject.toml")
        if "flask" in reqs.lower():
            return "Flask"
    if _first_match(["next.config.*"], root):
        return "Next.js"
    pkg = _read_text(root / "package.json")
    if '"express"' in pkg or "'express'" in pkg:
        return "Express"
    return None


def _detect_package_manager(root: Path) -> str | None:
    if (root / "package.json").exists():
        return "npm"
    if (root / "requirements.txt").exists() or (root / "poetry.lock").exists():
        return "pip"
    if (root / "go.mod").exists():
        return "go"
    if (root / "Cargo.toml").exists():
        return "cargo"
    if (root / "pom.xml").exists():
        return "maven"
    return None


def _detect_tests(root: Path) -> bool:
    test_indicators = [
        "pytest.ini",
        "test/**",
        "__tests__/**",
        "*_test.go",
        "*.test.ts",
    ]
    return any(_first_match([p], root) for p in test_indicators)


def _detect_ci(root: Path) -> bool:
    ci_indicators = [
        ".github/workflows/*",
        ".gitlab-ci.yml",
        "Jenkinsfile",
    ]
    return any(_first_match([p], root) for p in ci_indicators)


def _detect_category(root: Path) -> ProfileCategory:
    has_pkg = (root / "package.json").exists()
    has_public = (root / "public").is_dir()
    has_dockerfile = (root / "Dockerfile").exists()
    has_api = (root / "api").is_dir()
    has_setup = (root / "setup.py").exists() or (root / "pyproject.toml").exists()
    has_packages = (root / "packages").is_dir()
    has_apps = (root / "apps").is_dir()

    if has_pkg and has_public:
        return ProfileCategory.APP
    if has_dockerfile or has_api:
        return ProfileCategory.SERVICE
    if has_setup and not has_public:
        return ProfileCategory.LIBRARY
    if has_packages or has_apps:
        return ProfileCategory.MONOREPO
    return ProfileCategory.UNKNOWN


def _calc_confidence(tech: TechStack, category: ProfileCategory) -> float:
    signals = 0
    if tech.language != "Unknown":
        signals += 1
    if tech.framework:
        signals += 1
    if tech.package_manager:
        signals += 1
    if category != ProfileCategory.UNKNOWN:
        signals += 1
    if signals >= 3:
        return 1.0
    if signals >= 1:
        return 0.7
    return 0.5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_project(directory: str) -> ProjectProfile:
    """Scan *directory* and return an inferred :class:`ProjectProfile`."""
    root = Path(directory).resolve()
    language = _detect_language(root)
    framework = _detect_framework(root)
    package_manager = _detect_package_manager(root)
    has_tests = _detect_tests(root)
    has_ci = _detect_ci(root)
    category = _detect_category(root)

    tech = TechStack(
        language=language,
        framework=framework,
        package_manager=package_manager,
        has_tests=has_tests,
        has_ci=has_ci,
    )
    confidence = _calc_confidence(tech, category)
    qa_strategy = _QA_STRATEGY.get(category, [])

    return ProjectProfile(
        category=category,
        tech_stack=tech,
        qa_strategy=qa_strategy,
        confidence=confidence,
    )


def merge_profiles(
    base: ProjectProfile,
    override: ProjectProfile,
) -> ProjectProfile:
    """Merge *override* into *base*.

    * Category is taken from *override* when its confidence is higher.
    * ``qa_strategy`` is the union of both.
    * Each non-``None`` field in *override*'s ``tech_stack`` wins.
    """
    category = (
        override.category if override.confidence > base.confidence else base.category
    )
    qa = sorted(set(base.qa_strategy) | set(override.qa_strategy))

    def _pick(base_val: Any, over_val: Any) -> Any:
        return over_val if over_val is not None else base_val

    merged_tech = TechStack(
        language=_pick(base.tech_stack.language, override.tech_stack.language),
        framework=_pick(base.tech_stack.framework, override.tech_stack.framework),
        package_manager=_pick(
            base.tech_stack.package_manager, override.tech_stack.package_manager
        ),
        has_tests=base.tech_stack.has_tests or override.tech_stack.has_tests,
        has_ci=base.tech_stack.has_ci or override.tech_stack.has_ci,
    )

    return ProjectProfile(
        category=category,
        tech_stack=merged_tech,
        qa_strategy=qa,
        confidence=max(base.confidence, override.confidence),
    )


def format_profile_report(profile: ProjectProfile) -> str:
    """Return a human-readable project profile report."""
    lines = [
        f"Category:  {profile.category.value}",
        f"Language:  {profile.tech_stack.language}",
        f"Framework: {profile.tech_stack.framework or 'N/A'}",
        f"Pkg Mgr:   {profile.tech_stack.package_manager or 'N/A'}",
        f"Tests:     {'yes' if profile.tech_stack.has_tests else 'no'}",
        f"CI:        {'yes' if profile.tech_stack.has_ci else 'no'}",
        f"QA:        {', '.join(profile.qa_strategy) or 'none'}",
        f"Confidence: {profile.confidence:.0%}",
    ]
    return "\n".join(lines)
