from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class ExecutorError(Exception):
    """Raised when an executor cannot fulfill a run_task request."""


@dataclass(frozen=True)
class RunTaskRequest:
    """Contract for dispatching a single stage execution to an adapter target."""

    prompt: str
    role: str
    stage: str
    task_dir: Path
    task_id: str
    token_budget_input: int
    token_budget_output: int
    adapter_target: str  # e.g. "claude", "codex", "gemini"
    artifacts_to_stream: list[str] | None = None
    extra: dict[str, Any] | None = None


@dataclass(frozen=True)
class RunTaskResult:
    """Result of a single stage execution attempt."""

    status: str  # "success", "failure", "blocked", "partial"
    artifacts_produced: list[str] = field(default_factory=list)
    token_usage: dict[str, int] = field(default_factory=dict)
    raw_output: str | None = None
    error: str | None = None
    execution_mode: str | None = None


class ExecutorAdapter(Protocol):
    """Protocol for runtime-specific adapters (Claude, Codex, Gemini)."""

    @property
    def name(self) -> str:
        ...

    def run_task(self, request: RunTaskRequest) -> RunTaskResult:
        ...

    def estimate_tokens(self, text: str) -> int:
        ...


def _estimate_tokens(text: str) -> int:
    # Naïve approximation: 1 token ~= 4 chars for English/mixed
    return max(1, len(text) // 4)


class _BaseStubAdapter:
    """Shared stub logic for all stub adapters."""

    def estimate_tokens(self, text: str) -> int:
        return _estimate_tokens(text)

    def _run_stub(self, request: RunTaskRequest, label: str) -> RunTaskResult:
        prompt_tokens = self.estimate_tokens(request.prompt)
        if prompt_tokens > request.token_budget_input:
            return RunTaskResult(
                status="blocked",
                error=f"prompt tokens {prompt_tokens} exceed input budget {request.token_budget_input}",
                token_usage={"input": prompt_tokens, "output": 0},
            )

        simulated_output = f"<{label} stage={request.stage} role={request.role}>"
        output_tokens = self.estimate_tokens(simulated_output)

        if output_tokens > request.token_budget_output:
            return RunTaskResult(
                status="blocked",
                error=f"output tokens {output_tokens} exceed output budget {request.token_budget_output}",
                token_usage={"input": prompt_tokens, "output": output_tokens},
            )

        artifacts = list(request.artifacts_to_stream or [])
        return RunTaskResult(
            status="success",
            artifacts_produced=artifacts,
            token_usage={"input": prompt_tokens, "output": output_tokens},
            raw_output=simulated_output,
        )


class StubClaudeAdapter(_BaseStubAdapter):
    """Stub adapter for Claude Code / Claude CLI workflows."""

    name = "claude"

    def run_task(self, request: RunTaskRequest) -> RunTaskResult:
        return self._run_stub(request, "stub-claude-output")


class StubCodexAdapter(_BaseStubAdapter):
    """Stub adapter for OpenAI Codex CLI workflows."""

    name = "codex"

    def run_task(self, request: RunTaskRequest) -> RunTaskResult:
        return self._run_stub(request, "stub-codex-output")


class StubGeminiAdapter(_BaseStubAdapter):
    """Stub adapter for Google Gemini CLI workflows."""

    name = "gemini"

    def run_task(self, request: RunTaskRequest) -> RunTaskResult:
        return self._run_stub(request, "stub-gemini-output")


class _BaseRealCLIAdapter:
    """Shared subprocess/budget handling for real CLI adapters."""

    name: str
    binary_name: str
    missing_binary_hint: str

    def __init__(self, timeout: int = 300) -> None:
        self.timeout = timeout
        self._binary = shutil.which(self.binary_name)

    def estimate_tokens(self, text: str) -> int:
        return _estimate_tokens(text)

    def build_command(self, request: RunTaskRequest) -> list[str]:
        raise NotImplementedError

    def _subprocess_error_prefix(self) -> str:
        return self.binary_name

    def run_task(self, request: RunTaskRequest) -> RunTaskResult:
        if not self._binary:
            return RunTaskResult(status="failure", error=self.missing_binary_hint)

        prompt_tokens = self.estimate_tokens(request.prompt)
        if prompt_tokens > request.token_budget_input:
            return RunTaskResult(
                status="blocked",
                error=f"prompt tokens {prompt_tokens} exceed input budget {request.token_budget_input}",
                token_usage={"input": prompt_tokens, "output": 0},
            )

        try:
            proc = subprocess.run(
                self.build_command(request),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(request.task_dir),
            )
        except subprocess.TimeoutExpired:
            return RunTaskResult(
                status="failure",
                error=f"{self._subprocess_error_prefix()} timed out after {self.timeout}s",
                token_usage={"input": prompt_tokens, "output": 0},
            )
        except Exception as exc:
            return RunTaskResult(
                status="failure",
                error=f"{self._subprocess_error_prefix()} subprocess error: {exc}",
                token_usage={"input": prompt_tokens, "output": 0},
            )

        output_tokens = self.estimate_tokens(proc.stdout)
        if output_tokens > request.token_budget_output:
            return RunTaskResult(
                status="blocked",
                error=f"output tokens {output_tokens} exceed output budget {request.token_budget_output}",
                token_usage={"input": prompt_tokens, "output": output_tokens},
            )

        status = "success" if proc.returncode == 0 else "failure"
        error = None
        if proc.returncode != 0:
            error = f"{self._subprocess_error_prefix()} exited {proc.returncode}: {proc.stderr[:500]}"

        return RunTaskResult(
            status=status,
            artifacts_produced=list(request.artifacts_to_stream or []),
            token_usage={"input": prompt_tokens, "output": output_tokens},
            raw_output=proc.stdout,
            error=error,
        )


class ClaudeCodeAdapter(_BaseRealCLIAdapter):
    """Real adapter that invokes the Claude Code CLI (``claude``)."""

    name = "claude"
    binary_name = "claude"
    missing_binary_hint = "claude binary not found on PATH; install/auth Claude Code or omit --real to use the safe stub"

    def build_command(self, request: RunTaskRequest) -> list[str]:
        return [
            self._binary or self.binary_name,
            "-p",
            "--dangerously-skip-permissions",
            "--bare",
            request.prompt,
        ]


class CodexCLIAdapter(_BaseRealCLIAdapter):
    """Real adapter that invokes the OpenAI Codex CLI (``codex``)."""

    name = "codex"
    binary_name = "codex"
    missing_binary_hint = "codex binary not found on PATH; install/auth Codex CLI or omit --real to use the safe stub"

    def build_command(self, request: RunTaskRequest) -> list[str]:
        return [self._binary or self.binary_name, "exec", request.prompt]


class GeminiCLIAdapter(_BaseRealCLIAdapter):
    """Real adapter that invokes the Google Gemini CLI (``gemini``)."""

    name = "gemini"
    binary_name = "gemini"
    missing_binary_hint = "gemini binary not found on PATH; install/auth Gemini CLI or omit --real to use the safe stub"

    def build_command(self, request: RunTaskRequest) -> list[str]:
        return [self._binary or self.binary_name, "--prompt", "--yolo", request.prompt]


STUB_REGISTRY: dict[str, ExecutorAdapter] = {
    "claude": StubClaudeAdapter(),
    "codex": StubCodexAdapter(),
    "gemini": StubGeminiAdapter(),
}


REAL_REGISTRY: dict[str, ExecutorAdapter] = {
    "claude": ClaudeCodeAdapter(),
    "codex": CodexCLIAdapter(),
    "gemini": GeminiCLIAdapter(),
}
SUPPORTED_REAL_ADAPTERS = tuple(sorted(REAL_REGISTRY))


def dispatch(request: RunTaskRequest, *, use_real: bool = False) -> RunTaskResult:
    """Dispatch a run_task request to the named adapter target.

    Args:
        request: The execution request.
        use_real: If ``True``, try to use real CLI adapters (Claude Code,
            Codex CLI, Gemini CLI) when available.  Defaults to ``False`` (stubs) so
            tests and local development do not incur API costs.
    """
    execution_mode = "real" if use_real else "stub"
    if use_real:
        adapter = REAL_REGISTRY.get(request.adapter_target)
        if adapter is None:
            return RunTaskResult(
                status="failure",
                error=(
                    f"real adapter unsupported: {request.adapter_target}; "
                    f"supported real adapters: {', '.join(SUPPORTED_REAL_ADAPTERS)}"
                ),
                execution_mode=execution_mode,
            )
        result = adapter.run_task(request)
        return RunTaskResult(
            status=result.status,
            artifacts_produced=result.artifacts_produced,
            token_usage=result.token_usage,
            raw_output=result.raw_output,
            error=result.error,
            execution_mode=execution_mode,
        )

    adapter = STUB_REGISTRY.get(request.adapter_target)
    if adapter is None:
        return RunTaskResult(
            status="failure",
            error=f"unknown adapter target: {request.adapter_target}",
            execution_mode=execution_mode,
        )
    result = adapter.run_task(request)
    return RunTaskResult(
        status=result.status,
        artifacts_produced=result.artifacts_produced,
        token_usage=result.token_usage,
        raw_output=result.raw_output,
        error=result.error,
        execution_mode=execution_mode,
    )


def list_adapters(*, include_real: bool = False) -> list[str]:
    if include_real:
        return sorted(set(STUB_REGISTRY) | set(REAL_REGISTRY))
    return sorted(STUB_REGISTRY.keys())


def orchestrate(
    request: RunTaskRequest,
    policy: Any | None = None,
    *,
    use_real: bool = False,
) -> RunTaskResult:
    """Orchestrate a run_task request, using multi-model if policy configures it.

    If *policy* has an ``orchestration`` dict with a ``strategy`` key, the
    request is fanned out to multiple adapters using the configured strategy.
    Otherwise, falls back to single-adapter :func:`dispatch`.

    Args:
        request: The execution request.
        policy: A RuntimePolicy (or any object with an ``orchestration`` attr).
        use_real: Whether to use real CLI adapters.

    Returns:
        RunTaskResult from either orchestration or single dispatch.
    """
    orch_config = getattr(policy, "orchestration", None)
    if isinstance(orch_config, dict) and orch_config.get("strategy"):
        from experimental.orchestra import OrchestrationConfig, run_orchestration

        config = OrchestrationConfig(
            strategy=orch_config["strategy"],
            providers=orch_config.get("providers", [request.adapter_target]),
            fallback=orch_config.get("fallback", "first"),
            timeout=float(orch_config.get("timeout", 120.0)),
            consensus_threshold=float(orch_config.get("consensus_threshold", 0.6)),
        )
        result = run_orchestration(request, config, use_real=use_real).to_run_task_result()
        return RunTaskResult(
            status=result.status,
            artifacts_produced=result.artifacts_produced,
            token_usage=result.token_usage,
            raw_output=result.raw_output,
            error=result.error,
            execution_mode="real" if use_real else "stub",
        )

    return dispatch(request, use_real=use_real)
