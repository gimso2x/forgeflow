"""Tests for forgeflow_runtime.telemetry — pipeline telemetry JSONL."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from forgeflow_runtime.telemetry import (
    EventType,
    TelemetryEvent,
    TelemetryRecorder,
    clean_expired,
)


# -- Helpers ----------------------------------------------------------------

@pytest.fixture()
def tmp_recorder(tmp_path: Path) -> TelemetryRecorder:
    filepath = tmp_path / "test.jsonl"
    return TelemetryRecorder(filepath, pipeline_id="pipe-001")


# -- Basic record + read back -----------------------------------------------

class TestRecordAndRead:
    def test_record_and_read_back(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record("pipeline_run", data={"status": "started"})
        tmp_recorder.finalize()
        events = tmp_recorder.events()
        assert len(events) == 1
        assert events[0].event_type == "pipeline_run"
        assert events[0].pipeline_id == "pipe-001"
        assert events[0].data["status"] == "started"

    def test_empty_recorder_reads_empty(self, tmp_recorder: TelemetryRecorder) -> None:
        events = tmp_recorder.events()
        assert events == []

    def test_pipeline_id_preserved(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record("phase_record", phase="planning")
        tmp_recorder.record("agent_run", agent="worker", phase="implementation")
        tmp_recorder.finalize()
        for ev in tmp_recorder.events():
            assert ev.pipeline_id == "pipe-001"

    def test_multiple_events(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record("pipeline_run")
        tmp_recorder.record("phase_record", phase="planning")
        tmp_recorder.record("agent_run", agent="worker", phase="coding")
        tmp_recorder.finalize()
        events = tmp_recorder.events()
        assert len(events) == 3
        assert events[0].event_type == "pipeline_run"
        assert events[1].event_type == "phase_record"
        assert events[2].event_type == "agent_run"

    def test_timestamp_is_iso8601(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record("pipeline_run")
        tmp_recorder.finalize()
        events = tmp_recorder.events()
        assert len(events) == 1
        ts = events[0].timestamp
        assert isinstance(ts, str)
        assert "T" in ts or "+" in ts  # ISO 8601 format


# -- Convenience methods ----------------------------------------------------

class TestConvenienceMethods:
    def test_record_agent_run(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record_agent_run(
            agent="claude",
            phase="planning",
            token_usage={"input": 100, "output": 50},
            status="success",
            duration_s=2.5,
        )
        tmp_recorder.finalize()
        events = tmp_recorder.events()
        assert len(events) == 1
        ev = events[0]
        assert ev.event_type == EventType.AGENT_RUN
        assert ev.agent == "claude"
        assert ev.phase == "planning"
        assert ev.data["token_usage"] == {"input": 100, "output": 50}
        assert ev.data["status"] == "success"
        assert ev.data["duration_s"] == 2.5

    def test_record_gate_eval(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record_gate_eval(
            gate="planning_gate",
            phase="planning",
            passed=True,
            reason="All checks passed",
        )
        tmp_recorder.finalize()
        events = tmp_recorder.events()
        assert len(events) == 1
        ev = events[0]
        assert ev.event_type == EventType.GATE_EVAL
        assert ev.data["gate"] == "planning_gate"
        assert ev.data["passed"] is True
        assert ev.data["reason"] == "All checks passed"

    def test_record_gate_eval_failed(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record_gate_eval(
            gate="quality_gate",
            phase="review",
            passed=False,
            reason="Test coverage below threshold",
        )
        tmp_recorder.finalize()
        events = tmp_recorder.events()
        assert events[0].data["passed"] is False

    def test_record_cost_snapshot(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record_cost_snapshot(total_usd=1.25, task_count=5)
        tmp_recorder.finalize()
        events = tmp_recorder.events()
        assert len(events) == 1
        ev = events[0]
        assert ev.event_type == EventType.COST_SNAPSHOT
        assert ev.data["total_usd"] == 1.25
        assert ev.data["task_count"] == 5


# -- Finalize idempotency ---------------------------------------------------

class TestFinalize:
    def test_double_finalize_safe(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record("pipeline_run")
        tmp_recorder.finalize()
        tmp_recorder.finalize()  # Should not raise
        events = tmp_recorder.events()
        assert len(events) == 1

    def test_record_after_finalize_ignored(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record("pipeline_run")
        tmp_recorder.finalize()
        tmp_recorder.record("phase_record", phase="planning")
        events = tmp_recorder.events()
        assert len(events) == 1


# -- Thread safety ----------------------------------------------------------

class TestThreadSafety:
    def test_concurrent_writes(self, tmp_recorder: TelemetryRecorder) -> None:
        n_threads = 10
        writes_per_thread = 50

        barrier = threading.Barrier(n_threads)

        def writer(idx: int) -> None:
            barrier.wait()
            for i in range(writes_per_thread):
                tmp_recorder.record(
                    "agent_run",
                    agent=f"agent-{idx}",
                    phase=f"phase-{i}",
                )

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        tmp_recorder.finalize()
        events = tmp_recorder.events()
        assert len(events) == n_threads * writes_per_thread


# -- Path traversal prevention ----------------------------------------------

class TestPathTraversal:
    def test_traversal_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            TelemetryRecorder(
                tmp_path / ".." / ".." / "etc" / "passwd.jsonl",
                pipeline_id="evil",
                parent=tmp_path,
            )

    def test_absolute_outside_parent(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            TelemetryRecorder(
                Path("/tmp/telemetry_escape.jsonl"),
                pipeline_id="escape",
                parent=tmp_path,
            )

    def test_valid_within_parent(self, tmp_path: Path) -> None:
        # Should not raise — file is within parent
        recorder = TelemetryRecorder(
            tmp_path / "subdir" / "telemetry.jsonl",
            pipeline_id="ok",
            parent=tmp_path,
        )
        recorder.record("pipeline_run")
        recorder.finalize()
        assert (tmp_path / "subdir" / "telemetry.jsonl").exists()


# -- File format ------------------------------------------------------------

class TestFileFormat:
    def test_valid_jsonl(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record("pipeline_run", data={"key": "value"})
        tmp_recorder.finalize()
        lines = tmp_recorder._filepath.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        obj = json.loads(lines[0])
        assert obj["event_type"] == "pipeline_run"
        assert obj["pipeline_id"] == "pipe-001"

    def test_each_event_one_line(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record("pipeline_run")
        tmp_recorder.record("phase_record")
        tmp_recorder.finalize()
        lines = tmp_recorder._filepath.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            json.loads(line)  # Must be valid JSON


# -- clean_expired ----------------------------------------------------------

class TestCleanExpired:
    def test_removes_old_files(self, tmp_path: Path) -> None:
        # Create a telemetry file
        old_file = tmp_path / "old_telemetry.jsonl"
        old_file.write_text('{"test": true}\n', encoding="utf-8")

        # Backdate the file mtime to 60 days ago
        import os
        import time

        old_time = time.time() - (60 * 86400)
        os.utime(old_file, (old_time, old_time))

        # Also create a recent file
        recent_file = tmp_path / "recent_telemetry.jsonl"
        recent_file.write_text('{"test": true}\n', encoding="utf-8")

        deleted = clean_expired(tmp_path, retention_days=30)
        assert deleted == 1
        assert not old_file.exists()
        assert recent_file.exists()

    def test_empty_directory(self, tmp_path: Path) -> None:
        deleted = clean_expired(tmp_path, retention_days=30)
        assert deleted == 0

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        deleted = clean_expired(tmp_path / "nonexistent", retention_days=30)
        assert deleted == 0

    def test_only_keeps_jsonl(self, tmp_path: Path) -> None:
        # Create a .log file (should be ignored)
        log_file = tmp_path / "telemetry.log"
        log_file.write_text("old log\n", encoding="utf-8")

        import os
        import time

        old_time = time.time() - (60 * 86400)
        os.utime(log_file, (old_time, old_time))

        deleted = clean_expired(tmp_path, retention_days=30)
        assert deleted == 0
        assert log_file.exists()


# -- Malformed lines --------------------------------------------------------

class TestMalformedLines:
    def test_skips_malformed_lines(self, tmp_recorder: TelemetryRecorder) -> None:
        tmp_recorder.record("pipeline_run")
        tmp_recorder.finalize()

        # Append a malformed line
        with tmp_recorder._filepath.open("a", encoding="utf-8") as fh:
            fh.write("NOT VALID JSON{{{\n")

        events = tmp_recorder.events()
        assert len(events) == 1
        assert events[0].event_type == "pipeline_run"


# -- EventType enum ---------------------------------------------------------

class TestEventType:
    def test_all_values(self) -> None:
        assert EventType.PIPELINE_RUN == "pipeline_run"
        assert EventType.PHASE_RECORD == "phase_record"
        assert EventType.AGENT_RUN == "agent_run"
        assert EventType.GATE_EVAL == "gate_eval"
        assert EventType.COST_SNAPSHOT == "cost_snapshot"

    def test_is_str_enum(self) -> None:
        assert isinstance(EventType.PIPELINE_RUN, str)
