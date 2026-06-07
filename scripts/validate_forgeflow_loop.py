#!/usr/bin/env python3
"""Smoke tests for scripts/forgeflow_loop.py.

Kept as a stdlib validation script instead of a tests/ package so the v1.x slim
surface guard remains intact.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "forgeflow_loop.py"

LEDGER = """---
schema: ledger/v1
task_id: demo
route: medium
total_items: 2
---

# Ledger

## Execution Tracking

### Task 1: Update docs
- **Plan Step**: docs
- **Status**: done
- **Assignee**: worker
- **Claim Marker**: none
- **Evidence Refs**: evidence_index:task=T1 command=make-validate exit=0
- **Blocker**: none
- **Retry Count**: 0

### Task 2: Add smoke
- **Plan Step**: smoke
- **Status**: pending
- **Assignee**: worker
- **Claim Marker**: none
- **Evidence Refs**:
- **Blocker**: none
- **Retry Count**: 0
"""

CHECKPOINT = """# Checkpoint

## Current Stage
execute

## Status
in_progress

## Active Task
Task 2

## Resume Pointer
ledger.md#task-2-add-smoke status=pending retry=0 owner=worker next_update=implementation-notes.md#Evidence

## Next Action
Run the next smoke item.

## Last Verified Evidence
none
"""


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def assert_ok(proc: subprocess.CompletedProcess[str]) -> str:
    if proc.returncode != 0:
        raise AssertionError(f"expected success, got {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc.stdout


def assert_contains(haystack: str, needle: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"missing {needle!r} in:\n{haystack}")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="forgeflow-loop-smoke-"))
    try:
        task_dir = tmp / ".forgeflow" / "tasks" / "demo"
        task_dir.mkdir(parents=True)
        (task_dir / "ledger.md").write_text(LEDGER, encoding="utf-8")
        (task_dir / "checkpoint.md").write_text(CHECKPOINT, encoding="utf-8")
        (task_dir / "brief.md").write_text("# Brief\nAdd the smoke marker.\n", encoding="utf-8")
        (task_dir / "plan.md").write_text("# Plan\nOne small task.\n", encoding="utf-8")
        (task_dir / "implementation-notes.md").write_text("# Implementation Notes\n", encoding="utf-8")

        out = assert_ok(run("next", "--task-dir", str(task_dir), cwd=ROOT))
        assert_contains(out, "Task 2: Add smoke")
        assert_contains(out, "status=pending")

        out = assert_ok(run("status", "--task-dir", str(task_dir), cwd=ROOT))
        assert_contains(out, "done: 1")
        assert_contains(out, "pending: 1")
        assert_contains(out, "next: Task 2: Add smoke")

        out = assert_ok(
            run(
                "record",
                "--task-dir",
                str(task_dir),
                "--status",
                "done",
                "--evidence",
                "evidence_index:task=T2 command=make-validate-forgeflow-loop exit=0",
                cwd=ROOT,
            )
        )
        assert_contains(out, "recorded: Task 2: Add smoke")
        ledger = (task_dir / "ledger.md").read_text(encoding="utf-8")
        checkpoint = (task_dir / "checkpoint.md").read_text(encoding="utf-8")
        assert_contains(ledger, "- **Status**: done")
        assert_contains(ledger, "evidence_index:task=T2")
        assert_contains(checkpoint, "Task 2: Add smoke status=done")
        assert_contains(checkpoint, "recorded_at=")

        adapter_task_dir = tmp / ".forgeflow" / "tasks" / "adapter"
        shutil.copytree(task_dir, adapter_task_dir)
        (adapter_task_dir / "ledger.md").write_text(LEDGER, encoding="utf-8")
        (adapter_task_dir / "checkpoint.md").write_text(CHECKPOINT, encoding="utf-8")
        out = assert_ok(
            run(
                "run-adapter",
                "--task-dir",
                str(adapter_task_dir),
                "--adapter",
                "stub",
                "--command",
                "python3 -c 'import sys; print(\"adapter saw\", len(sys.stdin.read()))'",
                "--verify-command",
                "python3 -c 'from pathlib import Path; print(Path(\"agent-prompt.md\").exists())'",
                cwd=ROOT,
            )
        )
        assert_contains(out, "recorded: Task 2: Add smoke")
        assert_contains((adapter_task_dir / "implementation-notes.md").read_text(encoding="utf-8"), "Adapter stdout")
        assert_contains((adapter_task_dir / "implementation-notes.md").read_text(encoding="utf-8"), "verification: exit=0")
        assert_contains((adapter_task_dir / "ledger.md").read_text(encoding="utf-8"), "## Agent Runs")
        assert_contains((adapter_task_dir / "ledger.md").read_text(encoding="utf-8"), "verification_exit=0")

        failed_verify_dir = tmp / ".forgeflow" / "tasks" / "failed-verify"
        shutil.copytree(task_dir, failed_verify_dir)
        (failed_verify_dir / "ledger.md").write_text(LEDGER, encoding="utf-8")
        (failed_verify_dir / "checkpoint.md").write_text(CHECKPOINT, encoding="utf-8")
        out = assert_ok(
            run(
                "run-adapter",
                "--task-dir",
                str(failed_verify_dir),
                "--adapter",
                "stub",
                "--command",
                "python3 -c 'print(\"adapter ok\")'",
                "--verify-command",
                "python3 -c 'import sys; print(\"verify failed\"); sys.exit(3)'",
                cwd=ROOT,
            )
        )
        assert_contains(out, "status=blocked")
        assert_contains((failed_verify_dir / "ledger.md").read_text(encoding="utf-8"), "verification command failed")

        blocked_task_dir = tmp / ".forgeflow" / "tasks" / "blocked"
        shutil.copytree(task_dir, blocked_task_dir)
        ledger2 = LEDGER.replace("- **Status**: pending", "- **Status**: in_progress")
        (blocked_task_dir / "ledger.md").write_text(ledger2, encoding="utf-8")
        out = assert_ok(
            run(
                "record",
                "--task-dir",
                str(blocked_task_dir),
                "--status",
                "blocked",
                "--blocker",
                "needs user decision",
                cwd=ROOT,
            )
        )
        assert_contains(out, "status=blocked")
        assert_contains((blocked_task_dir / "ledger.md").read_text(encoding="utf-8"), "needs user decision")

        print("OK: forgeflow-loop CLI reads, selects, and records markdown loop state")
        return 0
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    raise SystemExit(main())
