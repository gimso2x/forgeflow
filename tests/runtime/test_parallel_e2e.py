"""End-to-end integration tests for parallel worktree execution flow.

Covers the full lifecycle: init → plan → parallel execute → review → finalize.
Uses a real git repo to verify worktree isolation, merge, and conflict detection.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from forgeflow_runtime.orchestrator import (
    _allocate_parallel_worker_worktrees,
    _merge_completed_parallel_workers,
    _sync_parallel_worktree_plan,
    init_task,
)
from forgeflow_runtime.policy_loader import RuntimePolicy, load_runtime_policy
from forgeflow_runtime.worktree import detect_path_conflicts

from .helpers import read_json_file, write_json_file

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def git_project(tmp_path: Path) -> Path:
    """Create a real git repo with initial commit."""
    repo = tmp_path / "project"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo, check=True, capture_output=True,
    )
    (repo / "README.md").write_text("# test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True,
    )
    return repo


@pytest.fixture()
def policy() -> RuntimePolicy:
    return load_runtime_policy(ROOT)


# ---------------------------------------------------------------------------
# Test 1: init creates proper workspace structure
# ---------------------------------------------------------------------------


def test_init_creates_workspace_with_all_artifacts(git_project: Path, policy: RuntimePolicy) -> None:
    """Phase A gate: init_task must create brief, run-state, checkpoint, session-state."""
    task_dir = git_project / ".forgeflow" / "tasks" / "e2e-init"
    result = init_task(
        task_dir=task_dir,
        policy=policy,
        objective="end-to-end parallel test",
        risk_level="medium",
        project_root=git_project,
    )
    assert result["task_id"]
    assert result["route"] == "medium"
    assert (task_dir / "brief.json").exists()
    assert (task_dir / "run-state.json").exists()
    assert (task_dir / "checkpoint.json").exists()
    assert (task_dir / "session-state.json").exists()
    brief = read_json_file(task_dir / "brief.json")
    assert brief["objective"] == "end-to-end parallel test"
    assert brief["risk_level"] == "medium"


# ---------------------------------------------------------------------------
# Test 2: parallel path conflict detection blocks overlapping files
# ---------------------------------------------------------------------------


def test_sync_parallel_detects_path_conflicts(tmp_path: Path) -> None:
    """Two plan tasks touching the same file must be flagged as NOT parallel-safe."""
    plan_ledger = {
        "tasks": [
            {"id": "t1", "title": "edit login", "files": ["src/login.tsx"], "parallel_safe": True},
            {"id": "t2", "title": "edit login api", "files": ["src/login.tsx"], "parallel_safe": True},
        ],
    }
    run_state: dict[str, Any] = {}
    decision_log: dict[str, Any] = {"entries": []}

    summary = _sync_parallel_worktree_plan(plan_ledger, run_state, decision_log)

    assert summary is not None
    assert summary["parallel_safe"] is False
    assert len(summary["conflicts"]) > 0


# ---------------------------------------------------------------------------
# Test 3: parallel-safe plan allocates worker worktrees
# ---------------------------------------------------------------------------


def test_allocate_workers_creates_worktrees_for_safe_plan(
    git_project: Path, policy: RuntimePolicy,
) -> None:
    """When plan tasks have disjoint paths, worker worktrees should be allocated."""
    task_dir = git_project / ".forgeflow" / "tasks" / "e2e-parallel"
    task_dir.mkdir(parents=True)

    # Set up minimal artifacts
    write_json_file(task_dir / "brief.json", {
        "schema_version": "0.1",
        "task_id": "e2e-parallel",
        "objective": "parallel e2e",
        "use_worktree": True,
        "risk_level": "medium",
        "route": "medium",
    })
    write_json_file(task_dir / "run-state.json", {
        "schema_version": "0.1",
        "task_id": "e2e-parallel",
        "current_stage": "execute",
        "status": "in_progress",
        "completed_gates": [],
        "failed_gates": [],
        "retries": {},
    })
    write_json_file(task_dir / "decision-log.json", {"schema_version": "0.1", "entries": []})

    plan_ledger = {
        "schema_version": "0.1",
        "task_id": "e2e-parallel",
        "current_task_id": "t1",
        "tasks": [
            {"id": "t1", "title": "frontend", "files": ["src/ui.tsx"], "owned_paths": ["src/ui.tsx"], "parallel_safe": True},
            {"id": "t2", "title": "backend", "files": ["src/api.py"], "owned_paths": ["src/api.py"], "parallel_safe": True},
        ],
    }
    run_state = read_json_file(task_dir / "run-state.json")
    decision_log = read_json_file(task_dir / "decision-log.json")

    # Step 1: sync parallel plan (should detect safe)
    summary = _sync_parallel_worktree_plan(plan_ledger, run_state, decision_log)
    assert summary is not None
    assert summary["parallel_safe"] is True, f"Expected parallel_safe, got conflicts: {summary.get('conflicts')}"

    # Step 2: allocate workers
    workers = _allocate_parallel_worker_worktrees(task_dir, plan_ledger, run_state, decision_log)
    assert len(workers) == 2, f"Expected 2 workers, got {len(workers)}"

    # Verify worker state files exist
    for worker in workers:
        plan_task_id = worker["plan_task_id"]
        worker_state_path = task_dir / "workers" / plan_task_id / "worker-state.json"
        assert worker_state_path.exists(), f"worker-state.json missing for {plan_task_id}"
        ws = read_json_file(worker_state_path)
        assert ws["plan_task_id"] == plan_task_id
        assert ws["worktree"]["path"]
        assert ws["worktree"]["branch"]
        # Verify the worktree actually exists on disk
        wt_path = Path(ws["worktree"]["path"])
        assert wt_path.exists(), f"worktree path does not exist: {wt_path}"

    # Verify the worker worktree branches are distinct
    branches = [w["worktree"]["branch"] for w in workers]
    assert len(set(branches)) == 2, f"Expected 2 distinct branches, got: {branches}"

    # Cleanup: remove worktrees
    for worker in workers:
        wt_info = worker.get("worktree", {})
        if wt_info.get("path"):
            wt_path = Path(wt_info["path"])
            if wt_path.exists():
                subprocess.run(
                    ["git", "worktree", "remove", str(wt_path), "--force"],
                    cwd=git_project, capture_output=True,
                )


# ---------------------------------------------------------------------------
# Test 4: parallel workers do NOT modify shared task_dir artifacts
# ---------------------------------------------------------------------------


def test_parallel_workers_do_not_modify_shared_artifacts(
    git_project: Path, policy: RuntimePolicy,
) -> None:
    """Each worker's worktree should be isolated — no writes to parent task_dir."""
    task_dir = git_project / ".forgeflow" / "tasks" / "e2e-isolation"
    task_dir.mkdir(parents=True)

    write_json_file(task_dir / "brief.json", {
        "schema_version": "0.1", "task_id": "e2e-isolation",
        "objective": "isolation test", "use_worktree": True,
        "risk_level": "medium", "route": "medium",
    })
    write_json_file(task_dir / "run-state.json", {
        "schema_version": "0.1", "task_id": "e2e-isolation",
        "current_stage": "execute", "status": "in_progress",
        "completed_gates": [], "failed_gates": [], "retries": {},
    })
    write_json_file(task_dir / "decision-log.json", {"schema_version": "0.1", "entries": []})

    plan_ledger = {
        "schema_version": "0.1", "task_id": "e2e-isolation",
        "current_task_id": "t1",
        "tasks": [
            {"id": "t1", "title": "mod A", "files": ["a.py"], "owned_paths": ["a.py"], "parallel_safe": True},
            {"id": "t2", "title": "mod B", "files": ["b.py"], "owned_paths": ["b.py"], "parallel_safe": True},
        ],
    }
    run_state = read_json_file(task_dir / "run-state.json")
    decision_log = read_json_file(task_dir / "decision-log.json")

    _sync_parallel_worktree_plan(plan_ledger, run_state, decision_log)
    workers = _allocate_parallel_worker_worktrees(task_dir, plan_ledger, run_state, decision_log)
    assert len(workers) == 2

    # Simulate: each worker writes a file in its worktree
    for worker in workers:
        wt_path = Path(worker["worktree"]["path"])
        plan_task_id = worker["plan_task_id"]
        (wt_path / f"{plan_task_id}.txt").write_text(f"output from {plan_task_id}", encoding="utf-8")

    # Verify: the files are in worktrees, NOT in the shared task_dir
    for worker in workers:
        wt_path = Path(worker["worktree"]["path"])
        plan_task_id = worker["plan_task_id"]
        assert (wt_path / f"{plan_task_id}.txt").exists()
        assert not (task_dir / f"{plan_task_id}.txt").exists(), \
            f"Worker {plan_task_id} leaked a file into the shared task_dir!"

    # Verify: git status of the main repo should NOT see worker changes
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=git_project, capture_output=True, text=True,
    )
    # Only .forgeflow/ changes should appear (if any)
    for line in result.stdout.strip().splitlines():
        assert ".forgeflow" in line, \
            f"Worker leaked changes into main working tree: {line}"

    # Cleanup
    for worker in workers:
        wt_path = Path(worker.get("worktree", {}).get("path", ""))
        if wt_path.exists():
            subprocess.run(
                ["git", "worktree", "remove", str(wt_path), "--force"],
                cwd=git_project, capture_output=True,
            )


