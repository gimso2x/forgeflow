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
    adapter_target: str  # e.g. "claude", "codex"
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


class ExecutorAdapter(Protocol):
    """Protocol for runtime-specific adapters (Claude, Codex)."""

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



class ClaudeCodeAdapter:
    """Real adapter that invokes the Claude Code CLI (``claude``).

    Uses ``claude -p`` for non-interactive prompt mode.  Assumes the
    ``claude`` binary is on ``$PATH`` and authenticated.
    """

    name = "claude"

    def __init__(self, timeout: int = 300) -> None:
        self.timeout = timeout
        self._binary = shutil.which("claude")

    def estimate_tokens(self, text: str) -> int:
        return _estimate_tokens(text)

    def run_task(self, request: RunTaskRequest) -> RunTaskResult:
        if not self._binary:
            return RunTaskResult(
                status="failure",
                error="claude binary not found on PATH; install/auth Claude Code or omit --real to use the safe stub",
            )

        prompt_tokens = self.estimate_tokens(request.prompt)
        if prompt_tokens > request.token_budget_input:
            return RunTaskResult(
                status="blocked",
                error=f"prompt tokens {prompt_tokens} exceed input budget {request.token_budget_input}",
                token_usage={"input": prompt_tokens, "output": 0},
            )

        cmd = [
            self._binary,
            "-p",
            "--dangerously-skip-permissions",
            "--bare",
            request.prompt,
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(request.task_dir),
            )
        except subprocess.TimeoutExpired as exc:
            return RunTaskResult(
                status="failure",
                error=f"claude timed out after {self.timeout}s",
                token_usage={"input": prompt_tokens, "output": 0},
            )
        except Exception as exc:
            return RunTaskResult(
                status="failure",
                error=f"claude subprocess error: {exc}",
                token_usage={"input": prompt_tokens, "output": 0},
            )

        output_tokens = self.estimate_tokens(proc.stdout)
        if output_tokens > request.token_budget_output:
            return RunTaskResult(
                status="blocked",
                error=f"output tokens {output_tokens} exceed output budget {request.token_budget_output}",
                token_usage={"input": prompt_tokens, "output": output_tokens},
            )

        artifacts = list(request.artifacts_to_stream or [])
        status = "success" if proc.returncode == 0 else "failure"
        error = None
        if proc.returncode != 0:
            error = f"claude exited {proc.returncode}: {proc.stderr[:500]}"

        return RunTaskResult(
            status=status,
            artifacts_produced=artifacts,
            token_usage={"input": prompt_tokens, "output": output_tokens},
            raw_output=proc.stdout,
            error=error,
        )


class CodexCLIAdapter:
    """Real adapter that invokes the OpenAI Codex CLI (``codex``).

    Uses ``codex exec`` for non-interactive execution.  Assumes the
    ``codex`` binary is on ``$PATH`` and authenticated.
    """

    name = "codex"

    def __init__(self, timeout: int = 300) -> None:
        self.timeout = timeout
        self._binary = shutil.which("codex")

    def estimate_tokens(self, text: str) -> int:
        return _estimate_tokens(text)

    def run_task(self, request: RunTaskRequest) -> RunTaskResult:
        if not self._binary:
            return RunTaskResult(
                status="failure",
                error="codex binary not found on PATH; install/auth Codex CLI or omit --real to use the safe stub",
            )

        prompt_tokens = self.estimate_tokens(request.prompt)
        if prompt_tokens > request.token_budget_input:
            return RunTaskResult(
                status="blocked",
                error=f"prompt tokens {prompt_tokens} exceed input budget {request.token_budget_input}",
                token_usage={"input": prompt_tokens, "output": 0},
            )

        cmd = [self._binary, "exec", request.prompt]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(request.task_dir),
            )
        except subprocess.TimeoutExpired as exc:
            return RunTaskResult(
                status="failure",
                error=f"codex timed out after {self.timeout}s",
                token_usage={"input": prompt_tokens, "output": 0},
            )
        except Exception as exc:
            return RunTaskResult(
                status="failure",
                error=f"codex subprocess error: {exc}",
                token_usage={"input": prompt_tokens, "output": 0},
            )

        output_tokens = self.estimate_tokens(proc.stdout)
        if output_tokens > request.token_budget_output:
            return RunTaskResult(
                status="blocked",
                error=f"output tokens {output_tokens} exceed output budget {request.token_budget_output}",
                token_usage={"input": prompt_tokens, "output": output_tokens},
            )

        artifacts = list(request.artifacts_to_stream or [])
        status = "success" if proc.returncode == 0 else "failure"
        error = None
        if proc.returncode != 0:
            error = f"codex exited {proc.returncode}: {proc.stderr[:500]}"

        return RunTaskResult(
            status=status,
            artifacts_produced=artifacts,
            token_usage={"input": prompt_tokens, "output": output_tokens},
            raw_output=proc.stdout,
            error=error,
        )


STUB_REGISTRY: dict[str, ExecutorAdapter] = {
    "claude": StubClaudeAdapter(),
    "codex": StubCodexAdapter(),
}


REAL_REGISTRY: dict[str, ExecutorAdapter] = {
    "claude": ClaudeCodeAdapter(),
    "codex": CodexCLIAdapter(),
}
SUPPORTED_REAL_ADAPTERS = tuple(sorted(REAL_REGISTRY))


def dispatch(request: RunTaskRequest, *, use_real: bool = False) -> RunTaskResult:
    """Dispatch a run_task request to the named adapter target.

    Args:
        request: The execution request.
        use_real: If ``True``, try to use real CLI adapters (Claude Code,
            Codex CLI) when available.  Defaults to ``False`` (stubs) so
            tests and local development do not incur API costs.
    """
    if use_real:
        adapter = REAL_REGISTRY.get(request.adapter_target)
        if adapter is None:
            return RunTaskResult(
                status="failure",
                error=(
                    f"real adapter unsupported: {request.adapter_target}; "
                    f"supported real adapters: {', '.join(SUPPORTED_REAL_ADAPTERS)}"
                ),
            )
        return adapter.run_task(request)

    adapter = STUB_REGISTRY.get(request.adapter_target)
    if adapter is None:
        return RunTaskResult(
            status="failure",
            error=f"unknown adapter target: {request.adapter_target}",
        )
    return adapter.run_task(request)


def list_adapters(*, include_real: bool = False) -> list[str]:
    if include_real:
        return sorted(set(STUB_REGISTRY) | set(REAL_REGISTRY))
    return sorted(STUB_REGISTRY.keys())
