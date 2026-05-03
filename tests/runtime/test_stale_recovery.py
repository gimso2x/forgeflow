"""Tests for forgeflow_runtime.stale_recovery — daemon stale detection & backoff."""

from __future__ import annotations

import os
import dataclasses
from datetime import datetime, timedelta

import pytest

from forgeflow_runtime.stale_recovery import (
    DaemonState,
    DaemonStatus,
    StaleConfig,
    apply_backoff,
    format_status_report,
    is_backoff_expired,
    is_pid_alive,
    is_stale,
    mark_stale,
    reset_backoff,
)


# -- Helpers ----------------------------------------------------------------

def _running_status(
    *,
    pid: int = 1234,
    heartbeat_age: timedelta | None = None,
    backoff_count: int = 0,
) -> DaemonStatus:
    """Build a RUNNING DaemonStatus with an optional stale heartbeat."""
    last_heartbeat: str | None = None
    if heartbeat_age is not None:
        last_heartbeat = (datetime.now() - heartbeat_age).isoformat()
    return DaemonStatus(
        pid=pid,
        state=DaemonState.RUNNING,
        last_heartbeat=last_heartbeat,
        last_update=datetime.now().isoformat(),
        disabled_until=None,
        backoff_count=backoff_count,
        error_message=None,
    )


# -- is_pid_alive -----------------------------------------------------------

class TestIsPidAlive:
    def test_current_process_is_alive(self) -> None:
        assert is_pid_alive(os.getpid()) is True

    def test_fake_pid_is_dead(self) -> None:
        assert is_pid_alive(999999) is False


# -- is_stale ---------------------------------------------------------------

class TestIsStale:
    def test_old_heartbeat_is_stale(self) -> None:
        status = _running_status(heartbeat_age=timedelta(hours=3))
        config = StaleConfig()
        assert is_stale(status, config) is True

    def test_recent_heartbeat_not_stale(self) -> None:
        status = _running_status(heartbeat_age=timedelta(seconds=10))
        config = StaleConfig()
        assert is_stale(status, config) is False

    def test_none_heartbeat_is_stale(self) -> None:
        status = _running_status()
        assert is_stale(status, StaleConfig()) is True


# -- mark_stale -------------------------------------------------------------

class TestMarkStale:
    def test_running_and_stale_transitions(self) -> None:
        status = _running_status(heartbeat_age=timedelta(hours=3))
        result = mark_stale(status)
        assert result is not status
        assert result.state == DaemonState.STALE

    def test_running_not_stale_unchanged(self) -> None:
        status = _running_status(heartbeat_age=timedelta(seconds=10))
        result = mark_stale(status)
        assert result is status
        assert result.state == DaemonState.RUNNING

    def test_non_running_unchanged(self) -> None:
        status = DaemonStatus(
            pid=1,
            state=DaemonState.COMPLETED,
            last_heartbeat=None,
            last_update=None,
            disabled_until=None,
            backoff_count=0,
            error_message=None,
        )
        assert mark_stale(status).state == DaemonState.COMPLETED


# -- apply_backoff ----------------------------------------------------------

class TestApplyBackoff:
    def test_exponential_backoff(self) -> None:
        config = StaleConfig(backoff_multiplier=2.0, max_backoff_seconds=3600)
        status = _running_status(backoff_count=0)
        result = apply_backoff(status, config, error="timeout")
        assert result.state == DaemonState.BACKOFF
        assert result.backoff_count == 1
        assert result.error_message == "timeout"
        # 2^0 = 1 second disabled_until should be ~1s from now
        disabled = datetime.fromisoformat(result.disabled_until)
        assert disabled > datetime.now() + timedelta(seconds=0.5)
        assert disabled < datetime.now() + timedelta(seconds=5)

    def test_caps_at_max_backoff(self) -> None:
        config = StaleConfig(backoff_multiplier=1000.0, max_backoff_seconds=3600)
        status = _running_status(backoff_count=5)
        result = apply_backoff(status, config)
        disabled = datetime.fromisoformat(result.disabled_until)
        # Should be capped at 3600s from now, not 1000^5
        assert disabled < datetime.now() + timedelta(seconds=3700)
        assert disabled > datetime.now() + timedelta(seconds=3500)

    def test_increments_backoff_count(self) -> None:
        config = StaleConfig()
        status = _running_status(backoff_count=3)
        result = apply_backoff(status, config)
        assert result.backoff_count == 4


# -- reset_backoff ----------------------------------------------------------

class TestResetBackoff:
    def test_clears_all_backoff_state(self) -> None:
        config = StaleConfig()
        status = _running_status(backoff_count=5)
        status = apply_backoff(status, config, error="boom")
        assert status.state == DaemonState.BACKOFF

        result = reset_backoff(status)
        assert result.state == DaemonState.RUNNING
        assert result.backoff_count == 0
        assert result.disabled_until is None
        assert result.error_message is None


# -- is_backoff_expired -----------------------------------------------------

class TestIsBackoffExpired:
    def test_expired_returns_true(self) -> None:
        status = DaemonStatus(
            pid=1,
            state=DaemonState.BACKOFF,
            last_heartbeat=None,
            last_update=None,
            disabled_until=(datetime.now() - timedelta(seconds=10)).isoformat(),
            backoff_count=2,
            error_message=None,
        )
        assert is_backoff_expired(status) is True

    def test_not_expired_returns_false(self) -> None:
        status = DaemonStatus(
            pid=1,
            state=DaemonState.BACKOFF,
            last_heartbeat=None,
            last_update=None,
            disabled_until=(datetime.now() + timedelta(hours=1)).isoformat(),
            backoff_count=2,
            error_message=None,
        )
        assert is_backoff_expired(status) is False


# -- format_status_report ---------------------------------------------------

class TestFormatStatusReport:
    def test_contains_state_and_pid(self) -> None:
        status = DaemonStatus(
            pid=42,
            state=DaemonState.RUNNING,
            last_heartbeat="2025-01-01T00:00:00",
            last_update="2025-01-01T00:01:00",
            disabled_until=None,
            backoff_count=0,
            error_message=None,
        )
        report = format_status_report(status)
        assert "RUNNING" in report
        assert "42" in report

    def test_no_pid_shows_NAA(self) -> None:
        status = DaemonStatus(
            pid=None,
            state=DaemonState.DISABLED,
            last_heartbeat=None,
            last_update=None,
            disabled_until=None,
            backoff_count=0,
            error_message=None,
        )
        report = format_status_report(status)
        assert "N/A" in report
        assert "DISABLED" in report


# -- DaemonStatus frozen immutability ---------------------------------------

class TestDaemonStatusFrozen:
    def test_cannot_assign_field(self) -> None:
        status = _running_status()
        with pytest.raises(dataclasses.FrozenInstanceError):
            status.state = DaemonState.STALE  # type: ignore[misc]
