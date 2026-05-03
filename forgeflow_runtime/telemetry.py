"""Pipeline telemetry JSONL recorder for ForgeFlow.

Thread-safe, append-only JSONL logger with path-traversal prevention
and automatic cleanup of expired telemetry files.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------
class EventType(str, Enum):
    PIPELINE_RUN = "pipeline_run"
    PHASE_RECORD = "phase_record"
    AGENT_RUN = "agent_run"
    GATE_EVAL = "gate_eval"
    COST_SNAPSHOT = "cost_snapshot"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class TelemetryEvent:
    """A single telemetry event persisted to JSONL."""

    timestamp: str  # ISO 8601 UTC
    event_type: str
    pipeline_id: str
    phase: str = ""
    agent: str = ""
    data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_filepath(filepath: Path, parent: Path) -> None:
    """Reject path-traversal attempts.

    The resolved *filepath* must be under *parent*.
    """
    resolved = filepath.resolve()
    base = parent.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValueError(
            f"path traversal detected: {filepath} resolves outside {base}"
        ) from exc


# ---------------------------------------------------------------------------
# TelemetryRecorder
# ---------------------------------------------------------------------------
class TelemetryRecorder:
    """Append-only JSONL telemetry recorder.

    Thread-safe via :mod:`threading.Lock`.  Safe to call :meth:`finalize`
    multiple times (idempotent).
    """

    def __init__(
        self,
        filepath: Path,
        pipeline_id: str,
        *,
        parent: Path | None = None,
    ) -> None:
        if parent is not None:
            _validate_filepath(filepath, parent)
        self._filepath = filepath
        self._pipeline_id = pipeline_id
        self._lock = threading.Lock()
        self._closed = False
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

    # -- core recording -----------------------------------------------------

    def record(
        self,
        event_type: str,
        phase: str = "",
        agent: str = "",
        data: dict[str, Any] | None = None,
    ) -> None:
        """Append one JSONL line to the telemetry file."""
        event = TelemetryEvent(
            timestamp=_utc_now_iso(),
            event_type=event_type,
            pipeline_id=self._pipeline_id,
            phase=phase,
            agent=agent,
            data=data or {},
        )
        line = json.dumps(asdict(event), sort_keys=True, default=str)
        with self._lock:
            if self._closed:
                return
            with self._filepath.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    # -- convenience methods ------------------------------------------------

    def record_agent_run(
        self,
        agent: str,
        phase: str,
        token_usage: dict[str, Any],
        status: str,
        duration_s: float,
    ) -> None:
        self.record(
            event_type=EventType.AGENT_RUN,
            phase=phase,
            agent=agent,
            data={
                "token_usage": token_usage,
                "status": status,
                "duration_s": duration_s,
            },
        )

    def record_gate_eval(
        self,
        gate: str,
        phase: str,
        passed: bool,
        reason: str = "",
    ) -> None:
        self.record(
            event_type=EventType.GATE_EVAL,
            phase=phase,
            data={
                "gate": gate,
                "passed": passed,
                "reason": reason,
            },
        )

    def record_cost_snapshot(
        self,
        total_usd: float,
        task_count: int,
    ) -> None:
        self.record(
            event_type=EventType.COST_SNAPSHOT,
            data={
                "total_usd": total_usd,
                "task_count": task_count,
            },
        )

    # -- lifecycle ----------------------------------------------------------

    def finalize(self) -> None:
        """Idempotent close.  Safe to call multiple times."""
        with self._lock:
            self._closed = True

    def events(self) -> list[TelemetryEvent]:
        """Read back all events from the telemetry file."""
        if not self._filepath.exists():
            return []
        result: list[TelemetryEvent] = []
        with self._lock:
            with self._filepath.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                        result.append(
                            TelemetryEvent(
                                timestamp=raw["timestamp"],
                                event_type=raw["event_type"],
                                pipeline_id=raw["pipeline_id"],
                                phase=raw.get("phase", ""),
                                agent=raw.get("agent", ""),
                                data=raw.get("data", {}),
                            )
                        )
                    except (json.JSONDecodeError, KeyError):
                        # Skip malformed lines
                        continue
        return result


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
def clean_expired(directory: Path, retention_days: int = 30) -> int:
    """Delete telemetry files older than *retention_days*.

    Args:
        directory: Directory to scan for ``*.jsonl`` telemetry files.
        retention_days: Minimum age (in days) before a file is eligible
            for deletion.

    Returns:
        Number of files deleted.
    """
    if not directory.is_dir():
        return 0
    cutoff = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
    deleted = 0
    for entry in directory.iterdir():
        if entry.is_file() and entry.suffix == ".jsonl":
            try:
                if entry.stat().st_mtime < cutoff:
                    entry.unlink()
                    deleted += 1
            except OSError:
                continue
    return deleted
