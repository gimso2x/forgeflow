"""Stale state recovery and timeout backoff for ForgeFlow daemon processes.

Tracks daemon liveness via heartbeats, detects stale processes, and applies
exponential backoff on repeated failures.  Pure stdlib — no external deps.
"""

from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
from math import pow


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class DaemonState(str, Enum):
    RUNNING = "RUNNING"
    STALE = "STALE"
    BACKOFF = "BACKOFF"
    DISABLED = "DISABLED"
    COMPLETED = "COMPLETED"


@dataclass(frozen=True)
class StaleConfig:
    stale_threshold_seconds: int = 7200
    heartbeat_interval_seconds: int = 300
    max_backoff_seconds: int = 3600
    backoff_multiplier: float = 2.0


@dataclass(frozen=True)
class DaemonStatus:
    pid: int | None
    state: DaemonState
    last_heartbeat: str | None
    last_update: str | None
    disabled_until: str | None
    backoff_count: int
    error_message: str | None


# ---------------------------------------------------------------------------
# Process helpers
# ---------------------------------------------------------------------------

def is_pid_alive(pid: int) -> bool:
    """Return *True* if a process with *pid* exists on this host."""
    if pid <= 0:
        return False
    if os.name == "nt":
        # On Windows, os.kill(pid, 0) is not a liveness probe and can deliver
        # a console control event. Use OpenProcess instead.
        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, OSError):
        return False


# ---------------------------------------------------------------------------
# Staleness detection
# ---------------------------------------------------------------------------

def is_stale(status: DaemonStatus, config: StaleConfig) -> bool:
    """Return *True* when the daemon is RUNNING but has not heartbeated
    within *stale_threshold_seconds*."""
    if status.state != DaemonState.RUNNING:
        return False
    if status.last_heartbeat is None:
        return True
    last = datetime.fromisoformat(status.last_heartbeat)
    threshold = timedelta(seconds=config.stale_threshold_seconds)
    return datetime.now() - last > threshold


def mark_stale(status: DaemonStatus) -> DaemonStatus:
    """Transition RUNNING → STALE if the daemon appears stale."""
    if status.state != DaemonState.RUNNING:
        return status
    # Use default config for the check — callers wanting a custom threshold
    # should call :func:`is_stale` directly.
    if status.last_heartbeat is None:
        return replace(status, state=DaemonState.STALE)
    last = datetime.fromisoformat(status.last_heartbeat)
    if datetime.now() - last > timedelta(seconds=StaleConfig().stale_threshold_seconds):
        return replace(status, state=DaemonState.STALE)
    return status


# ---------------------------------------------------------------------------
# Exponential backoff
# ---------------------------------------------------------------------------

def _compute_backoff_seconds(count: int, config: StaleConfig) -> int:
    """Exponential backoff: multiplier^count, capped at *max_backoff_seconds*."""
    raw = pow(config.backoff_multiplier, count)
    return min(int(raw), config.max_backoff_seconds)


def apply_backoff(
    status: DaemonStatus,
    config: StaleConfig,
    error: str | None = None,
) -> DaemonStatus:
    """Enter BACKOFF state with exponential *disabled_until*."""
    wait = _compute_backoff_seconds(status.backoff_count, config)
    disabled_until = (datetime.now() + timedelta(seconds=wait)).isoformat()
    return replace(
        status,
        state=DaemonState.BACKOFF,
        disabled_until=disabled_until,
        backoff_count=status.backoff_count + 1,
        error_message=error,
    )


def reset_backoff(status: DaemonStatus) -> DaemonStatus:
    """Clear all backoff state and return to RUNNING."""
    return replace(
        status,
        state=DaemonState.RUNNING,
        backoff_count=0,
        disabled_until=None,
        error_message=None,
    )


def is_backoff_expired(status: DaemonStatus) -> bool:
    """Return *True* when BACKOFF period has elapsed."""
    if status.state != DaemonState.BACKOFF or status.disabled_until is None:
        return False
    return datetime.now() > datetime.fromisoformat(status.disabled_until)


# ---------------------------------------------------------------------------
# Human-readable reporting
# ---------------------------------------------------------------------------

def format_status_report(status: DaemonStatus) -> str:
    """Return a concise, human-readable status line."""
    pid_str = str(status.pid) if status.pid is not None else "N/A"
    lines = [
        f"Daemon PID: {pid_str}",
        f"State: {status.state.value}",
    ]
    if status.last_heartbeat:
        lines.append(f"Last heartbeat: {status.last_heartbeat}")
    if status.last_update:
        lines.append(f"Last update: {status.last_update}")
    if status.disabled_until:
        lines.append(f"Disabled until: {status.disabled_until}")
    if status.backoff_count:
        lines.append(f"Backoff count: {status.backoff_count}")
    if status.error_message:
        lines.append(f"Error: {status.error_message}")
    return "\n".join(lines)
