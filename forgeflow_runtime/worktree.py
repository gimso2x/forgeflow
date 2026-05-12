"""Worktree isolation and patch routing for ForgeFlow."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


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


_PROTECTED_COMMON_PATHS = frozenset({
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
})
_PROTECTED_COMMON_PREFIXES = (".claude/", ".github/", ".forgeflow/", "docs/")


def _normalize_owned_paths(plan_task: dict[str, Any]) -> list[str]:
    raw_paths = plan_task.get("owned_paths") or plan_task.get("files") or []
    normalized: list[str] = []
    for raw_path in raw_paths:
        path = str(raw_path).strip().replace("\\", "/")
        while path.startswith("./"):
            path = path[2:]
        if path and path not in normalized:
            normalized.append(path)
    return normalized


def _is_protected_common_path(path: str) -> bool:
    return path in _PROTECTED_COMMON_PATHS or any(path.startswith(prefix) for prefix in _PROTECTED_COMMON_PREFIXES)


def detect_path_conflicts(plan_tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Return worker-level parallelization conflicts for a plan ledger task list.

    ForgeFlow only gets real parallelism when each worker has exclusive file
    ownership. Shared paths and common project docs/config are deliberately
    treated as non-parallel, because merging those blind is how you summon hell.
    """
    by_path: dict[str, list[str]] = {}
    task_order = [str(task.get("id", "")) for task in plan_tasks]
    task_index = {task_id: idx for idx, task_id in enumerate(task_order)}

    for task in plan_tasks:
        task_id = str(task.get("id", ""))
        for path in _normalize_owned_paths(task):
            by_path.setdefault(path, []).append(task_id)

    conflicts: list[dict[str, Any]] = []
    for path, task_ids in by_path.items():
        ordered_task_ids = sorted(task_ids, key=lambda value: task_index.get(value, 10_000))
        if len(ordered_task_ids) > 1:
            conflicts.append({"path": path, "task_ids": ordered_task_ids, "reason": "shared_path"})
        elif _is_protected_common_path(path):
            conflicts.append({"path": path, "task_ids": ordered_task_ids, "reason": "protected_common_path"})

    conflicts.sort(key=lambda item: (item["path"], item["reason"]))
    return {"parallel_safe": not conflicts, "conflicts": conflicts}


def _worker_dir(task_dir: Path, plan_task_id: str) -> Path:
    safe_id = plan_task_id.strip().replace("/", "-").replace("\\", "-")
    if not safe_id:
        raise ValueError("plan task id is required")
    return task_dir / "workers" / safe_id


def create_worker_worktree(
    *,
    task_dir: Path,
    repo_path: str | Path,
    task_id: str,
    plan_task: dict[str, Any],
) -> dict[str, Any]:
    """Create a plan-task-scoped worktree and persist worker artifacts.

    Artifacts are intentionally task-local:
    .forgeflow/tasks/<task-id>/workers/<plan-task-id>/{worker-state,worktree,output}.
    Review/merge can consume them later without guessing where a worker ran.
    """
    plan_task_id = str(plan_task.get("id", "")).strip()
    worker_dir = _worker_dir(task_dir, plan_task_id)
    if worker_dir.exists() and any(worker_dir.iterdir()):
        raise RuntimeError(f"worker artifacts already exist for plan task {plan_task_id}")
    worker_dir.mkdir(parents=True, exist_ok=True)

    branch = f"ff/{task_id}/{plan_task_id}".replace(" ", "-")[:120]
    session = create_worktree(str(repo_path), branch)
    owned_paths = _normalize_owned_paths(plan_task)
    worktree_payload = {
        "path": session.worktree_path,
        "branch": session.branch,
        "base_commit": session.base_commit,
        "created_at": session.created_at,
        "active": session.active,
    }
    worker_state = {
        "schema_version": "0.1",
        "task_id": task_id,
        "plan_task_id": plan_task_id,
        "status": "in_progress",
        "owned_paths": owned_paths,
        "worktree": worktree_payload,
        "output_ref": "output.md",
    }
    (worker_dir / "worktree.json").write_text(json.dumps(worktree_payload, indent=2) + "\n", encoding="utf-8")
    (worker_dir / "worker-state.json").write_text(json.dumps(worker_state, indent=2) + "\n", encoding="utf-8")
    (worker_dir / "output.md").write_text("", encoding="utf-8")
    return worker_state


def _worker_artifact_dir(task_dir: Path, worker: dict[str, Any]) -> Path:
    plan_task_id = str(worker.get("plan_task_id", "")).strip()
    return _worker_dir(task_dir, plan_task_id)


