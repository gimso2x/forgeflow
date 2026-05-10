"""Tests for project type detection and project-specific draft generation."""
import json
from pathlib import Path

import pytest

from forgeflow_runtime.orchestrator import (
    _detect_project_type,
    _project_type_considerations,
    _init_markdown_drafts,
)
from forgeflow_runtime.policy_loader import RuntimePolicy


@pytest.fixture
def policy() -> RuntimePolicy:
    return RuntimePolicy()


# ── _detect_project_type ──────────────────────────────────────────


class TestDetectProjectType:

    def test_no_project_markers_returns_unknown(self, tmp_path: Path) -> None:
        task_dir = tmp_path / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        result = _detect_project_type(task_dir)
        assert result["project_type"] == "unknown"
        assert result["project_root"] is None
        assert result["framework"] is None

    def test_nextjs_detected_via_package_json(self, tmp_path: Path) -> None:
        project = tmp_path / "myapp"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({
            "dependencies": {"next": "14.0.0", "react": "18.2.0"},
        }))
        task_dir = project / ".forgeflow" / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        result = _detect_project_type(task_dir)
        assert result["project_type"] == "nextjs"
        assert result["framework"] == "Next.js"
        assert result["language"] == "JavaScript"

    def test_nextjs_with_typescript(self, tmp_path: Path) -> None:
        project = tmp_path / "myapp"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({
            "dependencies": {"next": "14.0.0"},
            "devDependencies": {"typescript": "5.3.0"},
        }))
        task_dir = project / ".forgeflow" / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        result = _detect_project_type(task_dir)
        assert result["project_type"] == "nextjs"
        assert result["language"] == "TypeScript"

    def test_react_detected_via_package_json(self, tmp_path: Path) -> None:
        project = tmp_path / "myapp"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({
            "dependencies": {"react": "18.2.0"},
        }))
        task_dir = project / ".forgeflow" / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        result = _detect_project_type(task_dir)
        assert result["project_type"] == "react"
        assert result["framework"] == "React"

    def test_fastapi_detected_via_pyproject(self, tmp_path: Path) -> None:
        project = tmp_path / "myapi"
        project.mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "myapi"\n[tool.poetry.dependencies]\nfastapi = "*"\n'
        )
        task_dir = project / ".forgeflow" / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        result = _detect_project_type(task_dir)
        assert result["project_type"] == "fastapi"
        assert result["framework"] == "FastAPI"
        assert result["language"] == "Python"

    def test_django_detected_via_manage_py(self, tmp_path: Path) -> None:
        project = tmp_path / "mysite"
        project.mkdir()
        (project / "manage.py").write_text("# django manage.py\n")
        task_dir = project / ".forgeflow" / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        result = _detect_project_type(task_dir)
        assert result["project_type"] == "django"
        assert result["framework"] == "Django"

    def test_go_service_detected_via_go_mod(self, tmp_path: Path) -> None:
        project = tmp_path / "myservice"
        project.mkdir()
        (project / "go.mod").write_text("module github.com/example/myservice\n")
        task_dir = project / ".forgeflow" / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        result = _detect_project_type(task_dir)
        assert result["project_type"] == "go-service"
        assert result["language"] == "Go"

    def test_rust_detected_via_cargo_toml(self, tmp_path: Path) -> None:
        project = tmp_path / "myrust"
        project.mkdir()
        (project / "Cargo.toml").write_text('[package]\nname = "myrust"\n')
        task_dir = project / ".forgeflow" / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        result = _detect_project_type(task_dir)
        assert result["project_type"] == "rust-project"
        assert result["language"] == "Rust"

    def test_generic_python_project(self, tmp_path: Path) -> None:
        project = tmp_path / "mylib"
        project.mkdir()
        (project / "pyproject.toml").write_text('[project]\nname = "mylib"\n')
        task_dir = project / ".forgeflow" / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        result = _detect_project_type(task_dir)
        assert result["project_type"] == "python-cli"
        assert result["language"] == "Python"

    def test_tanstack_start_detected_via_package_json(self, tmp_path: Path) -> None:
        project = tmp_path / "myapp"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({
            "dependencies": {"@tanstack/start": "1.0.0", "react": "18.2.0"},
            "devDependencies": {"typescript": "5.3.0"},
        }))
        (project / "tsconfig.json").write_text("{}")
        task_dir = project / ".forgeflow" / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        result = _detect_project_type(task_dir)
        assert result["project_type"] == "tanstack-start"
        assert result["framework"] == "TanStack Start"
        assert result["language"] == "TypeScript"

    def test_tanstack_start_detected_via_vinxi(self, tmp_path: Path) -> None:
        project = tmp_path / "myapp"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({
            "dependencies": {"vinxi": "0.4.0", "react": "18.2.0"},
        }))
        task_dir = project / ".forgeflow" / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        result = _detect_project_type(task_dir)
        assert result["project_type"] == "tanstack-start"
        assert result["framework"] == "TanStack Start"

    def test_tanstack_start_not_confused_with_plain_react(self, tmp_path: Path) -> None:
        """When @tanstack/start is present, it should win over plain react."""
        project = tmp_path / "myapp"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({
            "dependencies": {"@tanstack/start": "1.0.0", "react": "18.2.0"},
        }))
        task_dir = project / ".forgeflow" / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        result = _detect_project_type(task_dir)
        assert result["project_type"] == "tanstack-start"
        assert result["project_type"] != "react"

    def test_max_depth_stops_at_8_levels(self, tmp_path: Path) -> None:
        """Project root 9+ levels up should not be detected."""
        deep = tmp_path
        for i in range(12):
            deep = deep / f"level{i}"
        task_dir = deep / "tasks" / "t-01"
        task_dir.mkdir(parents=True)
        # Put a marker at the very top
        (tmp_path / "go.mod").write_text("module test\n")
        result = _detect_project_type(task_dir)
        # Should not find go.mod 12 levels up (max 8)
        assert result["project_type"] == "unknown"


