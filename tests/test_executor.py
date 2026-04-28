from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from forgeflow_runtime.executor import (
    ExecutorError,
    RunTaskRequest,
    RunTaskResult,
    StubClaudeAdapter,
    StubCodexAdapter,
    dispatch,
    list_adapters,
)


class TestStubClaudeAdapter:
    def test_successful_run(self):
        adapter = StubClaudeAdapter()
        req = RunTaskRequest(
            prompt="hello world",
            role="worker",
            stage="execute",
            task_dir=Path("."),
            task_id="t1",
            token_budget_input=8000,
            token_budget_output=4000,
            adapter_target="claude",
        )
        result = adapter.run_task(req)
        assert result.status == "success"
        assert result.token_usage["input"] > 0
        assert result.token_usage["output"] > 0
        assert "stub-claude-output" in (result.raw_output or "")

    def test_input_budget_block(self):
        adapter = StubClaudeAdapter()
        req = RunTaskRequest(
            prompt="x" * 40000,  # ~10000 tokens at 4 chars/token
            role="worker",
            stage="execute",
            task_dir=Path("."),
            task_id="t1",
            token_budget_input=100,
            token_budget_output=4000,
            adapter_target="claude",
        )
        result = adapter.run_task(req)
        assert result.status == "blocked"
        assert "input budget" in (result.error or "")

    def test_output_budget_block(self):
        adapter = StubClaudeAdapter()
        req = RunTaskRequest(
            prompt="hi",
            role="worker",
            stage="execute",
            task_dir=Path("."),
            task_id="t1",
            token_budget_input=8000,
            token_budget_output=1,
            adapter_target="claude",
        )
        result = adapter.run_task(req)
        assert result.status == "blocked"
        assert "output budget" in (result.error or "")

    def test_estimate_tokens(self):
        adapter = StubClaudeAdapter()
        assert adapter.estimate_tokens("abcd") == 1
        assert adapter.estimate_tokens("a" * 40) == 10


class TestStubCodexAdapter:
    def test_successful_run(self):
        adapter = StubCodexAdapter()
        req = RunTaskRequest(
            prompt="print hello",
            role="worker",
            stage="execute",
            task_dir=Path("."),
            task_id="t2",
            token_budget_input=8000,
            token_budget_output=4000,
            adapter_target="codex",
        )
        result = adapter.run_task(req)
        assert result.status == "success"
        assert "stub-codex-output" in (result.raw_output or "")


class TestDispatch:
    def test_dispatch_claude(self):
        req = RunTaskRequest(
            prompt="test",
            role="coordinator",
            stage="clarify",
            task_dir=Path("."),
            task_id="t1",
            token_budget_input=8000,
            token_budget_output=4000,
            adapter_target="claude",
        )
        result = dispatch(req)
        assert result.status == "success"

    def test_dispatch_unknown_target(self):
        req = RunTaskRequest(
            prompt="test",
            role="coordinator",
            stage="clarify",
            task_dir=Path("."),
            task_id="t1",
            token_budget_input=8000,
            token_budget_output=4000,
            adapter_target="gemini",
        )
        result = dispatch(req)
        assert result.status == "failure"
        assert "unknown adapter target" in (result.error or "")

    def test_list_adapters(self):
        adapters = list_adapters()
        assert set(adapters) == {"claude", "codex"}


class TestArtifactStreaming:
    def test_artifacts_produced(self):
        adapter = StubClaudeAdapter()
        req = RunTaskRequest(
            prompt="test",
            role="worker",
            stage="execute",
            task_dir=Path("."),
            task_id="t1",
            token_budget_input=8000,
            token_budget_output=4000,
            adapter_target="claude",
            artifacts_to_stream=["run-state", "decision-log"],
        )
        result = adapter.run_task(req)
        assert result.status == "success"
        assert "run-state" in result.artifacts_produced
        assert "decision-log" in result.artifacts_produced
