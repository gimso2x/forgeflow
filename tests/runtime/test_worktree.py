"""Tests for forgeflow_runtime.worktree — worktree isolation & patch routing."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from forgeflow_runtime.worktree import (
    PatchResult,
    PatchScope,
    WorktreeSession,
    acquire_lock,
    apply_patch,
    create_worktree,
    create_worker_worktree,
    detect_path_conflicts,
    is_repo_clean,
    merge_worker_worktree,
    release_lock,
    remove_worktree,
    route_patch,
)


# ---------------------------------------------------------------------------
# route_patch
# ---------------------------------------------------------------------------


class TestRoutePatch:
    def test_project_scope_allowed(self) -> None:
        assert route_patch(PatchScope.PROJECT, project_allowed=True, codex_allowed=False) == ["project"]

    def test_codex_scope_allowed(self) -> None:
        assert route_patch(PatchScope.CODEX, project_allowed=False, codex_allowed=True) == ["codex"]

    def test_both_scope_allowed(self) -> None:
        result = route_patch(PatchScope.BOTH, project_allowed=True, codex_allowed=True)
        assert sorted(result) == ["codex", "project"]

    def test_project_scope_denied(self) -> None:
        assert route_patch(PatchScope.PROJECT, project_allowed=False, codex_allowed=True) == []

    def test_codex_scope_denied(self) -> None:
        assert route_patch(PatchScope.CODEX, project_allowed=True, codex_allowed=False) == []

    def test_both_scope_partially_denied(self) -> None:
        assert route_patch(PatchScope.BOTH, project_allowed=True, codex_allowed=False) == ["project"]

    def test_both_scope_fully_denied(self) -> None:
        assert route_patch(PatchScope.BOTH, project_allowed=False, codex_allowed=False) == []


# ---------------------------------------------------------------------------
# WorktreeSession frozen dataclass
# ---------------------------------------------------------------------------


class TestWorktreeSession:
    def test_frozen(self) -> None:
        session = WorktreeSession(
            worktree_path="/tmp/wt",
            branch="test-branch",
            base_commit="abc123",
            created_at="2025-01-01T00:00:00Z",
            active=True,
        )
        with pytest.raises(AttributeError):
            session.active = False  # type: ignore[misc]

    def test_equality(self) -> None:
        s1 = WorktreeSession("/a", "b", "c", "d", True)
        s2 = WorktreeSession("/a", "b", "c", "d", True)
        assert s1 == s2


# ---------------------------------------------------------------------------
# is_repo_clean
# ---------------------------------------------------------------------------


class TestIsRepoClean:
    def _init_repo(self, path: Path) -> None:
        subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=path,
            capture_output=True,
            check=True,
        )

    def test_clean_repo(self, tmp_path: Path) -> None:
        self._init_repo(tmp_path)
        # Create a file and commit it
        (tmp_path / "file.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        assert is_repo_clean(str(tmp_path)) is True

    def test_dirty_repo(self, tmp_path: Path) -> None:
        self._init_repo(tmp_path)
        (tmp_path / "file.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        # Modify the file without committing
        (tmp_path / "file.txt").write_text("changed")
        assert is_repo_clean(str(tmp_path)) is False


# ---------------------------------------------------------------------------
# apply_patch
# ---------------------------------------------------------------------------


class TestApplyPatch:
    def _init_repo(self, path: Path) -> None:
        subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=path,
            capture_output=True,
            check=True,
        )
        (path / "target.txt").write_text("line1\nline2\nline3\n")
        subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=path,
            capture_output=True,
            check=True,
        )

    def test_valid_patch(self, tmp_path: Path) -> None:
        self._init_repo(tmp_path)
        patch = (
            "--- a/target.txt\n"
            "+++ b/target.txt\n"
            "@@ -1,3 +1,3 @@\n"
            " line1\n"
            "-line2\n"
            "+line2-modified\n"
            " line3\n"
        )
        result = apply_patch(str(tmp_path), patch)
        assert result.success is True
        assert result.error is None
        assert "target.txt" in result.files_changed

    def test_invalid_patch(self, tmp_path: Path) -> None:
        self._init_repo(tmp_path)
        patch = "--- a/nonexistent.txt\n+++ b/nonexistent.txt\n@@ -1 +1 @@\n-old\n+new\n"
        result = apply_patch(str(tmp_path), patch)
        assert result.success is False
        assert result.error is not None


# ---------------------------------------------------------------------------
# acquire_lock / release_lock
# ---------------------------------------------------------------------------


class TestFileLock:
    def test_acquire_and_release(self, tmp_path: Path) -> None:
        lock_file = str(tmp_path / "test.lock")
        assert acquire_lock(lock_file) is True
        assert os.path.exists(lock_file)
        release_lock(lock_file)
        assert not os.path.exists(lock_file)

    def test_acquire_when_held(self, tmp_path: Path) -> None:
        lock_file = str(tmp_path / "test.lock")
        assert acquire_lock(lock_file) is True
        assert acquire_lock(lock_file) is False
        release_lock(lock_file)

    def test_release_nonexistent(self, tmp_path: Path) -> None:
        # Should not raise
        release_lock(str(tmp_path / "nope.lock"))


# ---------------------------------------------------------------------------
# create_worktree / remove_worktree (integration)
# ---------------------------------------------------------------------------


class TestWorktreeIntegration:
    def _init_repo(self, path: Path) -> None:
        subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=path,
            capture_output=True,
            check=True,
        )
        (path / "README.md").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=path,
            capture_output=True,
            check=True,
        )

    def test_create_and_remove(self, tmp_path: Path) -> None:
        self._init_repo(tmp_path)
        session = create_worktree(str(tmp_path), "feature/test")
        assert session.active is True
        assert os.path.isdir(session.worktree_path)

        ok = remove_worktree(str(tmp_path), session.worktree_path)
        assert ok is True
        assert not os.path.isdir(session.worktree_path)


def test_detect_path_conflicts_blocks_shared_owned_files() -> None:
    from forgeflow_runtime.worktree import detect_path_conflicts

    tasks = [
        {"id": "ui", "files": ["src/login.tsx"], "parallel_safe": True},
        {"id": "api", "owned_paths": ["src/login.tsx"], "parallel_safe": True},
    ]

    result = detect_path_conflicts(tasks)

    assert result["parallel_safe"] is False
    assert result["conflicts"] == [
        {"path": "src/login.tsx", "task_ids": ["ui", "api"], "reason": "shared_path"}
    ]


def test_detect_path_conflicts_blocks_common_docs_and_config() -> None:
    from forgeflow_runtime.worktree import detect_path_conflicts

    tasks = [
        {"id": "docs", "files": ["README.md"], "parallel_safe": True},
        {"id": "code", "files": ["src/app.py"], "parallel_safe": True},
    ]

    result = detect_path_conflicts(tasks)

    assert result["parallel_safe"] is False
    assert result["conflicts"] == [
        {"path": "README.md", "task_ids": ["docs"], "reason": "protected_common_path"}
    ]


def test_create_worker_worktree_records_worker_artifacts(tmp_path: Path) -> None:
    from forgeflow_runtime.worktree import create_worker_worktree

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True, check=True)
    (repo / "README.md").write_text("hello", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True, check=True)

    task_dir = repo / ".forgeflow" / "tasks" / "task-001"
    task_dir.mkdir(parents=True)

    state = create_worker_worktree(
        task_dir=task_dir,
        repo_path=repo,
        task_id="task-001",
        plan_task={"id": "ui", "files": ["src/login.tsx"], "parallel_safe": True},
    )

    worker_dir = task_dir / "workers" / "ui"
    assert (worker_dir / "worker-state.json").exists()
    assert (worker_dir / "worktree.json").exists()
    assert (worker_dir / "output.md").exists()
    assert state["plan_task_id"] == "ui"
    assert state["status"] == "in_progress"
    assert state["owned_paths"] == ["src/login.tsx"]
    assert Path(state["worktree"]["path"]).exists()
    assert state["worktree"]["active"] is True


def test_merge_worker_worktree_applies_owned_changes_after_review(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True, check=True)
    (repo / "src").mkdir()
    (repo / "src" / "login.tsx").write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True, check=True)

    task_dir = repo / ".forgeflow" / "tasks" / "task-001"
    task_dir.mkdir(parents=True)
    worker = create_worker_worktree(
        task_dir=task_dir,
        repo_path=repo,
        task_id="task-001",
        plan_task={"id": "ui", "files": ["src/login.tsx"], "parallel_safe": True},
    )
    worktree_path = Path(worker["worktree"]["path"])
    (worktree_path / "src" / "login.tsx").write_text("new\n", encoding="utf-8")
    worker["status"] = "completed"

    result = merge_worker_worktree(repo_path=repo, task_dir=task_dir, worker=worker, approved=True)

    assert result["status"] == "merged"
    assert result["files_changed"] == ["src/login.tsx"]
    assert (repo / "src" / "login.tsx").read_text(encoding="utf-8") == "new\n"
    assert worker["status"] == "merged"
    assert (task_dir / "workers" / "ui" / "merge-result.json").exists()


def test_merge_worker_worktree_refuses_unowned_changes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True, check=True)
    (repo / "src").mkdir()
    (repo / "src" / "login.tsx").write_text("old\n", encoding="utf-8")
    (repo / "src" / "other.tsx").write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True, check=True)

    task_dir = repo / ".forgeflow" / "tasks" / "task-001"
    task_dir.mkdir(parents=True)
    worker = create_worker_worktree(
        task_dir=task_dir,
        repo_path=repo,
        task_id="task-001",
        plan_task={"id": "ui", "files": ["src/login.tsx"], "parallel_safe": True},
    )
    worktree_path = Path(worker["worktree"]["path"])
    (worktree_path / "src" / "other.tsx").write_text("new\n", encoding="utf-8")
    worker["status"] = "completed"

    result = merge_worker_worktree(repo_path=repo, task_dir=task_dir, worker=worker, approved=True)

    assert result["status"] == "blocked"
    assert result["reason"] == "unowned_changes"
    assert result["files_changed"] == ["src/other.tsx"]
    assert (repo / "src" / "other.tsx").read_text(encoding="utf-8") == "old\n"
    assert worker["status"] == "merge_blocked"


def test_detect_path_conflicts_blocks_empty_owned_paths() -> None:
    result = detect_path_conflicts([
        {"id": "ui", "files": ["src/login.tsx"]},
        {"id": "unknown", "files": []},
    ])

    assert result["parallel_safe"] is False
    assert result["worker_count"] == 2
    assert result["conflicts"] == [
        {
            "path": "<undeclared>",
            "task_ids": ["unknown"],
            "reason": "undeclared_scope",
            "blocked_by": ["ui", "unknown"],
        }
    ]


def test_merge_worker_worktree_refuses_missing_base_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True, check=True)
    (repo / "src").mkdir()
    (repo / "src" / "login.tsx").write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True, check=True)

    task_dir = repo / ".forgeflow" / "tasks" / "task-001"
    task_dir.mkdir(parents=True)
    worker = create_worker_worktree(
        task_dir=task_dir,
        repo_path=repo,
        task_id="task-001",
        plan_task={"id": "ui", "files": ["src/login.tsx"], "parallel_safe": True},
    )
    worker["worktree"]["base_commit"] = ""
    worker["status"] = "completed"

    result = merge_worker_worktree(repo_path=repo, task_dir=task_dir, worker=worker, approved=True)

    assert result["status"] == "blocked"
    assert result["reason"] == "base_commit_missing"
    assert worker["status"] == "merge_blocked"