# ── _project_type_considerations ──────────────────────────────────


class TestProjectTypeConsiderations:

    def test_nextjs_notes(self) -> None:
        info = {"project_type": "nextjs", "framework": None, "language": "TypeScript"}
        notes = _project_type_considerations(info)
        assert "App Router" in notes
        assert "Server Components" in notes

    def test_fastapi_notes(self) -> None:
        info = {"project_type": "fastapi", "framework": "FastAPI", "language": "Python"}
        notes = _project_type_considerations(info)
        assert "dependency injection" in notes
        assert "Pydantic" in notes

    def test_unknown_uses_language(self) -> None:
        info = {"project_type": "unknown", "framework": None, "language": "Go"}
        notes = _project_type_considerations(info)
        assert "Go" in notes

    def test_unknown_no_language(self) -> None:
        info = {"project_type": "unknown", "framework": None, "language": None}
        notes = _project_type_considerations(info)
        assert "general best practices" in notes

    def test_tanstack_start_notes(self) -> None:
        info = {"project_type": "tanstack-start", "framework": "TanStack Start", "language": "TypeScript"}
        notes = _project_type_considerations(info)
        assert "TanStack Start" in notes
        assert "file-based routing" in notes
        assert "Server Functions" in notes


# ── Integration: init with project context ────────────────────────


class TestInitWithProjectContext:

    def test_init_generates_project_context_in_prd(self, tmp_path: Path) -> None:
        """Init inside a Next.js project should include project context in PRD."""
        project = tmp_path / "nextapp"
        project.mkdir()
        (project / "package.json").write_text(json.dumps({
            "dependencies": {"next": "14.0.0"},
            "devDependencies": {"typescript": "5.3.0"},
        }))
        (project / "tsconfig.json").write_text("{}")
        task_dir = project / ".forgeflow" / "tasks" / "t-01"

        _init_markdown_drafts(
            task_dir=task_dir,
            project_root=project,
            task_id="t-01",
            objective="add authentication to the dashboard",
            risk_level="medium",
            route_name="medium",
        )

        prd = (task_dir / "docs" / "PRD.md").read_text()
        assert "## Project Context" in prd
        assert "nextjs" in prd
        assert "Next.js" in prd
        assert "TypeScript" in prd
        assert "App Router" in prd

        arch = (task_dir / "docs" / "ARCHITECTURE.md").read_text()
        assert "## Project Context" in arch
        assert "nextjs" in arch

        qa = (task_dir / "docs" / "QA.md").read_text()
        assert "## Project-Specific QA Notes" in qa
        assert "nextjs" in qa

    def test_init_outside_project_generates_unknown_context(self, tmp_path: Path) -> None:
        """Init in a bare directory should still work with unknown project type."""
        task_dir = tmp_path / "tasks" / "t-01"

        _init_markdown_drafts(
            task_dir=task_dir,
            project_root=tmp_path,
            task_id="t-01",
            objective="fix the bug",
            risk_level="low",
            route_name="small",
        )

        prd = (task_dir / "docs" / "PRD.md").read_text()
        assert "## Project Context" in prd
        assert "unknown" in prd

    def test_init_fastapi_project_generates_framework_notes(self, tmp_path: Path) -> None:
        """Init inside a FastAPI project should include FastAPI-specific guidelines."""
        project = tmp_path / "myapi"
        project.mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "myapi"\n[tool.poetry.dependencies]\nfastapi = "*"\n'
        )
        task_dir = project / ".forgeflow" / "tasks" / "t-01"

        _init_markdown_drafts(
            task_dir=task_dir,
            project_root=project,
            task_id="t-01",
            objective="add rate limiting to the API endpoints",
            risk_level="medium",
            route_name="medium",
        )

        prd = (task_dir / "docs" / "PRD.md").read_text()
        assert "fastapi" in prd
        assert "FastAPI" in prd
        assert "Python" in prd
        assert "dependency injection" in prd
