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

        step_task_dir = tmp / ".forgeflow" / "tasks" / "step"
        shutil.copytree(task_dir, step_task_dir)
        (step_task_dir / "ledger.md").write_text(LEDGER, encoding="utf-8")
        (step_task_dir / "checkpoint.md").write_text(CHECKPOINT, encoding="utf-8")
        out = assert_ok(
            run(
                "step",
                "--task-dir",
                str(step_task_dir),
                "--verify-command",
                "python3 -c 'from pathlib import Path; assert Path(\"agent-prompt.md\").exists(); print(\"step verified\")'",
                cwd=ROOT,
            )
        )
        assert_contains(out, "step: selected=Task 2: Add smoke")
        assert_contains(out, "step: adapter=stub")
        assert_contains(out, "recorded: Task 2: Add smoke")
        assert_contains((step_task_dir / "ledger.md").read_text(encoding="utf-8"), "adapter=stub")
        assert_contains((step_task_dir / "ledger.md").read_text(encoding="utf-8"), "verification_exit=0")

        fanout_repo = tmp / "fanout-repo"
        fanout_repo.mkdir()
        subprocess.run(["git", "init"], cwd=fanout_repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run(["git", "config", "user.email", "forgeflow@example.invalid"], cwd=fanout_repo, check=True)
        subprocess.run(["git", "config", "user.name", "ForgeFlow Test"], cwd=fanout_repo, check=True)
        (fanout_repo / "README.md").write_text("# Demo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=fanout_repo, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=fanout_repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        fanout_task_dir = fanout_repo / ".forgeflow" / "tasks" / "fanout"
        fanout_task_dir.mkdir(parents=True)
        fanout_ledger = LEDGER.replace("- **Status**: done", "- **Status**: pending", 1).replace(
            "- **Claim Marker**: none", "- **Claim Marker**: docs/a.md", 1
        ).replace("- **Claim Marker**: none", "- **Claim Marker**: docs/b.md", 1)
        (fanout_task_dir / "ledger.md").write_text(fanout_ledger, encoding="utf-8")
        (fanout_task_dir / "checkpoint.md").write_text(CHECKPOINT, encoding="utf-8")
        worker_root = tmp / "workers"
        out = assert_ok(
            run(
                "fanout",
                "--task-dir",
                str(fanout_task_dir),
                "--project-root",
                str(fanout_repo),
                "--worker-root",
                str(worker_root),
                cwd=ROOT,
            )
        )
        assert_contains(out, "fanout: created=2")
        workers = sorted(worker_root.iterdir())
        if len(workers) != 2:
            raise AssertionError(f"expected two workers, got {workers}")
        (workers[0] / "docs").mkdir(exist_ok=True)
        (workers[0] / "docs" / "a.md").write_text("A\n", encoding="utf-8")
        (workers[1] / "docs").mkdir(exist_ok=True)
        (workers[1] / "docs" / "b.md").write_text("B\n", encoding="utf-8")
        out = assert_ok(
            run(
                "fanin",
                "--task-dir",
                str(fanout_task_dir),
                "--project-root",
                str(fanout_repo),
                "--worker-root",
                str(worker_root),
                "--verify-command",
                "python3 -c 'from pathlib import Path; assert Path(\"docs/a.md\").exists(); assert Path(\"docs/b.md\").exists(); print(\"fan-in verified\")'",
                cwd=ROOT,
            )
        )
        assert_contains(out, "fanin: merged=2 failed=0 verification=0")
        assert_contains((fanout_repo / "docs" / "a.md").read_text(encoding="utf-8"), "A")
        assert_contains((fanout_repo / "docs" / "b.md").read_text(encoding="utf-8"), "B")
        assert_contains((fanout_task_dir / "ledger.md").read_text(encoding="utf-8"), "## Worktree Fanout")
        assert_contains((fanout_task_dir / "ledger.md").read_text(encoding="utf-8"), "## Worktree Fanin")

        ship_task_dir = tmp / ".forgeflow" / "tasks" / "ship"
        shutil.copytree(task_dir, ship_task_dir)
        (ship_task_dir / "ledger.md").write_text(LEDGER, encoding="utf-8")
        (ship_task_dir / "checkpoint.md").write_text(CHECKPOINT, encoding="utf-8")
        (fanout_repo / "README.md").write_text("# Demo\n\nship candidate change\n", encoding="utf-8")
        out = assert_ok(
            run(
                "ship-candidate",
                "--task-dir",
                str(ship_task_dir),
                "--project-root",
                str(fanout_repo),
                "--verification-command",
                "make validate",
                "--task",
                "Update docs",
                cwd=ROOT,
            )
        )
        assert_contains(out, "evidence: evidence_index:task=T1")
        assert_contains(out, "approval_status: ship_candidate")
        assert_contains(out, "external_side_effects: blocked_until_human_approval")
        ship_ledger = (ship_task_dir / "ledger.md").read_text(encoding="utf-8")
        assert_contains(ship_ledger, "## Ship Ledger")
        assert_contains(ship_ledger, "status=ship_candidate")
        assert_contains(ship_ledger, "boundary=human_approval_required")
        assert_contains(ship_ledger, "verification_command='make validate'")
        assert_contains(ship_ledger, "README.md")
        assert_contains((ship_task_dir / "checkpoint.md").read_text(encoding="utf-8"), "## Ship Boundary")

        blocked_ship_dir = tmp / ".forgeflow" / "tasks" / "blocked-ship"
        shutil.copytree(task_dir, blocked_ship_dir)
        blocked_for_ship = LEDGER.replace("- **Status**: pending", "- **Status**: blocked")
        (blocked_ship_dir / "ledger.md").write_text(blocked_for_ship, encoding="utf-8")
        bad_ship = run(
            "ship-candidate",
            "--task-dir",
            str(blocked_ship_dir),
            "--verification-command",
            "make validate",
            "--task",
            "Add smoke",
            cwd=ROOT,
        )
        if bad_ship.returncode == 0:
            raise AssertionError("expected blocked task to fail ship-candidate")
        assert_contains(bad_ship.stderr, "only done tasks with evidence")

        unapproved = run(
            "ship-candidate",
            "--task-dir",
            str(ship_task_dir),
            "--verification-command",
            "make validate",
            "--task",
            "Update docs",
            "--approved",
            cwd=ROOT,
        )
        if unapproved.returncode == 0:
            raise AssertionError("expected approved without human ref to fail")
        assert_contains(unapproved.stderr, "--human-approval-ref is required")

        failed_worker_repo = tmp / "failed-worker-repo"
        shutil.copytree(fanout_repo, failed_worker_repo, ignore=shutil.ignore_patterns(".git"))
        subprocess.run(["git", "init"], cwd=failed_worker_repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run(["git", "config", "user.email", "forgeflow@example.invalid"], cwd=failed_worker_repo, check=True)
        subprocess.run(["git", "config", "user.name", "ForgeFlow Test"], cwd=failed_worker_repo, check=True)
        subprocess.run(["git", "add", "."], cwd=failed_worker_repo, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=failed_worker_repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        failed_task_dir = failed_worker_repo / ".forgeflow" / "tasks" / "failed"
        failed_task_dir.mkdir(parents=True, exist_ok=True)
        conflict_ledger = fanout_ledger.replace("docs/b.md", "docs/a.md")
        (failed_task_dir / "ledger.md").write_text(conflict_ledger, encoding="utf-8")
        (failed_task_dir / "checkpoint.md").write_text(CHECKPOINT, encoding="utf-8")
        bad = run("fanout", "--task-dir", str(failed_task_dir), "--project-root", str(failed_worker_repo), "--worker-root", str(tmp / "bad-workers"), cwd=ROOT)
        if bad.returncode == 0:
            raise AssertionError("expected fanout conflict to fail")
        assert_contains(bad.stderr, "conflicting path ownership")

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
        assert_contains(out, "retry_policy: route=medium retry=1/2 exhausted=no")
        assert_contains(out, "status=in_progress")
        failed_verify_ledger = (failed_verify_dir / "ledger.md").read_text(encoding="utf-8")
        assert_contains(failed_verify_ledger, "verification command failed; retry=1/2; route=medium")
        assert_contains(failed_verify_ledger, "- **Retry Count**: 1")

        exhausted_verify_dir = tmp / ".forgeflow" / "tasks" / "exhausted-verify"
        shutil.copytree(task_dir, exhausted_verify_dir)
        exhausted_ledger = LEDGER.replace("- **Retry Count**: 0", "- **Retry Count**: 1")
        (exhausted_verify_dir / "ledger.md").write_text(exhausted_ledger, encoding="utf-8")
        (exhausted_verify_dir / "checkpoint.md").write_text(CHECKPOINT, encoding="utf-8")
        out = assert_ok(
            run(
                "run-adapter",
                "--task-dir",
                str(exhausted_verify_dir),
                "--adapter",
                "stub",
                "--command",
                "python3 -c 'print(\"adapter ok\")'",
                "--verify-command",
                "python3 -c 'import sys; print(\"verify failed\"); sys.exit(3)'",
                cwd=ROOT,
            )
        )
        assert_contains(out, "retry_policy: route=medium retry=2/2 exhausted=yes")
        assert_contains(out, "status=blocked")
        exhausted_ledger_text = (exhausted_verify_dir / "ledger.md").read_text(encoding="utf-8")
        assert_contains(exhausted_ledger_text, "retry_budget_exhausted; promotion_hint=high")
        assert_contains(exhausted_ledger_text, "- **Retry Count**: 2")

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

        queue_root = tmp / "phone-queue"
        out = assert_ok(
            run(
                "queue",
                "--queue-root",
                str(queue_root),
                "--request",
                "이거 고쳐",
                "--task-id",
                "phone-demo",
                cwd=ROOT,
            )
        )
        assert_contains(out, "queued: phone-demo")
        assert_contains(out, "recommended_route: small")
        phone_task_dir = queue_root / "phone-demo"
        assert_contains((phone_task_dir / "brief.md").read_text(encoding="utf-8"), "이거 고쳐")
        assert_contains((phone_task_dir / "ledger.md").read_text(encoding="utf-8"), "recommended_route=small")
        assert_contains((phone_task_dir / "checkpoint.md").read_text(encoding="utf-8"), "run /forgeflow:clarify")

        out = assert_ok(
            run(
                "queue",
                "--queue-root",
                str(queue_root),
                "--request",
                "auth database migration refactor",
                "--task-id",
                "phone-override",
                "--route",
                "medium",
                cwd=ROOT,
            )
        )
        assert_contains(out, "recommended_route: high")
        assert_contains(out, "selected_route: medium")
        assert_contains((queue_root / "phone-override" / "ledger.md").read_text(encoding="utf-8"), "override=yes")

        learning_root = tmp / "learning"
        learning_task_dir = tmp / ".forgeflow" / "tasks" / "learning"
        shutil.copytree(task_dir, learning_task_dir)
        blocked_learning_ledger = LEDGER.replace("- **Status**: pending", "- **Status**: blocked")
        blocked_learning_ledger = blocked_learning_ledger.replace(
            "### Task 2: Add smoke\n- **Plan Step**: smoke\n- **Status**: blocked\n- **Assignee**: worker\n- **Claim Marker**: none\n- **Evidence Refs**:\n- **Blocker**: none\n- **Retry Count**: 0",
            "### Task 2: Add smoke\n- **Plan Step**: smoke\n- **Status**: blocked\n- **Assignee**: worker\n- **Claim Marker**: none\n- **Evidence Refs**:\n- **Blocker**: missing API token\n- **Retry Count**: 0",
        )
        (learning_task_dir / "ledger.md").write_text(blocked_learning_ledger, encoding="utf-8")
        out = assert_ok(
            run(
                "learn",
                "--task-dir",
                str(learning_task_dir),
                "--learning-root",
                str(learning_root),
                cwd=ROOT,
            )
        )
        assert_contains(out, "captured: 2")
        assert_contains(out, "canonical_promotion: human_approval_required")
        learning_state = (learning_root / "learning-candidates.json").read_text(encoding="utf-8")
        assert_contains(learning_state, "missing api token")
        assert_contains(learning_state, "human_approval_required")
        assert_contains((learning_task_dir / "implementation-notes.md").read_text(encoding="utf-8"), "Learning Capture")
        assert_contains((learning_task_dir / "ledger.md").read_text(encoding="utf-8"), "canonical_promotion=human_approval_required")

        out = assert_ok(
            run(
                "learn",
                "--task-dir",
                str(learning_task_dir),
                "--learning-root",
                str(learning_root),
                cwd=ROOT,
            )
        )
        assert_contains(out, "captured: 2")
        warned = run(
            "preflight",
            "--learning-root",
            str(learning_root),
            "--request",
            "fix missing API token before verification",
            cwd=ROOT,
        )
        if warned.returncode != 1:
            raise AssertionError(f"expected preflight warning, got {warned.returncode}\nSTDOUT:\n{warned.stdout}\nSTDERR:\n{warned.stderr}")
        assert_contains(warned.stdout, "preflight_warnings:")
        assert_contains(warned.stdout, "blockers:missing api token")
        assert_contains(warned.stdout, "canonical_promotion: human_approval_required")

        print("OK: forgeflow-loop CLI reads, selects, queues, records, and learns candidate-only loop state")
        return 0
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    raise SystemExit(main())
