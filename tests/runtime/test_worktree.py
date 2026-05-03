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
    is_repo_clean,
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
