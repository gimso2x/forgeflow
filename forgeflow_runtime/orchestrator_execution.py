from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TransitionResult:
    next_stage: str
    execution: dict[str, Any] | None = None


def stub_execution_warning() -> str:
    return "STUB EXECUTION: no real CLI adapter ran; pass --real for live execution or --assert-real to fail fast."


def execution_payload(*, stage: str, role: str, adapter: str, result: Any, use_real: bool = False) -> dict[str, Any]:
    execution_mode = "real" if use_real else "stub"
    payload = {
        "stage": stage,
        "role": role,
        "adapter": adapter,
        "execution_mode": execution_mode,
        "dry_run": execution_mode == "stub",
        "status": result.status,
        "artifacts_produced": result.artifacts_produced,
        "token_usage": result.token_usage,
    }
    if execution_mode == "stub":
        payload["warning"] = stub_execution_warning()
    if result.error:
        payload["error"] = result.error
    return payload
