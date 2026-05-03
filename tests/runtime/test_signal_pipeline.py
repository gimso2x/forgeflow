"""Tests for forgeflow_runtime.signal_pipeline — self-improve signal pipeline."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from forgeflow_runtime.signal_pipeline import (
    Signal,
    SignalFilter,
    SignalSource,
    build_signal_sources_config,
    filter_signals,
    format_signal_report,
    generate_signal_id,
    is_duplicate,
    is_on_cooldown,
    should_invoke_worker,
)

TS_NOW = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
TS_OLD = (datetime.now(UTC) - timedelta(hours=1)).isoformat(timespec="seconds").replace("+00:00", "Z")


def _make_signal(
    source: SignalSource = SignalSource.FIX_COMMIT,
    description: str = "test signal",
    severity: str = "medium",
    timestamp: str = TS_NOW,
    sid: str | None = None,
) -> Signal:
    return Signal(
        id=sid or generate_signal_id(source, description),
        source=source,
        description=description,
        severity=severity,
        timestamp=timestamp,
    )


# -- generate_signal_id -------------------------------------------------------


class TestGenerateSignalId:
    def test_deterministic_same_input(self) -> None:
        id1 = generate_signal_id(SignalSource.FIX_COMMIT, "fix null pointer")
        id2 = generate_signal_id(SignalSource.FIX_COMMIT, "fix null pointer")
        assert id1 == id2

    def test_different_input_different_id(self) -> None:
        id1 = generate_signal_id(SignalSource.FIX_COMMIT, "fix null pointer")
        id2 = generate_signal_id(SignalSource.TELEMETRY, "fix null pointer")
        id3 = generate_signal_id(SignalSource.FIX_COMMIT, "fix off-by-one")
        assert id1 != id2
        assert id1 != id3
        assert id2 != id3


# -- is_duplicate -------------------------------------------------------------


class TestIsDuplicate:
    def test_known_id_returns_true(self) -> None:
        sig = _make_signal(sid="abc123")
        assert is_duplicate(sig, {"abc123", "xyz"}) is True

    def test_unknown_id_returns_false(self) -> None:
        sig = _make_signal(sid="abc123")
        assert is_duplicate(sig, {"xyz", "def"}) is False


# -- is_on_cooldown ------------------------------------------------------------


class TestIsOnCooldown:
    def test_recent_signal_on_cooldown(self) -> None:
        now = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        recent = (datetime.now(UTC) - timedelta(seconds=60)).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        sig = _make_signal(source=SignalSource.TELEMETRY, timestamp=now)
        last_times = {"telemetry": recent}
        assert is_on_cooldown(sig, last_times, cooldown=900) is True

    def test_old_signal_not_on_cooldown(self) -> None:
        now = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        old = (datetime.now(UTC) - timedelta(hours=1)).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        sig = _make_signal(source=SignalSource.TELEMETRY, timestamp=now)
        last_times = {"telemetry": old}
        assert is_on_cooldown(sig, last_times, cooldown=900) is False


# -- filter_signals ------------------------------------------------------------


class TestFilterSignals:
    def test_removes_duplicates(self) -> None:
        sig = _make_signal(sid="dup1")
        sigs = [sig, sig]
        filt = SignalFilter(acked_signal_ids={"dup1"})
        assert filter_signals(sigs, filt, {}) == []

    def test_removes_cooldown_violations(self) -> None:
        now = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        recent = (datetime.now(UTC) - timedelta(seconds=30)).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        sig = _make_signal(source=SignalSource.TELEMETRY, timestamp=now, sid="cool1")
        filt = SignalFilter()
        last_times = {"telemetry": recent}
        assert filter_signals([sig], filt, last_times) == []

    def test_respects_per_source_cap(self) -> None:
        sigs = [
            _make_signal(
                source=SignalSource.FIX_COMMIT,
                description=f"sig-{i}",
                sid=f"cap-{i}",
            )
            for i in range(15)
        ]
        filt = SignalFilter(max_signals_per_source=5)
        result = filter_signals(sigs, filt, {})
        assert len(result) == 5

    def test_empty_input_empty_output(self) -> None:
        filt = SignalFilter()
        assert filter_signals([], filt, {}) == []


# -- should_invoke_worker ------------------------------------------------------


class TestShouldInvokeWorker:
    def test_non_empty_returns_true(self) -> None:
        assert should_invoke_worker([_make_signal()]) is True

    def test_empty_returns_false(self) -> None:
        assert should_invoke_worker([]) is False


# -- format_signal_report ------------------------------------------------------


class TestFormatSignalReport:
    def test_contains_source_names(self) -> None:
        sigs = [
            _make_signal(source=SignalSource.FIX_COMMIT, description="a fix"),
            _make_signal(source=SignalSource.TELEMETRY, description="slow query"),
        ]
        report = format_signal_report(sigs)
        assert "fix_commit" in report
        assert "telemetry" in report

    def test_empty_returns_no_signals(self) -> None:
        assert format_signal_report([]) == "No signals."


# -- build_signal_sources_config ----------------------------------------------


class TestBuildSignalSourcesConfig:
    def test_has_five_entries(self) -> None:
        cfg = build_signal_sources_config()
        assert len(cfg) == 5

    def test_all_sources_present(self) -> None:
        cfg = build_signal_sources_config()
        for src in SignalSource:
            assert src.value in cfg
