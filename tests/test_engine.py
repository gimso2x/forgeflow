from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from forgeflow_runtime.engine import execute_parallel_workers, execute_stage
from forgeflow_runtime.executor import RunTaskResult


class TestExecuteStage:
    def test_successful_wiring(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "brief.json").write_text(json.dumps({"task_id": "t1", "objective": "test"}))
            result = execute_stage(
                task_dir=p,
                task_id="t1",
                stage="execute",
                route="medium",
                role="worker",
                adapter_target="claude",
            )
            assert isinstance(result, RunTaskResult)
            assert result.status == "success"
            assert result.token_usage["input"] > 0
            assert result.token_usage["output"] > 0
            assert "stub-claude-output" in (result.raw_output or "")

    def test_codex_target(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "brief.json").write_text(json.dumps({"task_id": "t2", "objective": "test"}))
            result = execute_stage(
                task_dir=p,
                task_id="t2",
                stage="plan",
                route="medium",
                role="planner",
                adapter_target="codex",
            )
            assert result.status == "success"
            assert "stub-codex-output" in (result.raw_output or "")

    def test_codex_target(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "brief.json").write_text(json.dumps({"task_id": "t3", "objective": "test"}))
            result = execute_stage(
                task_dir=p,
                task_id="t3",
                stage="clarify",
                route="small",
                role="coordinator",
                adapter_target="codex",
            )
            assert result.status == "success"
            assert "stub-codex-output" in (result.raw_output or "")

    def test_extra_context_passed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "brief.json").write_text(json.dumps({"task_id": "t4", "objective": "test"}))
            result = execute_stage(
                task_dir=p,
                task_id="t4",
                stage="execute",
                route="high",
                role="worker",
                adapter_target="claude",
                extra_context={"risk_flag": "high"},
                artifacts_to_stream=["decision-log"],
            )
            assert result.status == "success"
            assert "decision-log" in result.artifacts_produced

    def test_unknown_target_returns_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "brief.json").write_text(json.dumps({"task_id": "t5", "objective": "test"}))
            result = execute_stage(
                task_dir=p,
                task_id="t5",
                stage="execute",
                route="small",
                role="worker",
                adapter_target="gemini",
            )
            assert result.status == "failure"
            assert "unknown adapter target" in (result.error or "")

    def test_token_budget_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            # Generator truncates artifact previews to ~1200 chars, so a huge
            # brief does not automatically block. Budget enforcement is proven
            # at the executor level in test_executor.py. Here we verify the
            # engine still reports executor-level blocks faithfully.
            result = execute_stage(
                task_dir=p,
                task_id="t6",
                stage="execute",
                route="small",
                role="worker",
                adapter_target="claude",
                extra_context={"_force_huge_prompt": "x" * 40000},
            )
            # The extra_context is included raw in the prompt, so this should
            # exceed the default 8000-token input budget (~40000 chars / 4).
            assert result.status == "blocked"
            assert "budget" in (result.error or "")


class TestExecuteParallelWorkers:
    def test_dispatches_each_worker_in_its_own_worktree_and_updates_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            task_dir = root / ".forgeflow" / "tasks" / "t-parallel"
            task_dir.mkdir(parents=True)
            (task_dir / "brief.json").write_text(json.dumps({"task_id": "t-parallel", "objective": "parallel"}))

            worker_a = root / "worktrees" / "ui"
            worker_b = root / "worktrees" / "api"
            worker_a.mkdir(parents=True)
            worker_b.mkdir(parents=True)

            workers = [
                {
                    "schema_version": "1.0",
                    "task_id": "t-parallel",
                    "plan_task_id": "ui",
                    "status": "pending",
                    "owned_paths": ["app/page.tsx"],
                    "worktree": {"path": str(worker_a), "branch": "ff/ui", "active": True},
                    "output_ref": "workers/ui/output.md",
                },
                {
                    "schema_version": "1.0",
                    "task_id": "t-parallel",
                    "plan_task_id": "api",
                    "status": "pending",
                    "owned_paths": ["api/route.ts"],
                    "worktree": {"path": str(worker_b), "branch": "ff/api", "active": True},
                    "output_ref": "workers/api/output.md",
                },
            ]

            results = execute_parallel_workers(
                task_dir=task_dir,
                task_id="t-parallel",
                route="medium",
                adapter_target="claude",
                workers=workers,
            )

            assert [item["plan_task_id"] for item in results] == ["ui", "api"]
            assert all(item["result"].status == "success" for item in results)
            assert workers[0]["status"] == "completed"
            assert workers[1]["status"] == "completed"
            assert "stub-claude-output" in (task_dir / "workers" / "ui" / "output.md").read_text()
            assert "stub-claude-output" in (task_dir / "workers" / "api" / "output.md").read_text()
            assert "app/page.tsx" in (task_dir / "workers" / "ui" / "output.md").read_text()
