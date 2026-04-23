from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from forgeflow_runtime.generator import (
    GenerationError,
    PromptContext,
    _artifact_summary,
    _discover_artifacts,
    _load_role_prompt,
    _token_budget_for_role,
    generate_prompt,
)


class TestLoadRolePrompt:
    def test_loads_coordinator(self):
        text = _load_role_prompt("coordinator")
        assert "Coordinator" in text
        assert "stage" in text

    def test_loads_planner(self):
        text = _load_role_prompt("planner")
        assert "Planner" in text

    def test_loads_worker(self):
        text = _load_role_prompt("worker")
        assert "Worker" in text

    def test_loads_spec_reviewer(self):
        text = _load_role_prompt("spec-reviewer")
        assert "Spec Reviewer" in text

    def test_loads_quality_reviewer(self):
        text = _load_role_prompt("quality-reviewer")
        assert "Quality Reviewer" in text

    def test_unknown_role_raises(self):
        with pytest.raises(GenerationError, match="unknown role"):
            _load_role_prompt("nonexistent")


class TestDiscoverArtifacts:
    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as td:
            assert _discover_artifacts(Path(td)) == []

    def test_discovers_json_files(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "brief.json").write_text("{}")
            (p / "run-state.json").write_text("{}")
            (p / "notes.md").write_text("hello")  # ignored
            assert _discover_artifacts(p) == ["brief", "run-state"]


class TestArtifactSummary:
    def test_missing_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            assert _artifact_summary(Path(td), "brief") is None

    def test_valid_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            payload = {"task_id": "t1", "objective": "test"}
            (p / "brief.json").write_text(json.dumps(payload))
            summary = _artifact_summary(p, "brief")
            assert summary is not None
            assert '"task_id": "t1"' in summary

    def test_truncates_long_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            payload = {"k" + str(i): "v" * 200 for i in range(50)}
            (p / "big.json").write_text(json.dumps(payload))
            summary = _artifact_summary(p, "big")
            assert summary is not None
            assert "... (truncated)" in summary


class TestTokenBudget:
    def test_default_budget(self):
        budget = _token_budget_for_role("worker")
        assert budget["input"] == 8000
        assert budget["output"] == 4000

    def test_planner_override(self):
        budget = _token_budget_for_role("planner")
        assert budget["input"] == 12000
        assert budget["output"] == 6000


class TestGeneratePrompt:
    def test_basic_generation(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "brief.json").write_text(json.dumps({"task_id": "t1", "objective": "do it"}))
            ctx = PromptContext(
                role="worker",
                stage="execute",
                route="medium",
                task_dir=p,
                task_id="t1",
            )
            result = generate_prompt(ctx)
            assert result.role == "worker"
            assert result.stage == "execute"
            assert result.route == "medium"
            assert "Worker" in result.system_prompt
            assert "task_id: t1" in result.task_prompt
            assert "execute" in result.task_prompt
            assert "brief" in result.referenced_artifacts
            assert result.token_budget["input"] == 8000

    def test_extra_context_included(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            ctx = PromptContext(
                role="planner",
                stage="plan",
                route="large_high_risk",
                task_dir=p,
                task_id="t2",
                extra_context={"priority": "p0", "deadline": "tomorrow"},
            )
            result = generate_prompt(ctx)
            assert "priority: p0" in result.task_prompt
            assert "deadline: tomorrow" in result.task_prompt

    def test_unknown_role_raises(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            ctx = PromptContext(
                role="wizard",
                stage="magic",
                route="small",
                task_dir=p,
                task_id="t3",
            )
            with pytest.raises(GenerationError, match="unknown role"):
                generate_prompt(ctx)
