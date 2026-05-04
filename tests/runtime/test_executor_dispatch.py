"""Comprehensive tests for forgeflow_runtime.executor."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from forgeflow_runtime.executor import (
    STUB_REGISTRY,
    REAL_REGISTRY,
    ClaudeCodeAdapter,
    CodexCLIAdapter,
    ExecutorError,
    ExecutorAdapter,
    RunTaskRequest,
    RunTaskResult,
    StubClaudeAdapter,
    StubCodexAdapter,
    _estimate_tokens,
    dispatch,
    list_adapters,
    orchestrate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(
    prompt: str = "Hello world",
    adapter_target: str = "claude",
    token_budget_input: int = 100,
    token_budget_output: int = 100,
    artifacts_to_stream: list[str] | None = None,
    task_dir: Path | None = None,
) -> RunTaskRequest:
    return RunTaskRequest(
        prompt=prompt,
        role="coder",
        stage="implement",
        task_dir=task_dir or Path("/tmp/forgeflow-test-task"),
        task_id="t-001",
        token_budget_input=token_budget_input,
        token_budget_output=token_budget_output,
        adapter_target=adapter_target,
        artifacts_to_stream=artifacts_to_stream,
        extra=None,
    )


# ---------------------------------------------------------------------------
# 1-2: _estimate_tokens
# ---------------------------------------------------------------------------

class TestEstimateTokens:
    def test_estimate_tokens_basic(self) -> None:
        # 16 chars => 16 // 4 = 4 tokens
        assert _estimate_tokens("1234567890123456") == 4

    def test_estimate_tokens_empty(self) -> None:
        # Empty string => max(1, 0) = 1
        assert _estimate_tokens("") == 1

    def test_estimate_tokens_short(self) -> None:
        # 3 chars => max(1, 0) = 1
        assert _estimate_tokens("abc") == 1


# ---------------------------------------------------------------------------
# 3-4: Dataclasses
# ---------------------------------------------------------------------------

class TestDataclasses:
    def test_run_task_request_dataclass(self, tmp_path: Path) -> None:
        req = _make_request(task_dir=tmp_path, artifacts_to_stream=["plan.json"])
        assert req.prompt == "Hello world"
        assert req.role == "coder"
        assert req.stage == "implement"
        assert req.task_dir == tmp_path
        assert req.task_id == "t-001"
        assert req.token_budget_input == 100
        assert req.token_budget_output == 100
        assert req.adapter_target == "claude"
        assert req.artifacts_to_stream == ["plan.json"]
        assert req.extra is None
        # Frozen — cannot assign
        with pytest.raises(dataclasses.FrozenInstanceError):
            req.prompt = "new"  # type: ignore[misc]

    def test_run_task_result_dataclass(self) -> None:
        result = RunTaskResult(status="success")
        assert result.status == "success"
        assert result.artifacts_produced == []
        assert result.token_usage == {}
        assert result.raw_output is None
        assert result.error is None
        # Frozen
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.status = "failure"  # type: ignore[misc]

    def test_run_task_result_with_all_fields(self) -> None:
        result = RunTaskResult(
            status="partial",
            artifacts_produced=["a.txt"],
            token_usage={"input": 10, "output": 5},
            raw_output="some output",
            error="timeout",
        )
        assert result.status == "partial"
        assert result.artifacts_produced == ["a.txt"]
        assert result.token_usage == {"input": 10, "output": 5}
        assert result.raw_output == "some output"
        assert result.error == "timeout"


# ---------------------------------------------------------------------------
# 5-9: Stub adapters
# ---------------------------------------------------------------------------

class TestStubClaudeAdapter:
    def test_stub_claude_success(self) -> None:
        adapter = StubClaudeAdapter()
        req = _make_request()
        result = adapter.run_task(req)
        assert result.status == "success"
        assert result.raw_output is not None
        assert "stub-claude-output" in result.raw_output
        assert "stage=implement" in result.raw_output
        assert result.token_usage["input"] > 0
        assert result.token_usage["output"] > 0

    def test_stub_claude_blocked_input_budget(self) -> None:
        adapter = StubClaudeAdapter()
        # Very long prompt that exceeds the tiny input budget
        long_prompt = "x" * 1000  # ~250 tokens
        req = _make_request(prompt=long_prompt, token_budget_input=10)
        result = adapter.run_task(req)
        assert result.status == "blocked"
        assert "exceed input budget" in result.error
        assert result.token_usage["input"] > 10

    def test_stub_claude_blocked_output_budget(self) -> None:
        adapter = StubClaudeAdapter()
        # The simulated output is "<stub-claude-output stage=implement role=coder>"
        # which is ~55 chars => ~13 tokens. Set output budget lower.
        simulated_len = len("<stub-claude-output stage=implement role=coder>")
        simulated_tokens = simulated_len // 4  # should be ~13
        req = _make_request(token_budget_output=max(1, simulated_tokens - 1))
        result = adapter.run_task(req)
        assert result.status == "blocked"
        assert "exceed output budget" in result.error

    def test_stub_claude_artifacts_to_stream(self) -> None:
        adapter = StubClaudeAdapter()
        req = _make_request(artifacts_to_stream=["plan.json", "code.py"])
        result = adapter.run_task(req)
        assert result.status == "success"
        assert result.artifacts_produced == ["plan.json", "code.py"]


class TestStubCodexAdapter:
    def test_stub_codex_success(self) -> None:
        adapter = StubCodexAdapter()
        req = _make_request(adapter_target="codex")
        result = adapter.run_task(req)
        assert result.status == "success"
        assert result.raw_output is not None
        assert "stub-codex-output" in result.raw_output
        assert "stage=implement" in result.raw_output

    def test_stub_codex_blocked_input_budget(self) -> None:
        adapter = StubCodexAdapter()
        long_prompt = "x" * 1000
        req = _make_request(prompt=long_prompt, token_budget_input=10, adapter_target="codex")
        result = adapter.run_task(req)
        assert result.status == "blocked"
        assert "exceed input budget" in result.error


# ---------------------------------------------------------------------------
# 10-13: dispatch
# ---------------------------------------------------------------------------

class TestDispatch:
    def test_dispatch_stub_default(self) -> None:
        req = _make_request(adapter_target="claude")
        result = dispatch(req, use_real=False)
        assert result.status == "success"
        assert "stub-claude-output" in result.raw_output

    def test_dispatch_stub_codex(self) -> None:
        req = _make_request(adapter_target="codex")
        result = dispatch(req, use_real=False)
        assert result.status == "success"
        assert "stub-codex-output" in result.raw_output

    def test_dispatch_unknown_adapter(self) -> None:
        req = _make_request(adapter_target="nonexistent")
        result = dispatch(req, use_real=False)
        assert result.status == "failure"
        assert "unknown adapter target" in result.error

    def test_dispatch_real_unknown_adapter(self) -> None:
        req = _make_request(adapter_target="nonexistent")
        result = dispatch(req, use_real=True)
        assert result.status == "failure"
        assert "real adapter unsupported" in result.error


# ---------------------------------------------------------------------------
# 14-15: list_adapters
# ---------------------------------------------------------------------------

class TestListAdapters:
    def test_list_adapters_stub_only(self) -> None:
        adapters = list_adapters(include_real=False)
        assert sorted(adapters) == ["claude", "codex"]

    def test_list_adapters_include_real(self) -> None:
        adapters = list_adapters(include_real=True)
        assert sorted(adapters) == ["claude", "codex"]


# ---------------------------------------------------------------------------
# 16-18: Real adapters (missing binary)
# ---------------------------------------------------------------------------

class TestRealAdaptersMissingBinary:
    def test_claude_code_adapter_missing_binary(self) -> None:
        with patch("forgeflow_runtime.executor.shutil.which", return_value=None):
            adapter = ClaudeCodeAdapter()
        req = _make_request()
        result = adapter.run_task(req)
        assert result.status == "failure"
        assert "claude binary not found" in result.error

    def test_codex_cli_adapter_missing_binary(self) -> None:
        with patch("forgeflow_runtime.executor.shutil.which", return_value=None):
            adapter = CodexCLIAdapter()
        req = _make_request(adapter_target="codex")
        result = adapter.run_task(req)
        assert result.status == "failure"
        assert "codex binary not found" in result.error

    def test_claude_code_adapter_budget_check(self) -> None:
        """Budget check runs even before binary is invoked."""
        with patch("forgeflow_runtime.executor.shutil.which", return_value="/usr/bin/claude"):
            adapter = ClaudeCodeAdapter()
        long_prompt = "x" * 1000  # ~250 tokens
        req = _make_request(prompt=long_prompt, token_budget_input=10)
        result = adapter.run_task(req)
        assert result.status == "blocked"
        assert "exceed input budget" in result.error
        # The subprocess should NOT have been called
        assert result.token_usage["output"] == 0


# ---------------------------------------------------------------------------
# 19-20: orchestrate
# ---------------------------------------------------------------------------

class TestOrchestrate:
    def test_orchestrate_no_policy_falls_back(self) -> None:
        """With policy=None, orchestrate falls back to dispatch (stub)."""
        req = _make_request(adapter_target="claude")
        result = orchestrate(req, policy=None, use_real=False)
        assert result.status == "success"
        assert "stub-claude-output" in result.raw_output

    def test_orchestrate_no_policy_falls_back_codex(self) -> None:
        req = _make_request(adapter_target="codex")
        result = orchestrate(req, policy=None, use_real=False)
        assert result.status == "success"
        assert "stub-codex-output" in result.raw_output

    def test_orchestrate_with_strategy(self) -> None:
        """Policy with orchestration.strategy triggers run_orchestration."""
        req = _make_request(adapter_target="claude")

        # Create a mock policy object with orchestration config
        mock_policy = MagicMock()
        mock_policy.orchestration = {
            "strategy": "consensus",
            "providers": ["claude", "codex"],
            "fallback": "first",
            "timeout": 30,
            "consensus_threshold": 0.6,
        }

        # Mock run_orchestration to avoid real multi-adapter calls
        mock_result = MagicMock()
        mock_result.to_run_task_result.return_value = RunTaskResult(
            status="success",
            raw_output="orchestrated output",
            token_usage={"input": 10, "output": 5},
            artifacts_produced=["a.txt"],
        )

        with patch(
            "forgeflow_runtime.executor.dispatch",
            wraps=dispatch,
        ) as mock_dispatch, \
             patch(
            "forgeflow_runtime.orchestra.run_orchestration",
            return_value=mock_result,
        ) as mock_orch:
            result = orchestrate(req, policy=mock_policy, use_real=False)

        assert result.status == "success"
        assert result.raw_output == "orchestrated output"
        mock_orch.assert_called_once()
        # dispatch should NOT have been called (orchestration path taken)
        mock_dispatch.assert_not_called()

    def test_orchestrate_empty_orchestration_dict_falls_back(self) -> None:
        """Policy with empty orchestration dict (no strategy) falls back."""
        req = _make_request(adapter_target="claude")
        mock_policy = MagicMock()
        mock_policy.orchestration = {}

        result = orchestrate(req, policy=mock_policy, use_real=False)
        assert result.status == "success"
        assert "stub-claude-output" in result.raw_output

    def test_orchestrate_none_orchestration_falls_back(self) -> None:
        """Policy with orchestration=None falls back."""
        req = _make_request(adapter_target="claude")
        mock_policy = MagicMock()
        mock_policy.orchestration = None

        result = orchestrate(req, policy=mock_policy, use_real=False)
        assert result.status == "success"
        assert "stub-claude-output" in result.raw_output


# ---------------------------------------------------------------------------
# Additional: ExecutorError, protocol, registries
# ---------------------------------------------------------------------------

class TestMiscellaneous:
    def test_executor_error_is_exception(self) -> None:
        with pytest.raises(ExecutorError):
            raise ExecutorError("test error")

    def test_stub_registry_keys(self) -> None:
        assert set(STUB_REGISTRY.keys()) == {"claude", "codex"}

    def test_real_registry_keys(self) -> None:
        assert set(REAL_REGISTRY.keys()) == {"claude", "codex"}

    def test_stub_claude_adapter_name(self) -> None:
        assert StubClaudeAdapter().name == "claude"

    def test_stub_codex_adapter_name(self) -> None:
        assert StubCodexAdapter().name == "codex"

    def test_estimate_tokens_on_adapter(self) -> None:
        adapter = StubClaudeAdapter()
        assert adapter.estimate_tokens("abcdefghijklmnop") == 4
