"""Comprehensive tests for execute_context, progress_tracker, and stuck_detector."""

from __future__ import annotations

from pathlib import Path

import pytest

from forgeflow_runtime.execute_context import build_execute_context, format_execute_prompt
from forgeflow_runtime.progress_tracker import calculate_progress, detect_progress_anomaly
from forgeflow_runtime.stuck_detector import (
    StuckSignal,
    detect_stuck,
    should_escalate,
    format_stuck_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plan_ledger(
    tasks: list[dict] | None = None,
    current_task_id: str | None = None,
) -> dict:
    return {
        "tasks": tasks if tasks is not None else [],
        "current_task_id": current_task_id or "",
    }


def _make_run_state(retries: dict | None = None, **overrides) -> dict:
    base = {
        "schema_version": "0.1",
        "task_id": "T1",
        "current_stage": "execute",
        "status": "in_progress",
        "completed_gates": [],
        "failed_gates": [],
        "retries": retries or {},
        "spec_review_approved": False,
        "quality_review_approved": False,
    }
    base.update(overrides)
    return base


# ===================================================================
# execute_context tests
# ===================================================================

class TestBuildExecuteContext:
    """Tests for build_execute_context(task_dir)."""

    def test_no_plan_ledger_returns_empty_context(self, tmp_path: Path):
        """No plan-ledger.json at all → empty context."""
        ctx = build_execute_context(tmp_path)
        assert ctx["current_task"] is None
        assert ctx["ready_to_work"] is False
        assert ctx["blocked_by"] == []
        assert ctx["files_to_edit"] == []
        assert ctx["gates_needed"] == []
        assert ctx["attempt_count"] == 0

    def test_plan_ledger_no_current_task_id_returns_empty(self, tmp_path: Path, write_json):
        """plan-ledger exists but current_task_id is empty → empty context."""
        ledger = _make_plan_ledger(
            tasks=[{"id": "T1", "title": "Do thing", "depends_on": [],
                     "files": [], "status": "pending", "required_gates": []}],
            current_task_id="",
        )
        write_json(tmp_path / "plan-ledger.json", ledger)

        ctx = build_execute_context(tmp_path)
        assert ctx["current_task"] is None
        assert ctx["ready_to_work"] is False

    def test_current_task_no_depends_on_ready(self, tmp_path: Path, write_json):
        """Current task with no depends_on → ready_to_work=True."""
        ledger = _make_plan_ledger(
            tasks=[
                {"id": "T1", "title": "First task", "depends_on": [],
                 "files": ["main.py"], "status": "in_progress",
                 "required_gates": ["machine"], "attempt_count": 0},
            ],
            current_task_id="T1",
        )
        write_json(tmp_path / "plan-ledger.json", ledger)

        ctx = build_execute_context(tmp_path)
        assert ctx["current_task"] is not None
        assert ctx["ready_to_work"] is True
        assert ctx["blocked_by"] == []
        assert ctx["files_to_edit"] == ["main.py"]
        assert ctx["gates_needed"] == ["machine"]

    def test_depends_on_not_done_blocks(self, tmp_path: Path, write_json):
        """depends_on task is still pending → blocked_by filled, not ready."""
        ledger = _make_plan_ledger(
            tasks=[
                {"id": "T1", "title": "Setup", "depends_on": [],
                 "files": [], "status": "pending",
                 "required_gates": [], "attempt_count": 0},
                {"id": "T2", "title": "Main work", "depends_on": ["T1"],
                 "files": ["core.py"], "status": "pending",
                 "required_gates": ["machine"], "attempt_count": 0},
            ],
            current_task_id="T2",
        )
        write_json(tmp_path / "plan-ledger.json", ledger)

        ctx = build_execute_context(tmp_path)
        assert ctx["ready_to_work"] is False
        assert ctx["blocked_by"] == ["T1"]

    def test_all_depends_on_done_ready(self, tmp_path: Path, write_json):
        """All depends_on tasks are done → ready_to_work=True."""
        ledger = _make_plan_ledger(
            tasks=[
                {"id": "T1", "title": "Setup", "depends_on": [],
                 "files": [], "status": "done",
                 "required_gates": [], "attempt_count": 1},
                {"id": "T2", "title": "Main work", "depends_on": ["T1"],
                 "files": ["core.py"], "status": "pending",
                 "required_gates": ["machine"], "attempt_count": 0},
            ],
            current_task_id="T2",
        )
        write_json(tmp_path / "plan-ledger.json", ledger)

        ctx = build_execute_context(tmp_path)
        assert ctx["ready_to_work"] is True
        assert ctx["blocked_by"] == []


class TestFormatExecutePrompt:
    """Tests for format_execute_prompt(context)."""

    def test_valid_context_contains_title_files_gates(self):
        context = {
            "current_task": {
                "id": "T2",
                "title": "Fix sector_rotation",
                "files": ["backend/reporting.py"],
                "required_gates": ["machine", "validator"],
                "evidence_refs": [],
            },
            "ready_to_work": True,
            "blocked_by": [],
            "files_to_edit": ["backend/reporting.py"],
            "gates_needed": ["machine", "validator"],
            "attempt_count": 3,
            "task_index": "T2/5",
            "progress_summary": "T2/5 — Fix sector_rotation",
        }
        result = format_execute_prompt(context)

        assert "Fix sector_rotation" in result
        assert "backend/reporting.py" in result
        assert "machine" in result
        assert "validator" in result
        assert "ready" in result.lower()

    def test_empty_context_says_no_task(self):
        context = {
            "current_task": None,
            "ready_to_work": False,
            "blocked_by": [],
            "files_to_edit": [],
            "gates_needed": [],
            "attempt_count": 0,
            "task_index": "",
            "progress_summary": "",
        }
        result = format_execute_prompt(context)
        assert "no current task" in result.lower()


# ===================================================================
# progress_tracker tests
# ===================================================================

class TestCalculateProgress:
    """Tests for calculate_progress(plan_ledger)."""

    def test_none_returns_zeroed_defaults(self):
        result = calculate_progress(None)
        assert result["total_tasks"] == 0
        assert result["done"] == 0
        assert result["in_progress"] == 0
        assert result["pending"] == 0
        assert result["blocked"] == 0
        assert result["cancelled"] == 0
        assert result["percent"] == 0.0
        assert result["next_actionable"] == []
        assert result["per_task"] == {}

    def test_five_tasks_correct_counts_and_percent(self):
        ledger = _make_plan_ledger(
            tasks=[
                {"id": "T1", "status": "done", "depends_on": []},
                {"id": "T2", "status": "done", "depends_on": []},
                {"id": "T3", "status": "in_progress", "depends_on": []},
                {"id": "T4", "status": "pending", "depends_on": []},
                {"id": "T5", "status": "pending", "depends_on": []},
            ],
            current_task_id="T3",
        )
        result = calculate_progress(ledger)
        assert result["total_tasks"] == 5
        assert result["done"] == 2
        assert result["in_progress"] == 1
        assert result["pending"] == 2
        assert result["percent"] == 40.0

    def test_next_actionable_pending_with_deps_done(self):
        """Pending task whose depends_on are all done → appears in next_actionable."""
        ledger = _make_plan_ledger(
            tasks=[
                {"id": "T1", "status": "done", "depends_on": []},
                {"id": "T2", "status": "done", "depends_on": []},
                {"id": "T3", "status": "pending", "depends_on": ["T1", "T2"]},
                {"id": "T4", "status": "pending", "depends_on": ["T3"]},
            ],
            current_task_id="T3",
        )
        result = calculate_progress(ledger)
        assert "T3" in result["next_actionable"]
        # T4 depends on T3 which is not done, so T4 is NOT actionable
        assert "T4" not in result["next_actionable"]


class TestDetectProgressAnomaly:
    """Tests for detect_progress_anomaly(plan_ledger, run_state)."""

    def test_attempt_count_gt_3_warning(self):
        ledger = _make_plan_ledger(
            tasks=[
                {"id": "T1", "status": "in_progress", "attempt_count": 4,
                 "depends_on": []},
            ],
        )
        warnings = detect_progress_anomaly(ledger, None)
        assert len(warnings) >= 1
        assert any("attempted 4 times" in w for w in warnings)

    def test_retries_gt_2_warning(self):
        run_state = _make_run_state(retries={"execute": 3})
        warnings = detect_progress_anomaly(None, run_state)
        assert any("execute" in w and "retried 3 times" in w for w in warnings)

    def test_three_plus_in_progress_warning(self):
        ledger = _make_plan_ledger(
            tasks=[
                {"id": "T1", "status": "in_progress", "depends_on": []},
                {"id": "T2", "status": "in_progress", "depends_on": []},
                {"id": "T3", "status": "in_progress", "depends_on": []},
            ],
        )
        warnings = detect_progress_anomaly(ledger, None)
        assert any("3 tasks in progress" in w for w in warnings)

    def test_no_issues_returns_empty(self):
        ledger = _make_plan_ledger(
            tasks=[
                {"id": "T1", "status": "done", "attempt_count": 1,
                 "depends_on": []},
                {"id": "T2", "status": "pending", "attempt_count": 0,
                 "depends_on": []},
            ],
        )
        run_state = _make_run_state(retries={"execute": 0})
        warnings = detect_progress_anomaly(ledger, run_state)
        assert warnings == []


# ===================================================================
# stuck_detector tests
# ===================================================================

class TestDetectStuck:
    """Tests for detect_stuck(task_dir, external_signals)."""

    def test_no_plan_ledger_returns_empty(self, tmp_path: Path):
        """No plan-ledger.json → no signals."""
        signals = detect_stuck(tmp_path)
        assert signals == []

    def test_attempt_count_gte_4_critical(self, tmp_path: Path, write_json):
        ledger = _make_plan_ledger(
            tasks=[
                {"id": "T1", "status": "in_progress", "attempt_count": 4,
                 "depends_on": [], "evidence_refs": []},
            ],
            current_task_id="T1",
        )
        write_json(tmp_path / "plan-ledger.json", ledger)
        write_json(tmp_path / "run-state.json", _make_run_state())

        signals = detect_stuck(tmp_path)
        assert len(signals) >= 1
        crit = [s for s in signals if s.signal_type == "attempt_threshold"]
        assert len(crit) == 1
        assert crit[0].severity == "critical"

    def test_test_regression_50pct_worse_critical(self, tmp_path: Path, write_json):
        """50%+ worse → critical signal."""
        write_json(tmp_path / "plan-ledger.json", _make_plan_ledger())
        write_json(tmp_path / "run-state.json", _make_run_state())

        ext = {"test_failures_before": 10, "test_failures_after": 20}
        signals = detect_stuck(tmp_path, external_signals=ext)
        reg = [s for s in signals if s.signal_type == "test_regression"]
        assert len(reg) == 1
        assert reg[0].severity == "critical"

    def test_test_regression_slight_increase_warning(self, tmp_path: Path, write_json):
        """Slight increase (not 50%+) → warning signal."""
        write_json(tmp_path / "plan-ledger.json", _make_plan_ledger())
        write_json(tmp_path / "run-state.json", _make_run_state())

        ext = {"test_failures_before": 10, "test_failures_after": 12}
        signals = detect_stuck(tmp_path, external_signals=ext)
        reg = [s for s in signals if s.signal_type == "test_regression"]
        assert len(reg) == 1
        assert reg[0].severity == "warning"

    def test_file_edit_loop_5plus_edits_warning(self, tmp_path: Path, write_json):
        """Same file edited 5+ times across tasks → warning."""
        ledger = _make_plan_ledger(
            tasks=[
                {"id": "T1", "status": "done", "depends_on": [],
                 "evidence_refs": ["core.py", "core.py"]},
                {"id": "T2", "status": "done", "depends_on": [],
                 "evidence_refs": ["core.py"]},
                {"id": "T3", "status": "in_progress", "depends_on": [],
                 "evidence_refs": ["core.py", "core.py"]},
            ],
        )
        write_json(tmp_path / "plan-ledger.json", ledger)
        write_json(tmp_path / "run-state.json", _make_run_state())

        signals = detect_stuck(tmp_path)
        loop = [s for s in signals if s.signal_type == "file_edit_loop"]
        assert len(loop) == 1
        assert loop[0].severity == "warning"
        assert "core.py" in loop[0].message

    def test_stage_retry_threshold_gte_4_critical(self, tmp_path: Path, write_json):
        """execute retries >= 4 → critical."""
        write_json(tmp_path / "plan-ledger.json", _make_plan_ledger())
        write_json(tmp_path / "run-state.json", _make_run_state(retries={"execute": 4}))

        signals = detect_stuck(tmp_path)
        srt = [s for s in signals if s.signal_type == "stage_retry_threshold"]
        assert len(srt) == 1
        assert srt[0].severity == "critical"


class TestShouldEscalate:
    """Tests for should_escalate(signals)."""

    def test_critical_returns_true(self):
        signals = [
            StuckSignal("attempt_threshold", "critical", "msg", "action"),
        ]
        assert should_escalate(signals) is True

    def test_only_warnings_returns_false(self):
        signals = [
            StuckSignal("file_edit_loop", "warning", "msg", "action"),
            StuckSignal("test_regression", "warning", "msg2", "action2"),
        ]
        assert should_escalate(signals) is False


class TestFormatStuckReport:
    """Tests for format_stuck_report(signals)."""

    def test_with_signals_non_empty_string(self):
        signals = [
            StuckSignal("attempt_threshold", "critical",
                        "Task T1 attempted 5 times", "Replan"),
        ]
        report = format_stuck_report(signals)
        assert isinstance(report, str)
        assert len(report) > 0
        assert "attempt_threshold" in report
        assert "[CRITICAL]" in report

    def test_empty_returns_no_stuck_signals(self):
        report = format_stuck_report([])
        assert report == "No stuck signals detected."
