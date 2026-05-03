"""Worktree isolation and patch routing for ForgeFlow."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path


class PatchScope(Enum):
    """Where a patch should be applied."""

    PROJECT = "project"
    CODEX = "codex"
    BOTH = "both"


@dataclass(frozen=True)
class PatchResult:
    """Outcome of a patch application attempt."""

    success: bool
    patch_path: str | None
    scope: PatchScope
    error: str | None
    files_changed: list[str]


@dataclass(frozen=True)
class WorktreeSession:
    """Represents an active git worktree session."""

    worktree_path: str
    branch: str
    base_commit: str
    created_at: str
    active: bool


def _run_git(*args: str, cwd: str | Path) -> subprocess.CompletedProcess[str]:
    """Run a git command in the given directory."""
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def create_worktree(repo_path: str, branch: str) -> WorktreeSession:
    """Create a detached worktree for isolated patch application."""
    repo = Path(repo_path).resolve()

    # Resolve the current HEAD commit
    head = _run_git("rev-parse", "HEAD", cwd=repo)
    if head.returncode != 0:
        raise RuntimeError(f"Cannot resolve HEAD in {repo}: {head.stderr.strip()}")
    base_commit = head.stdout.strip()

    # Create a temporary directory inside the repo's parent
    worktree_path = tempfile.mkdtemp(prefix="ff-worktree-", dir=repo.parent)

    result = _run_git("worktree", "add", "--detach", worktree_path, base_commit, cwd=repo)
    if result.returncode != 0:
        # Clean up the temp directory on failure
        os.rmdir(worktree_path)
        raise RuntimeError(f"Failed to create worktree: {result.stderr.strip()}")

    return WorktreeSession(
        worktree_path=worktree_path,
        branch=branch,
        base_commit=base_commit,
        created_at=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        active=True,
    )


def remove_worktree(repo_path: str, worktree_path: str) -> bool:
    """Remove a worktree, returning success status."""
    result = _run_git("worktree", "remove", worktree_path, cwd=repo_path)
    return result.returncode == 0


def is_repo_clean(repo_path: str) -> bool:
    """Check whether a repo has no uncommitted changes."""
    result = _run_git("status", "--porcelain", cwd=repo_path)
    return result.returncode == 0 and result.stdout.strip() == ""


def apply_patch(worktree_path: str, patch_content: str) -> PatchResult:
    """Apply a patch to a worktree after validation.

    Writes the patch to a temp file, runs ``git apply --check`` first,
    then applies.  Returns a *PatchResult* with the list of changed files.
    """
    patch_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".patch", delete=False, dir=worktree_path
    )
    try:
        patch_file.write(patch_content)
        patch_file.close()

        patch_path = patch_file.name

        # Dry-run check
        check = _run_git("apply", "--check", patch_path, cwd=worktree_path)
        if check.returncode != 0:
            return PatchResult(
                success=False,
                patch_path=patch_path,
                scope=PatchScope.PROJECT,
                error=check.stderr.strip() or check.stdout.strip(),
                files_changed=[],
            )

        # Real apply
        apply_result = _run_git("apply", patch_path, cwd=worktree_path)
        if apply_result.returncode != 0:
            return PatchResult(
                success=False,
                patch_path=patch_path,
                scope=PatchScope.PROJECT,
                error=apply_result.stderr.strip() or apply_result.stdout.strip(),
                files_changed=[],
            )

        # Determine which files changed
        diff = _run_git("diff", "--name-only", cwd=worktree_path)
        files_changed = (
            diff.stdout.strip().splitlines() if diff.returncode == 0 and diff.stdout.strip() else []
        )

        return PatchResult(
            success=True,
            patch_path=patch_path,
            scope=PatchScope.PROJECT,
            error=None,
            files_changed=files_changed,
        )
    except Exception as exc:
        return PatchResult(
            success=False,
            patch_path=None,
            scope=PatchScope.PROJECT,
            error=str(exc),
            files_changed=[],
        )
    finally:
        try:
            os.unlink(patch_file.name)
        except OSError:
            pass


def route_patch(scope: PatchScope, *, project_allowed: bool, codex_allowed: bool) -> list[str]:
    """Determine which targets a patch should be applied to."""
    targets: list[str] = []

    if scope in (PatchScope.PROJECT, PatchScope.BOTH) and project_allowed:
        targets.append("project")
    if scope in (PatchScope.CODEX, PatchScope.BOTH) and codex_allowed:
        targets.append("codex")

    return targets


def acquire_lock(lock_path: str) -> bool:
    """Atomically acquire a filesystem lock. Returns False if already held."""
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        return False


def release_lock(lock_path: str) -> None:
    """Release a previously acquired filesystem lock."""
    try:
        os.unlink(lock_path)
    except FileNotFoundError:
        pass
