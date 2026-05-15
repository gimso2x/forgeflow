"""Tests for domain analysis helpers in orchestrator."""
import json
import textwrap
from pathlib import Path

import pytest

from forgeflow_runtime.orchestrator import (
    _analyze_objective_domain,
    _architecture_considerations,
    _domain_considerations,
    _qa_checklist,
    clarify_task,
    init_task,
)
from forgeflow_runtime.policy_loader import RuntimePolicy, load_runtime_policy

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

@pytest.fixture()
def policy():
    return load_runtime_policy(_REPO_ROOT)


class TestAnalyzeObjectiveDomain:
    def test_generic_objective_returns_general(self) -> None:
        result = _analyze_objective_domain("do it")
        assert result["domains"] == ["general"]
        assert result["change_type"] == "feature"

    def test_api_endpoint_detected(self) -> None:
        result = _analyze_objective_domain("add REST api endpoint for users")
        assert "api" in result["domains"]
        assert result["change_type"] == "feature"

    def test_bugfix_detected(self) -> None:
        result = _analyze_objective_domain("fix crash in login form")
        assert "bugfix" in result["change_type"]
        assert "auth" in result["domains"]
        assert "frontend" in result["domains"]

    def test_refactor_detected(self) -> None:
        result = _analyze_objective_domain("refactor database query layer")
        assert result["change_type"] == "refactor"
        assert "data" in result["domains"]

    def test_migration_detected(self) -> None:
        result = _analyze_objective_domain("migrate from mysql to postgres")
        assert result["change_type"] == "migration"
        assert "data" in result["domains"]

    def test_security_detected(self) -> None:
        result = _analyze_objective_domain("patch XSS vulnerability in form handler")
        assert result["change_type"] == "security"
        assert "security" in result["domains"]

    def test_multi_domain_detected(self) -> None:
        result = _analyze_objective_domain("add auth middleware to API service")
        assert "auth" in result["domains"]
        assert "api" in result["domains"]
        assert "backend" in result["domains"]

    def test_tech_stack_python(self) -> None:
        result = _analyze_objective_domain("add pytest tests for fastapi endpoint")
        assert "python" in result["tech_stack"]
        assert "api" in result["domains"]

    def test_tech_stack_javascript(self) -> None:
        result = _analyze_objective_domain("build react component for dashboard")
        assert "javascript" in result["tech_stack"]
        assert "frontend" in result["domains"]

    def test_testing_change_type(self) -> None:
        result = _analyze_objective_domain("add test coverage for auth module")
        assert result["change_type"] == "testing"
        assert "testing" in result["domains"]

    def test_unspecified_tech_when_no_signal(self) -> None:
        result = _analyze_objective_domain("improve the thing")
        assert result["tech_stack"] == ["unspecified"]


class TestDomainConsiderations:
    def test_api_domain_gets_considerations(self) -> None:
        text = _domain_considerations(["api"], "feature")
        assert "backward compatibility" in text
        assert "endpoint contracts" in text

    def test_bugfix_change_type_gets_considerations(self) -> None:
        text = _domain_considerations(["general"], "bugfix")
        assert "Root cause" in text
        assert "regression test" in text

    def test_unknown_domain_returns_fallback(self) -> None:
        text = _domain_considerations(["general"], "feature")
        assert "scope" in text.lower()


class TestArchitectureConsiderations:
    def test_data_domain_gets_migration_advice(self) -> None:
        text = _architecture_considerations(["data"], "producer-reviewer + pipeline")
        assert "migration" in text.lower() or "schema" in text.lower()

    def test_empty_domains_returns_fallback(self) -> None:
        text = _architecture_considerations(["nonexistent"], "pipeline")
        assert "team pattern" in text.lower()


class TestQAChecklist:
    def test_api_checklist_items(self) -> None:
        text = _qa_checklist(["api"], "feature")
        assert "API contract verified" in text

    def test_bugfix_checklist_items(self) -> None:
        text = _qa_checklist(["backend"], "bugfix")
        assert "Bug reproduced before fix" in text

    def test_empty_domains_returns_fallback(self) -> None:
        text = _qa_checklist(["nonexistent"], "feature")
        assert "acceptance criteria" in text.lower()