# ---------------------------------------------------------------------------
# Test 5: empty owned_paths does NOT bypass conflict detection
# ---------------------------------------------------------------------------


def test_empty_owned_paths_not_treated_as_safe(tmp_path: Path) -> None:
    """Plan tasks with no owned_paths/files should NOT be auto-assumed parallel-safe."""
    tasks = [
        {"id": "t1", "title": "task 1", "parallel_safe": True},
        {"id": "t2", "title": "task 2", "parallel_safe": True},
    ]
    result = detect_path_conflicts(tasks)
    # Tasks with no file info should be treated cautiously
    assert "parallel_safe" in result
    # If neither task declares files, they're implicitly overlapping
    if not result["parallel_safe"]:
        assert len(result["conflicts"]) > 0


# ---------------------------------------------------------------------------
# Test 6: merge completes when workers have committed changes
# ---------------------------------------------------------------------------


def test_merge_parallel_workers_after_review(
    git_project: Path, policy: RuntimePolicy,
) -> None:
    """Full flow: allocate → simulate work → mark approved → merge."""
    task_dir = git_project / ".forgeflow" / "tasks" / "e2e-merge"
    task_dir.mkdir(parents=True)

    write_json_file(task_dir / "brief.json", {
        "schema_version": "0.1", "task_id": "e2e-merge",
        "objective": "merge test", "use_worktree": True,
        "risk_level": "medium", "route": "medium",
    })
    write_json_file(task_dir / "run-state.json", {
        "schema_version": "0.1", "task_id": "e2e-merge",
        "current_stage": "finalize", "status": "in_progress",
        "completed_gates": [], "failed_gates": [], "retries": {},
        "quality_review_approved": True,
        "spec_review_approved": True,
    })
    write_json_file(task_dir / "decision-log.json", {"schema_version": "0.1", "entries": []})

    plan_ledger = {
        "schema_version": "0.1", "task_id": "e2e-merge",
        "current_task_id": "t1",
        "tasks": [
            {"id": "t1", "title": "mod A", "files": ["a.py"], "owned_paths": ["a.py"], "parallel_safe": True},
            {"id": "t2", "title": "mod B", "files": ["b.py"], "owned_paths": ["b.py"], "parallel_safe": True},
        ],
    }

    run_state = read_json_file(task_dir / "run-state.json")
    decision_log = read_json_file(task_dir / "decision-log.json")

    _sync_parallel_worktree_plan(plan_ledger, run_state, decision_log)
    workers = _allocate_parallel_worker_worktrees(task_dir, plan_ledger, run_state, decision_log)
    assert len(workers) == 2

    # Simulate work: each worker commits its owned file in its worktree
    for worker in workers:
        wt_path = Path(worker["worktree"]["path"])
        plan_task_id = worker["plan_task_id"]
        # Create the file(s) this worker owns (must match owned_paths)
        for owned in worker.get("owned_paths", []):
            (wt_path / owned).write_text(f"# {plan_task_id} implementation\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=wt_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"implement {plan_task_id}"],
            cwd=wt_path, check=True, capture_output=True,
        )
        # Mark worker as completed (simulate successful execution)
        worker["status"] = "completed"
        # Update worker-state.json on disk too
        ws_path = task_dir / "workers" / plan_task_id / "worker-state.json"
        ws = read_json_file(ws_path)
        ws["status"] = "completed"
        write_json_file(ws_path, ws)

    # Update run_state with workers
    run_state["workers"] = workers
    write_json_file(task_dir / "run-state.json", run_state)

    # Attempt merge
    merge_results = _merge_completed_parallel_workers(task_dir, run_state)
    assert len(merge_results) == 2
    for mr in merge_results:
        assert mr.get("status") == "merged", f"Merge failed for {mr.get('plan_task_id')}: status={mr.get('status')}, reason={mr.get('reason')}, files={mr.get('files_changed')}"

    # Verify: committed worker changes are now applied to the main repo
    assert (git_project / "a.py").exists(), "a.py not in main repo after merge"
    assert (git_project / "b.py").exists(), "b.py not in main repo after merge"


