"""Tests for optional worktree isolation in run_route execute stage."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def git_project(tmp_path: Path) -> Path:
    """Create a minimal git repo with a .forgeflow task structure."""
    repo = tmp_path / "project"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True
    )
    (repo / "README.md").write_text("# test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True
    )
    return repo


@pytest.fixture()
def task_dir(git_project: Path, write_json) -> Path:
    """Create a minimal task directory inside the git project with use_worktree=true."""
    td = git_project / ".forgeflow" / "tasks" / "test-wt-001"
    td.mkdir(parents=True)

    write_json(td / "brief.json", {
        "schema_version": "0.2",
        "objective": "test worktree isolation",
        "risk_level": "low",
        "route": "small",
        "use_worktree": True,
    })
    write_json(td / "run-state.json", {
        "schema_version": "0.2",
        "task_id": "test-wt-001",
        "current_stage": "execute",
        "status": "not_started",
        "completed_gates": [],
        "failed_gates": [],
        "retries": {},
        "spec_review_approved": False,
        "quality_review_approved": False,
    })
    write_json(td / "decision-log.json", {
        "schema_version": "0.2",
        "decisions": [],
    })
    write_json(td / "checkpoint.json", {
        "schema_version": "0.2",
        "route": "small",
        "stages_completed": ["clarify", "plan"],
    })
    write_json(td / "session-state.json", {
        "schema_version": "0.2",
        "route": "small",
    })
    write_json(td / "plan-ledger.json", {
        "schema_version": "0.2",
        "tasks": [{"id": "t1", "title": "do stuff", "status": "pending"}],
    })
    return td


@pytest.fixture()
def task_dir_no_worktree(git_project: Path, write_json) -> Path:
    """Task directory with use_worktree=false."""
    td = git_project / ".forgeflow" / "tasks" / "test-wt-no"
    td.mkdir(parents=True)

    write_json(td / "brief.json", {
        "schema_version": "0.2",
        "objective": "test worktree skip",
        "risk_level": "low",
        "route": "small",
        "use_worktree": False,
    })
    write_json(td / "run-state.json", {
        "schema_version": "0.2",
        "task_id": "test-wt-no",
        "current_stage": "execute",
        "status": "not_started",
        "completed_gates": [],
        "failed_gates": [],
        "retries": {},
        "spec_review_approved": False,
        "quality_review_approved": False,
    })
    return td


@pytest.fixture()
def task_dir_unset(git_project: Path, write_json) -> Path:
    """Task directory with no use_worktree field (user hasn't answered yet)."""
    td = git_project / ".forgeflow" / "tasks" / "test-wt-unset"
    td.mkdir(parents=True)

    write_json(td / "brief.json", {
        "schema_version": "0.2",
        "objective": "test worktree ask",
        "risk_level": "low",
        "route": "small",
    })
    write_json(td / "run-state.json", {
        "schema_version": "0.2",
        "task_id": "test-wt-unset",
        "current_stage": "execute",
        "status": "not_started",
        "completed_gates": [],
        "failed_gates": [],
        "retries": {},
        "spec_review_approved": False,
        "quality_review_approved": False,
    })
    return td


# ---------------------------------------------------------------------------
# Unit tests: _find_git_root
# ---------------------------------------------------------------------------


def test_find_git_root_from_task_dir(git_project: Path):
    from forgeflow_runtime.orchestrator import _find_git_root

    td = git_project / ".forgeflow" / "tasks" / "x"
    td.mkdir(parents=True)
    assert _find_git_root(td) == git_project


def test_find_git_root_returns_none_outside_repo(tmp_path: Path):
    from forgeflow_runtime.orchestrator import _find_git_root

    assert _find_git_root(tmp_path) is None


# ---------------------------------------------------------------------------
# Unit tests: _maybe_create_worktree — use_worktree = true
# ---------------------------------------------------------------------------


def test_maybe_create_worktree_succeeds_when_enabled(task_dir: Path):
    from forgeflow_runtime.orchestrator import _maybe_create_worktree

    run_state = {"task_id": "test-wt-001"}
    decision_log: dict = {"schema_version": "0.2", "entries": []}

    result = _maybe_create_worktree(task_dir, run_state, decision_log)

    assert result is not None
    assert result["active"] is True
    assert Path(result["path"]).exists()
    assert "worktree created" in decision_log["entries"][-1]["decision"]

    # run_state should have worktree info
    assert run_state["worktree"]["active"] is True

    # Clean up the worktree
    repo_root = task_dir.parent.parent.parent
    subprocess.run(
        ["git", "worktree", "remove", result["path"]],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# Unit tests: _maybe_create_worktree — use_worktree = false
# ---------------------------------------------------------------------------


def test_maybe_create_worktree_skipped_when_disabled(task_dir_no_worktree: Path):
    from forgeflow_runtime.orchestrator import _maybe_create_worktree

    run_state = {"task_id": "test-wt-no"}
    decision_log: dict = {"schema_version": "0.2", "entries": []}

    result = _maybe_create_worktree(task_dir_no_worktree, run_state, decision_log)

    assert result is None
    assert decision_log["entries"] == []


# ---------------------------------------------------------------------------
# Unit tests: _maybe_create_worktree — use_worktree not set (ask user)
# ---------------------------------------------------------------------------


def test_maybe_create_worktree_asks_user_when_unset(task_dir_unset: Path):
    from forgeflow_runtime.orchestrator import _maybe_create_worktree

    run_state = {"task_id": "test-wt-unset"}
    decision_log: dict = {"schema_version": "0.2", "entries": []}

    result = _maybe_create_worktree(task_dir_unset, run_state, decision_log)

    assert result is None
    assert any("ask user" in e["decision"] for e in decision_log["entries"])


# ---------------------------------------------------------------------------
# Unit tests: _maybe_create_worktree — outside git repo
# ---------------------------------------------------------------------------


def test_maybe_create_worktree_returns_none_outside_repo(tmp_path: Path, write_json):
    from forgeflow_runtime.orchestrator import _maybe_create_worktree

    td = tmp_path / "not-a-repo" / ".forgeflow" / "tasks" / "t1"
    td.mkdir(parents=True)

    # Need brief.json with use_worktree=true to even attempt creation
    write_json(td / "brief.json", {
        "schema_version": "0.2",
        "objective": "test",
        "risk_level": "low",
        "use_worktree": True,
    })

    result = _maybe_create_worktree(td, {"task_id": "t1"}, {"schema_version": "0.2", "entries": []})
    assert result is None


# ---------------------------------------------------------------------------
# Unit tests: _cleanup_worktree
# ---------------------------------------------------------------------------


def test_cleanup_worktree_removes_active_worktree(task_dir: Path):
    from forgeflow_runtime.orchestrator import (
        _cleanup_worktree,
        _maybe_create_worktree,
    )

    run_state = {"task_id": "test-wt-001"}
    decision_log: dict = {"schema_version": "0.2", "entries": []}

    wt_info = _maybe_create_worktree(task_dir, run_state, decision_log)
    assert wt_info is not None
    wt_path = wt_info["path"]
    assert Path(wt_path).exists()

    # Clean up
    run_state_clean = {"task_id": "test-wt-001", "worktree": wt_info.copy()}
    decision_log_clean: dict = {"schema_version": "0.2", "entries": []}
    _cleanup_worktree(task_dir, wt_info, run_state_clean, decision_log_clean)

    assert run_state_clean["worktree"]["active"] is False
    entries = decision_log_clean["entries"]
    assert any("removed" in e["decision"] or "worktree" in e["decision"] for e in entries)


def test_cleanup_worktree_handles_missing_path(task_dir: Path):
    from forgeflow_runtime.orchestrator import _cleanup_worktree

    wt_info = {"path": "", "branch": "x", "base_commit": "abc", "active": True}
    run_state = {"task_id": "test-wt-001"}
    decision_log: dict = {"schema_version": "0.2", "entries": []}

    # Should not raise; empty path means nothing to remove
    _cleanup_worktree(task_dir, wt_info, run_state, decision_log)
    assert run_state["worktree"]["active"] is False


# ---------------------------------------------------------------------------
# Integration: run-state schema allows worktree field
# ---------------------------------------------------------------------------


def test_run_state_schema_allows_worktree_field():
    from forgeflow_runtime.artifact_validation import validate_artifact_payload

    payload = {
        "schema_version": "0.2",
        "task_id": "test-wt-001",
        "current_stage": "execute",
        "status": "in_progress",
        "completed_gates": [],
        "failed_gates": [],
        "retries": {},
        "spec_review_approved": False,
        "quality_review_approved": False,
        "worktree": {
            "path": "/tmp/ff-worktree-xyz",
            "branch": "ff-exec-test-wt-001",
            "base_commit": "abc123",
            "active": True,
        },
    }
    # Should not raise
    validate_artifact_payload(
        artifact_name="run-state",
        payload=payload,
        source_name="test",
    )


# ---------------------------------------------------------------------------
# Integration: brief schema allows use_worktree field
# ---------------------------------------------------------------------------


def test_brief_schema_allows_use_worktree_field():
    from forgeflow_runtime.artifact_validation import validate_artifact_payload

    payload = {
        "schema_version": "0.2",
        "task_id": "test-wt-001",
        "objective": "test",
        "in_scope": [],
        "out_of_scope": [],
        "constraints": [],
        "acceptance_criteria": [],
        "risk_level": "low",
        "use_worktree": True,
    }
    validate_artifact_payload(
        artifact_name="brief",
        payload=payload,
        source_name="test",
    )


def test_brief_schema_allows_use_worktree_false():
    from forgeflow_runtime.artifact_validation import validate_artifact_payload

    payload = {
        "schema_version": "0.2",
        "task_id": "test-wt-001",
        "objective": "test",
        "in_scope": [],
        "out_of_scope": [],
        "constraints": [],
        "acceptance_criteria": [],
        "risk_level": "low",
        "use_worktree": False,
    }
    validate_artifact_payload(
        artifact_name="brief",
        payload=payload,
        source_name="test",
    )