class TestClarifyWithDomainAnalysis:
    def test_clarify_generates_domain_rich_prd(self, tmp_path, policy) -> None:
        """Clarify with a domain-specific objective produces domain-aware drafts."""
        task_dir = tmp_path / "auth-task"
        init_task(
            task_dir,
            policy,
            task_id="t-auth",
            objective="add OAuth login endpoint with session management",
            risk_level="medium",
        )
        clarify_task(task_dir, policy)

        prd = (task_dir / "docs/PRD.md").read_text()
        assert "## Domain Analysis" in prd
        assert "auth" in prd
        assert "api" in prd
        assert "## Domain-Specific Considerations" in prd
        assert "security review" in prd.lower()

        arch = (task_dir / "docs/ARCHITECTURE.md").read_text()
        assert "## Domain Context" in arch
        assert "## Architecture Considerations" in arch

        qa = (task_dir / "docs/QA.md").read_text()
        assert "## Domain-Specific QA Checklist" in qa
        assert "Authenticated and unauthenticated" in qa

    def test_clarify_generates_refactor_aware_drafts(self, tmp_path, policy) -> None:
        """Clarify with refactor objective produces refactor-specific considerations."""
        task_dir = tmp_path / "refactor-task"
        init_task(
            task_dir,
            policy,
            task_id="t-ref",
            objective="refactor database query layer for better performance",
            risk_level="high",
        )
        clarify_task(task_dir, policy)

        prd = (task_dir / "docs/PRD.md").read_text()
        assert "refactor" in prd
        assert "Behavior must be preserved" in prd

        qa = (task_dir / "docs/QA.md").read_text()
        assert "All existing tests pass without modification" in qa


class TestAutoInference:
    """Tests for task-id slug and risk auto-inference."""

    def test_slugify_basic(self) -> None:
        from forgeflow_runtime.orchestrator import _slugify_objective
        slug = _slugify_objective("Add OAuth login endpoint with session management")
        assert slug == "add-oauth-login-endpoint-session-management"
        assert len(slug) <= 64

    def test_slugify_short(self) -> None:
        from forgeflow_runtime.orchestrator import _slugify_objective
        slug = _slugify_objective("fix typo")
        assert slug == "fix-typo"

    def test_slugify_korean_fallback(self) -> None:
        from forgeflow_runtime.orchestrator import _slugify_objective
        slug = _slugify_objective("로그인 페이지 만들기")
        assert slug.startswith("task-")  # no latin words → fallback with timestamp
        assert len(slug) > 10

    def test_estimate_risk_high(self) -> None:
        from forgeflow_runtime.orchestrator import _estimate_risk
        assert _estimate_risk("migrate database schema to v2") == "high"

    def test_estimate_risk_low(self) -> None:
        from forgeflow_runtime.orchestrator import _estimate_risk
        assert _estimate_risk("fix typo in readme") == "low"

    def test_estimate_risk_medium_default(self) -> None:
        from forgeflow_runtime.orchestrator import _estimate_risk
        assert _estimate_risk("add user profile page") == "medium"

    def test_init_objective_only(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        """init_task with only objective auto-infers task-id and risk."""
        task_dir = tmp_path / "auto-task"
        result = init_task(
            task_dir,
            policy,
            objective="fix typo in README",
        )
        assert result["task_id"] == "fix-typo-readme"
        assert result["risk_level"] == "low"
        assert result["route"] == "small"
        assert (task_dir / "brief.json").exists()

    def test_init_override_keeps_explicit(self, tmp_path: Path, policy: RuntimePolicy) -> None:
        """Explicit task_id/risk_level override auto-inference."""
        task_dir = tmp_path / "override-task"
        result = init_task(
            task_dir,
            policy,
            objective="fix typo in README",
            task_id="my-custom-id",
            risk_level="high",
        )
        assert result["task_id"] == "my-custom-id"
        assert result["risk_level"] == "high"
        assert result["route"] == "high"
