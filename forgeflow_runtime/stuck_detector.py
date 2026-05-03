"""Stuck detector for ForgeFlow execution loop.

Analyzes plan-ledger, run-state, and optional external signals to detect
when execution is stuck in a loop or regressing.  Produces structured
:class:`StuckSignal` instances that can be formatted into a human-readable
report or used programmatically to decide whether to escalate / replan.

No external dependencies beyond the Python standard library.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class StuckSignal:
    """A single signal indicating execution may be stuck."""

    signal_type: str   # "attempt_threshold" | "test_regression" | "file_edit_loop" | "stage_retry_threshold"
    severity: str      # "warning" | "critical"
    message: str
    suggested_action: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict[str, Any] | None:
    """Load a JSON file, returning *None* if missing or invalid."""
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text)  # type: ignore[no-any-return]
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _count_file_edits(plan_ledger: dict[str, Any]) -> dict[str, int]:
    """Count how many times each file path appears in *evidence_refs* across all tasks.

    Returns a mapping of ``{file_path: count}``.
    """
    counts: dict[str, int] = {}
    tasks = plan_ledger.get("tasks") or []
    for task in tasks:
        refs = task.get("evidence_refs") or []
        for ref in refs:
            if isinstance(ref, str) and ref.strip():
                counts[ref] = counts.get(ref, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Core detection
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {"critical": 0, "warning": 1}


def detect_stuck(
    task_dir: Path,
    external_signals: dict[str, Any] | None = None,
) -> list[StuckSignal]:
    """Detect if execution is stuck.

    Reads ``plan-ledger.json`` and ``run-state.json`` from *task_dir* and
    inspects optional *external_signals* for regressions.

    Signals checked
    ~~~~~~~~~~~~~~~~
    1. **attempt_threshold** -- any task with ``attempt_count >= 4`` → critical.
    2. **test_regression** -- ``external_signals`` provides
       ``test_failures_before`` / ``test_failures_after``.  ≥50 % worse →
       critical; any increase → warning.
    3. **file_edit_loop** -- same file appears in ``evidence_refs`` 5+ times
       across all tasks → warning.
    4. **stage_retry_threshold** -- ``run-state.retries.execute >= 4`` →
       critical; ``>= 2`` → warning.

    Returns a list of :class:`StuckSignal`, sorted by severity (critical
    first).
    """
    signals: list[StuckSignal] = []

    plan_ledger = _load_json(task_dir / "plan-ledger.json")
    run_state = _load_json(task_dir / "run-state.json")

    # 1. attempt_threshold ------------------------------------------------
    if plan_ledger is not None:
        tasks = plan_ledger.get("tasks") or []
        for task in tasks:
            attempt_count = task.get("attempt_count", 0)
            if not isinstance(attempt_count, int):
                continue
            if attempt_count >= 4:
                task_id = task.get("id", "<unknown>")
                signals.append(StuckSignal(
                    signal_type="attempt_threshold",
                    severity="critical",
                    message=f"Task {task_id} attempted {attempt_count} times without success",
                    suggested_action="Consider breaking this task into smaller sub-tasks or changing approach",
                ))

    # 2. test_regression --------------------------------------------------
    ext = external_signals or {}
    before = ext.get("test_failures_before")
    after = ext.get("test_failures_after")
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        if after > before * 1.5:
            signals.append(StuckSignal(
                signal_type="test_regression",
                severity="critical",
                message=f"Test failures increased from {before} to {after}",
                suggested_action="Rollback recent changes and try a more targeted fix",
            ))
        elif after > before:
            signals.append(StuckSignal(
                signal_type="test_regression",
                severity="warning",
                message=f"Test failures increased from {before} to {after}",
                suggested_action="Rollback recent changes and try a more targeted fix",
            ))

    # 3. file_edit_loop ---------------------------------------------------
    if plan_ledger is not None:
        edit_counts = _count_file_edits(plan_ledger)
        for file_path, count in edit_counts.items():
            if count >= 5:
                signals.append(StuckSignal(
                    signal_type="file_edit_loop",
                    severity="warning",
                    message=f"File {file_path} edited {count} times across tasks",
                    suggested_action="This file may need a deeper redesign rather than incremental fixes",
                ))

    # 4. stage_retry_threshold --------------------------------------------
    if run_state is not None:
        retries = run_state.get("retries") or {}
        execute_retries = retries.get("execute", 0)
        if isinstance(execute_retries, (int, float)):
            execute_retries = int(execute_retries)
            if execute_retries >= 4:
                signals.append(StuckSignal(
                    signal_type="stage_retry_threshold",
                    severity="critical",
                    message=f"Execute stage retried {execute_retries} times",
                    suggested_action="The current plan may not be feasible. Consider replanning.",
                ))
            elif execute_retries >= 2:
                signals.append(StuckSignal(
                    signal_type="stage_retry_threshold",
                    severity="warning",
                    message=f"Execute stage retried {execute_retries} times",
                    suggested_action="The current plan may not be feasible. Consider replanning.",
                ))

    # Sort: critical first, then warning
    signals.sort(key=lambda s: _SEVERITY_ORDER.get(s.severity, 99))
    return signals


# ---------------------------------------------------------------------------
# Decision helpers
# ---------------------------------------------------------------------------

def should_escalate(signals: list[StuckSignal]) -> bool:
    """Return *True* if any critical signal exists."""
    return any(s.severity == "critical" for s in signals)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_SEVERITY_BADGE = {"critical": "[CRITICAL]", "warning": "[WARNING]"}


def format_stuck_report(signals: list[StuckSignal]) -> str:
    """Format *signals* into a human-readable report.

    Returns ``"No stuck signals detected."`` when the list is empty.
    """
    if not signals:
        return "No stuck signals detected."

    lines: list[str] = []
    for signal in signals:
        badge = _SEVERITY_BADGE.get(signal.severity, "[???]")
        lines.append(f"{badge} {signal.signal_type}: {signal.message}")
        lines.append(f"  -> {signal.suggested_action}")
    return "\n".join(lines)
