#!/usr/bin/env python3
"""Disposable full-loop E2E smoke for scripts/forgeflow_loop.py.

This test builds a temporary git repo, queues a phone-style request, runs one
supervisor step with a credential-free stub adapter, verifies artifact mutation,
records learning candidates, and checks preflight warning behavior. Stdlib only.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "forgeflow_loop.py"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def shell(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=False)


def assert_ok(proc: subprocess.CompletedProcess[str]) -> str:
    if proc.returncode != 0:
        raise AssertionError(f"expected success, got {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc.stdout


def assert_contains(haystack: str, needle: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"missing {needle!r} in:\n{haystack}")


def replace_task(task_dir: Path) -> None:
    ledger = (task_dir / "ledger.md").read_text(encoding="utf-8")
    ledger = ledger.replace("route: small", "route: medium")
    ledger = ledger.replace("total_items: 1", "total_items: 2")
    ledger = ledger.replace(
        "### Task 1: Clarify phone request\n- **Plan Step**: clarify\n- **Status**: pending\n- **Assignee**: owner\n- **Claim Marker**: brief.md\n- **Evidence Refs**: " + next(line.split("Evidence Refs**: ", 1)[1] for line in ledger.splitlines() if "Evidence Refs**:" in line) + "\n- **Blocker**: none\n- **Retry Count**: 0",
        "### Task 1: Write disposable artifact\n- **Plan Step**: implementation\n- **Status**: pending\n- **Assignee**: worker\n- **Claim Marker**: app/result.txt\n- **Evidence Refs**:\n- **Blocker**: none\n- **Retry Count**: 0\n\n### Task 2: Capture blocked learning\n- **Plan Step**: learning\n- **Status**: blocked\n- **Assignee**: worker\n- **Claim Marker**: none\n- **Evidence Refs**:\n- **Blocker**: missing API token\n- **Retry Count**: 0",
    )
    (task_dir / "ledger.md").write_text(ledger, encoding="utf-8")
    checkpoint = (task_dir / "checkpoint.md").read_text(encoding="utf-8")
    checkpoint = checkpoint.replace("Task 1: Clarify phone request", "Task 1: Write disposable artifact")
    checkpoint = checkpoint.replace("run /forgeflow:clarify to refine the draft", "run one stub supervisor step")
    (task_dir / "checkpoint.md").write_text(checkpoint, encoding="utf-8")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="forgeflow-full-loop-e2e-"))
    try:
        repo = tmp / "repo"
        repo.mkdir()
        assert_ok(shell("git init", repo))
        assert_ok(shell("git config user.email forgeflow@example.invalid", repo))
        assert_ok(shell("git config user.name 'ForgeFlow Test'", repo))
        (repo / "README.md").write_text("# Disposable ForgeFlow E2E\n", encoding="utf-8")
        assert_ok(shell("git add README.md && git commit -m init", repo))

        task_root = repo / ".forgeflow" / "tasks"
        out = assert_ok(
            run(
                "queue",
                "--queue-root",
                str(task_root),
                "--request",
                "phone loop: write deterministic artifact and verify",
                "--task-id",
                "full-loop",
                cwd=ROOT,
            )
        )
        assert_contains(out, "queued: full-loop")
        task_dir = task_root / "full-loop"
        replace_task(task_dir)

        out = assert_ok(run("status", "--task-dir", str(task_dir), cwd=ROOT))
        assert_contains(out, "pending: 1")
        assert_contains(out, "blocked: 1")
        assert_contains(out, "next: Task 1: Write disposable artifact")

        command = "python3 -c 'from pathlib import Path; Path(\"app\").mkdir(exist_ok=True); Path(\"app/result.txt\").write_text(\"stub loop artifact\\n\", encoding=\"utf-8\"); print(\"artifact written\")'"
        verify = "python3 -c 'from pathlib import Path; assert Path(\"app/result.txt\").read_text(encoding=\"utf-8\") == \"stub loop artifact\\n\"; print(\"verified artifact\")'"
        out = assert_ok(run("step", "--task-dir", str(task_dir), "--adapter", "stub", "--command", command, "--verify-command", verify, cwd=ROOT))
        assert_contains(out, "step: selected=Task 1: Write disposable artifact")
        assert_contains(out, "recorded: Task 1: Write disposable artifact")
        assert_contains((task_dir / "app" / "result.txt").read_text(encoding="utf-8"), "stub loop artifact")

        ledger = (task_dir / "ledger.md").read_text(encoding="utf-8")
        checkpoint = (task_dir / "checkpoint.md").read_text(encoding="utf-8")
        notes = (task_dir / "implementation-notes.md").read_text(encoding="utf-8")
        assert_contains(ledger, "- **Status**: done")
        assert_contains(ledger, "adapter=stub notes=implementation-notes.md verification_exit=0")
        assert_contains(checkpoint, "Task 1: Write disposable artifact status=done")
        assert_contains(checkpoint, "recorded_at=")
        assert_contains(notes, "Adapter stdout")
        assert_contains(notes, "verification: exit=0")

        learning_root = repo / ".forgeflow" / "learning"
        out = assert_ok(run("learn", "--task-dir", str(task_dir), "--learning-root", str(learning_root), cwd=ROOT))
        assert_contains(out, "canonical_promotion: human_approval_required")
        state = (learning_root / "learning-candidates.json").read_text(encoding="utf-8")
        assert_contains(state, "missing api token")
        assert_contains(state, "candidate_only")

        warned = run("preflight", "--learning-root", str(learning_root), "--request", "fix missing API token before next loop", "--min-count", "1", cwd=ROOT)
        if warned.returncode != 1:
            raise AssertionError(f"expected preflight warning, got {warned.returncode}\nSTDOUT:\n{warned.stdout}\nSTDERR:\n{warned.stderr}")
        assert_contains(warned.stdout, "preflight_warnings:")
        assert_contains(warned.stdout, "canonical_promotion: human_approval_required")

        print("OK: disposable full-loop E2E queues, steps, verifies, records, checkpoints, learns, and preflights without credentials")
        return 0
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    raise SystemExit(main())