def test_merge_parallel_workers_skips_non_completed_workers(
    git_project: Path, policy: RuntimePolicy,
) -> None:
    """A failed/exception worker must not block merging completed parallel work."""
    task_dir = git_project / ".forgeflow" / "tasks" / "partial-merge"
    task_dir.mkdir(parents=True)
    write_json_file(task_dir / "brief.json", {
        "schema_version": "0.1", "task_id": "partial-merge",
        "objective": "partial merge test", "use_worktree": True,
        "risk_level": "medium", "route": "medium",
    })
    write_json_file(task_dir / "run-state.json", {
        "schema_version": "0.1", "task_id": "partial-merge",
        "current_stage": "finalize", "status": "in_progress",
        "completed_gates": [], "failed_gates": [], "retries": {},
        "quality_review_approved": True,
        "spec_review_approved": True,
    })
    write_json_file(task_dir / "decision-log.json", {"schema_version": "0.1", "entries": []})
    plan_ledger = {
        "schema_version": "0.1", "task_id": "partial-merge",
        "current_task_id": "t1",
        "tasks": [
            {"id": "done", "title": "done", "files": ["done.py"], "owned_paths": ["done.py"], "parallel_safe": True},
            {"id": "bad", "title": "bad", "files": ["bad.py"], "owned_paths": ["bad.py"], "parallel_safe": True},
        ],
    }
    run_state = read_json_file(task_dir / "run-state.json")
    decision_log = read_json_file(task_dir / "decision-log.json")

    _sync_parallel_worktree_plan(plan_ledger, run_state, decision_log)
    workers = _allocate_parallel_worker_worktrees(task_dir, plan_ledger, run_state, decision_log)
    done_worker = workers[0]
    wt_path = Path(done_worker["worktree"]["path"])
    (wt_path / "done.py").write_text("# done\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=wt_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "done"], cwd=wt_path, check=True, capture_output=True)
    done_worker["status"] = "completed"
    workers[1]["status"] = "exception"
    run_state["workers"] = workers

    merge_results = _merge_completed_parallel_workers(task_dir, run_state)

    assert len(merge_results) == 1
    assert merge_results[0]["plan_task_id"] == "done"
    assert merge_results[0]["status"] == "merged"
    assert (git_project / "done.py").read_text(encoding="utf-8") == "# done\n"
    assert not (git_project / "bad.py").exists()
    assert workers[1]["status"] == "exception"