def _git_stdout(*args: str, cwd: str | Path) -> str:
    result = _run_git(*args, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def _write_merge_result(task_dir: Path, worker: dict[str, Any], payload: dict[str, Any]) -> None:
    worker_dir = _worker_artifact_dir(task_dir, worker)
    worker_dir.mkdir(parents=True, exist_ok=True)
    (worker_dir / "merge-result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (worker_dir / "worker-state.json").write_text(json.dumps(worker, indent=2) + "\n", encoding="utf-8")


def _is_repo_clean_ignoring_forgeflow(repo_path: str | Path) -> bool:
    result = _run_git("status", "--porcelain", cwd=repo_path)
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        path = line[3:].strip().replace("\\", "/") if len(line) > 3 else ""
        if path and not path.startswith(".forgeflow/"):
            return False
    return True


def merge_worker_worktree(
    *,
    repo_path: str | Path,
    task_dir: Path,
    worker: dict[str, Any],
    approved: bool,
    require_clean: bool = True,
) -> dict[str, Any]:
    """Apply an approved worker worktree diff back to the project repo.

    This is intentionally conservative: no review approval, non-completed
    worker, unowned file changes, dirty target repo, or apply conflicts all
    block the merge. Blind parallel merging is how a harness becomes a woodchipper.
    """
    repo = Path(repo_path).resolve()
    worktree = worker.get("worktree") if isinstance(worker.get("worktree"), dict) else {}
    worktree_path = Path(str(worktree.get("path", ""))).resolve()
    owned_paths = {str(path).replace("\\", "/") for path in worker.get("owned_paths", [])}

    def blocked(reason: str, *, files_changed: list[str] | None = None, error: str | None = None) -> dict[str, Any]:
        worker["status"] = "merge_blocked"
        payload = {
            "schema_version": "0.1",
            "plan_task_id": worker.get("plan_task_id"),
            "status": "blocked",
            "reason": reason,
            "files_changed": files_changed or [],
            "error": error,
        }
        _write_merge_result(task_dir, worker, payload)
        return payload

    if not approved:
        return blocked("review_not_approved")
    if worker.get("status") != "completed":
        return blocked("worker_not_completed")
    if not worktree_path.exists():
        return blocked("worktree_missing")
    if require_clean and not _is_repo_clean_ignoring_forgeflow(repo):
        return blocked("target_repo_dirty")

    # Compare against base_commit so committed changes are included.
    # A bare `git diff` only shows unstaged working-tree changes, which
    # misses everything the worker already committed.
    base_commit = str(worktree.get("base_commit", "")).strip()
    diff_ref = base_commit if base_commit else "HEAD"

    diff_names = _run_git("diff", "--name-only", diff_ref, cwd=worktree_path)
    if diff_names.returncode != 0:
        return blocked("diff_failed", error=diff_names.stderr.strip() or diff_names.stdout.strip())
    files_changed = [line.strip().replace("\\", "/") for line in diff_names.stdout.splitlines() if line.strip()]
    unowned = [path for path in files_changed if path not in owned_paths]
    if unowned:
        return blocked("unowned_changes", files_changed=files_changed, error=", ".join(unowned))
    if not files_changed:
        worker["status"] = "merged"
        payload = {
            "schema_version": "0.1",
            "plan_task_id": worker.get("plan_task_id"),
            "status": "merged",
            "reason": "no_changes",
            "files_changed": [],
            "error": None,
        }
        _write_merge_result(task_dir, worker, payload)
        return payload

    patch_content = _git_stdout("diff", "--binary", diff_ref, cwd=worktree_path)
    patch_file = tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False, dir=repo)
    try:
        patch_file.write(patch_content)
        patch_file.close()
        check = _run_git("apply", "--check", patch_file.name, cwd=repo)
        if check.returncode != 0:
            return blocked("apply_check_failed", files_changed=files_changed, error=check.stderr.strip() or check.stdout.strip())
        apply_result = _run_git("apply", patch_file.name, cwd=repo)
        if apply_result.returncode != 0:
            return blocked("apply_failed", files_changed=files_changed, error=apply_result.stderr.strip() or apply_result.stdout.strip())
    finally:
        try:
            os.unlink(patch_file.name)
        except OSError:
            pass

    worker["status"] = "merged"
    payload = {
        "schema_version": "0.1",
        "plan_task_id": worker.get("plan_task_id"),
        "status": "merged",
        "reason": "applied",
        "files_changed": files_changed,
        "error": None,
    }
    _write_merge_result(task_dir, worker, payload)
    return payload
