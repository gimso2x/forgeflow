"""Tests for forgeflow_runtime.engine.execute_stage — prompt generation → executor dispatch."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from forgeflow_runtime.engine import execute_parallel_workers, execute_stage
from forgeflow_runtime.executor import RunTaskResult
from forgeflow_runtime.generator import GeneratedPrompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call(task_dir, *, role="worker", stage="clarify", route="small",
          adapter_target="claude", extra_context=None,
          artifacts_to_stream=None, use_real=False):
    """Thin wrapper so every test uses keyword-only style."""
    return execute_stage(
        task_dir=task_dir,
        task_id="task-001",
        stage=stage,
        route=route,
        role=role,
        adapter_target=adapter_target,
        extra_context=extra_context,
        artifacts_to_stream=artifacts_to_stream,
        use_real=use_real,
    )


# ---------------------------------------------------------------------------
# 1. Returns RunTaskResult
# ---------------------------------------------------------------------------

class TestExecuteStageReturnsRunTaskResult:
    def test_success_with_stub_adapter(self, tmp_path, make_task_dir):
        task_dir = make_task_dir(tmp_path)
        result = _call(task_dir)
        assert isinstance(result, RunTaskResult)
        assert result.status == "success"

    def test_has_raw_output(self, tmp_path, make_task_dir):
        task_dir = make_task_dir(tmp_path)
        result = _call(task_dir)
        assert result.raw_output is not None


# ---------------------------------------------------------------------------
# 2. Includes role and stage in output
# ---------------------------------------------------------------------------

class TestExecuteStageIncludesRoleAndStage:
    def test_role_present_in_raw_output(self, tmp_path, make_task_dir):
        task_dir = make_task_dir(tmp_path)
        result = _call(task_dir, role="planner")
        assert result.raw_output is not None
        assert "role=planner" in result.raw_output

    def test_stage_present_in_raw_output(self, tmp_path, make_task_dir):
        task_dir = make_task_dir(tmp_path)
        result = _call(task_dir, stage="execute")
        assert result.raw_output is not None
        assert "stage=execute" in result.raw_output


# ---------------------------------------------------------------------------
# 3. Default adapter is claude
# ---------------------------------------------------------------------------

class TestExecuteStageDefaultAdapter:
    def test_default_adapter_is_claude(self, tmp_path, make_task_dir):
        task_dir = make_task_dir(tmp_path)
        # Omit adapter_target → should default to "claude" stub
        result = execute_stage(
            task_dir=task_dir,
            task_id="task-001",
            stage="clarify",
            route="small",
            role="worker",
        )
        assert result.status == "success"
        assert "stub-claude-output" in (result.raw_output or "")


# ---------------------------------------------------------------------------
# 4. Extra context passed through to generated prompt
# ---------------------------------------------------------------------------

class TestExecuteStageExtraContext:
    def test_extra_context_appears_in_prompt(self, tmp_path, make_task_dir):
        task_dir = make_task_dir(tmp_path)
        extra = {"focus": "testing", "priority": "high"}

        from forgeflow_runtime.executor import dispatch as _real_dispatch
        captured_req = None

        def _spy(request, *, use_real=False):
            nonlocal captured_req
            captured_req = request
            return _real_dispatch(request, use_real=use_real)

        with patch("forgeflow_runtime.engine.dispatch", side_effect=_spy):
            _call(task_dir, extra_context=extra)

        assert captured_req is not None
        prompt = captured_req.prompt
        assert "focus" in prompt and "testing" in prompt
        assert "priority" in prompt and "high" in prompt

    def test_none_extra_context_still_works(self, tmp_path, make_task_dir):
        task_dir = make_task_dir(tmp_path)
        result = _call(task_dir, extra_context=None)
        assert result.status == "success"


# ---------------------------------------------------------------------------
# 5. artifacts_to_stream reflected in result
# ---------------------------------------------------------------------------

class TestExecuteStageArtifactsToStream:
    def test_artifacts_produced_matches_input(self, tmp_path, make_task_dir):
        task_dir = make_task_dir(tmp_path)
        artifacts = ["brief.json", "run-state.json"]
        result = _call(task_dir, artifacts_to_stream=artifacts)
        assert result.status == "success"
        assert set(result.artifacts_produced) == set(artifacts)

    def test_none_artifacts_yields_empty_list(self, tmp_path, make_task_dir):
        task_dir = make_task_dir(tmp_path)
        result = _call(task_dir, artifacts_to_stream=None)
        assert result.status == "success"
        assert result.artifacts_produced == []


# ---------------------------------------------------------------------------
# 6. Unknown adapter fails
# ---------------------------------------------------------------------------

class TestExecuteStageUnknownAdapter:
    def test_unknown_adapter_returns_failure(self, tmp_path, make_task_dir):
        task_dir = make_task_dir(tmp_path)
        result = _call(task_dir, adapter_target="unknown")
        assert result.status == "failure"
        assert "unknown adapter target" in (result.error or "")


# ---------------------------------------------------------------------------
# 7. Budget enforcement
# ---------------------------------------------------------------------------

class TestExecuteStageBudgetEnforcement:
    def test_tiny_budget_blocks_prompt(self, tmp_path, make_task_dir):
        """When generate_prompt returns a tiny token budget, the stub should block."""
        task_dir = make_task_dir(tmp_path)

        fake_prompt = GeneratedPrompt(
            role="worker",
            stage="clarify",
            route="small",
            system_prompt="You are a worker.",
            task_prompt="# Task\nDo work.",
            referenced_artifacts=[],
            token_budget={"input": 1, "output": 1},
        )

        with patch("forgeflow_runtime.engine.generate_prompt", return_value=fake_prompt):
            result = _call(task_dir)

        assert result.status == "blocked"
        assert "exceed" in (result.error or "").lower()

    def test_normal_budget_succeeds(self, tmp_path, make_task_dir):
        """Default budgets from canonical roles should not be exceeded by small prompts."""
        task_dir = make_task_dir(tmp_path)
        result = _call(task_dir, role="coordinator")
        assert result.status == "success"


# ---------------------------------------------------------------------------
# 8. use_real flag propagates
# ---------------------------------------------------------------------------

class TestExecuteStageUseRealFlag:
    def test_use_real_dispatches_to_real_registry(self, tmp_path, make_task_dir):
        """use_real=True routes through REAL_REGISTRY, not STUB_REGISTRY.

        The real ClaudeCodeAdapter will either succeed (binary present) or
        fail with a descriptive error (binary absent).  Either way the
        raw_output must NOT be the stub format, proving the real path was
        taken.
        """
        task_dir = make_task_dir(tmp_path)
        result = _call(task_dir, use_real=True)
        # Stub adapter outputs a marker at the beginning of raw_output.
        # Real adapters may echo test/source text that mentions the marker, so
        # check the structured stub prefix instead of any incidental substring.
        assert not (result.raw_output or "").startswith("<stub-claude-output")
        # Status is either success (binary found & ran) or failure (binary missing)
        assert result.status in ("success", "failure")

    def test_use_real_unknown_real_adapter(self, tmp_path, make_task_dir):
        """An adapter_target not in REAL_REGISTRY should fail with a descriptive error."""
        task_dir = make_task_dir(tmp_path)
        result = _call(task_dir, adapter_target="unknown", use_real=True)
        assert result.status == "failure"
        assert "real adapter unsupported" in (result.error or "")


class TestExecuteParallelWorkersRegression:
    def test_worker_exception_is_recorded_without_aborting_batch(self, tmp_path):
        task_dir = tmp_path / "task"
        task_dir.mkdir()
        ok_wt = tmp_path / "ok-worktree"
        bad_wt = tmp_path / "bad-worktree"
        ok_wt.mkdir()
        bad_wt.mkdir()
        workers = [
            {
                "plan_task_id": "ok",
                "status": "allocated",
                "owned_paths": ["ok.txt"],
                "output_ref": "workers/ok/output.md",
                "worktree": {"path": str(ok_wt)},
            },
            {
                "plan_task_id": "bad",
                "status": "allocated",
                "owned_paths": ["bad.txt"],
                "output_ref": "workers/bad/output.md",
                "worktree": {"path": str(bad_wt)},
            },
        ]

        def _fake_execute_stage(*, task_dir, **kwargs):
            if task_dir == bad_wt:
                raise RuntimeError("boom")
            return RunTaskResult(status="success", raw_output="ok")

        with patch("forgeflow_runtime.engine.execute_stage", side_effect=_fake_execute_stage):
            results = execute_parallel_workers(
                task_dir=task_dir,
                task_id="task-001",
                route="medium",
                workers=workers,
                max_workers=2,
            )

        assert [item["plan_task_id"] for item in results] == ["ok", "bad"]
        assert results[0]["result"].status == "success"
        assert results[1]["result"].status == "failure"
        assert "boom" in (results[1]["result"].error or "")
        assert json.loads((task_dir / "workers" / "ok" / "worker-state.json").read_text())["status"] == "completed"
        assert json.loads((task_dir / "workers" / "bad" / "worker-state.json").read_text())["status"] == "exception"

    def test_worker_output_ref_cannot_escape_task_dir(self, tmp_path):
        task_dir = tmp_path / "task"
        worktree = tmp_path / "worker"
        task_dir.mkdir()
        worktree.mkdir()
        outside = tmp_path / "escaped.md"
        worker = {
            "plan_task_id": "escape",
            "status": "allocated",
            "owned_paths": ["x.txt"],
            "output_ref": "../escaped.md",
            "worktree": {"path": str(worktree)},
        }

        with patch("forgeflow_runtime.engine.execute_stage", return_value=RunTaskResult(status="success", raw_output="ok")):
            results = execute_parallel_workers(
                task_dir=task_dir,
                task_id="task-001",
                route="medium",
                workers=[worker],
            )

        assert results[0]["result"].status == "success"
        assert not outside.exists()
        assert (task_dir / "workers" / "escape" / "worker-state.json").exists()
