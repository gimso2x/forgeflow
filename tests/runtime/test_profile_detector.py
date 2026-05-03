from __future__ import annotations

import dataclasses

import pytest

from forgeflow_runtime.profile_detector import (
    ProfileCategory,
    ProjectProfile,
    TechStack,
    format_profile_report,
    merge_profiles,
    scan_project,
)


# ── scan_project helpers ──────────────────────────────────────────────────


class TestScanProjectPython:
    def test_python_language_and_pip_manager(self, tmp_path) -> None:
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "requirements.txt").write_text("")
        profile = scan_project(str(tmp_path))
        assert profile.tech_stack.language == "Python"
        assert profile.tech_stack.package_manager == "pip"


class TestScanProjectTypeScript:
    def test_typescript_language(self, tmp_path) -> None:
        (tmp_path / "index.ts").write_text("console.log('hi')")
        (tmp_path / "package.json").write_text("{}")
        profile = scan_project(str(tmp_path))
        assert profile.tech_stack.language == "TypeScript"
        assert profile.tech_stack.package_manager == "npm"


class TestScanProjectTests:
    def test_tests_dir_sets_has_tests(self, tmp_path) -> None:
        (tmp_path / "main.py").write_text("")
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "test_main.py").write_text("")
        profile = scan_project(str(tmp_path))
        assert profile.tech_stack.has_tests is True


class TestScanProjectCI:
    def test_github_workflows_sets_has_ci(self, tmp_path) -> None:
        (tmp_path / "main.py").write_text("")
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("")
        profile = scan_project(str(tmp_path))
        assert profile.tech_stack.has_ci is True


# ── Category detection ────────────────────────────────────────────────────


class TestCategoryApp:
    def test_package_json_plus_public(self, tmp_path) -> None:
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "public").mkdir()
        profile = scan_project(str(tmp_path))
        assert profile.category == ProfileCategory.APP


class TestCategoryService:
    def test_dockerfile(self, tmp_path) -> None:
        (tmp_path / "main.py").write_text("")
        (tmp_path / "Dockerfile").write_text("FROM python:3.12")
        profile = scan_project(str(tmp_path))
        assert profile.category == ProfileCategory.SERVICE


class TestCategoryLibrary:
    def test_setup_py_no_public(self, tmp_path) -> None:
        (tmp_path / "setup.py").write_text("")
        (tmp_path / "main.py").write_text("")
        profile = scan_project(str(tmp_path))
        assert profile.category == ProfileCategory.LIBRARY


class TestCategoryMonorepo:
    def test_packages_dir(self, tmp_path) -> None:
        (tmp_path / "main.py").write_text("")
        (tmp_path / "packages").mkdir()
        profile = scan_project(str(tmp_path))
        assert profile.category == ProfileCategory.MONOREPO


# ── QA strategy ───────────────────────────────────────────────────────────


class TestQAStrategy:
    def test_app_qa(self, tmp_path) -> None:
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "public").mkdir()
        profile = scan_project(str(tmp_path))
        assert "ui-button-event" in profile.qa_strategy
        assert "browser-console-clean" in profile.qa_strategy

    def test_service_qa(self, tmp_path) -> None:
        (tmp_path / "main.py").write_text("")
        (tmp_path / "Dockerfile").write_text("")
        profile = scan_project(str(tmp_path))
        assert profile.qa_strategy == ["api-flow", "browser-console-clean"]

    def test_library_qa(self, tmp_path) -> None:
        (tmp_path / "setup.py").write_text("")
        (tmp_path / "main.py").write_text("")
        profile = scan_project(str(tmp_path))
        assert profile.qa_strategy == ["api-flow"]


# ── merge_profiles ────────────────────────────────────────────────────────


class TestMergeProfiles:
    def test_higher_confidence_overrides_category(self) -> None:
        base = ProjectProfile(
            category=ProfileCategory.LIBRARY,
            tech_stack=TechStack(language="Python"),
            qa_strategy=["api-flow"],
            confidence=0.7,
        )
        override = ProjectProfile(
            category=ProfileCategory.SERVICE,
            tech_stack=TechStack(language="Python"),
            qa_strategy=["browser-console-clean"],
            confidence=1.0,
        )
        merged = merge_profiles(base, override)
        assert merged.category == ProfileCategory.SERVICE

    def test_qa_strategy_is_union(self) -> None:
        base = ProjectProfile(
            category=ProfileCategory.LIBRARY,
            tech_stack=TechStack(language="Python"),
            qa_strategy=["api-flow"],
            confidence=0.7,
        )
        override = ProjectProfile(
            category=ProfileCategory.LIBRARY,
            tech_stack=TechStack(language="Python"),
            qa_strategy=["browser-console-clean"],
            confidence=0.5,
        )
        merged = merge_profiles(base, override)
        assert "api-flow" in merged.qa_strategy
        assert "browser-console-clean" in merged.qa_strategy

    def test_override_tech_stack_non_none(self) -> None:
        base = ProjectProfile(
            category=ProfileCategory.UNKNOWN,
            tech_stack=TechStack(language="Unknown", framework=None, package_manager=None),
            qa_strategy=[],
            confidence=0.5,
        )
        override = ProjectProfile(
            category=ProfileCategory.APP,
            tech_stack=TechStack(language="TypeScript", framework="Next.js", package_manager="npm"),
            qa_strategy=[],
            confidence=1.0,
        )
        merged = merge_profiles(base, override)
        assert merged.tech_stack.language == "TypeScript"
        assert merged.tech_stack.framework == "Next.js"
        assert merged.tech_stack.package_manager == "npm"


# ── format_profile_report ─────────────────────────────────────────────────


class TestFormatProfileReport:
    def test_contains_category_and_language(self) -> None:
        profile = ProjectProfile(
            category=ProfileCategory.LIBRARY,
            tech_stack=TechStack(language="Python"),
            qa_strategy=["api-flow"],
            confidence=1.0,
        )
        report = format_profile_report(profile)
        assert "LIBRARY" in report
        assert "Python" in report


# ── Frozen immutability ───────────────────────────────────────────────────


class TestProjectProfileFrozen:
    def test_frozen_raises_on_set(self) -> None:
        profile = ProjectProfile(
            category=ProfileCategory.UNKNOWN,
            tech_stack=TechStack(language="Unknown"),
            qa_strategy=[],
            confidence=0.5,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            profile.category = ProfileCategory.APP  # type: ignore[misc]
