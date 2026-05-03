"""Git operations for XLOOP experiment isolation."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitDiff:
    """Diff statistics for experiment changes."""

    files_changed: int
    lines_added: int
    lines_removed: int


class ExperimentGit:
    """Manages experiment branches and change tracking."""

    def __init__(self, repo_root: Path, branch_prefix: str = "xloop") -> None:
        self.repo_root = repo_root
        self.branch_prefix = branch_prefix
        self._original_branch: str | None = None
        self._experiment_branch: str | None = None

    # -- internal helpers ---------------------------------------------------

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run a git command with list args (no shell=True)."""
        return subprocess.run(
            ["git"] + list(args),
            capture_output=True,
            text=True,
            cwd=self.repo_root,
            check=check,
        )

    def _current_branch(self) -> str:
        result = self._git("branch", "--show-current")
        return result.stdout.strip()

    # -- public API ---------------------------------------------------------

    def create_branch(self, experiment_id: str) -> str:
        """Create isolated experiment branch. Returns branch name."""
        self._original_branch = self._current_branch()
        branch_name = f"{self.branch_prefix}/{experiment_id}"
        self._git("checkout", "-b", branch_name)
        self._experiment_branch = branch_name
        return branch_name

    def commit_changes(self, message: str) -> str:
        """Stage all and commit. Returns commit hash."""
        self._git("add", "-A")
        result = self._git("commit", "--allow-empty", "-m", message)
        # Extract short hash from " [abcdef ...]" or just the hash
        output = result.stdout.strip()
        # Typical output: "[xloop/exp-123 abcdef1] message"
        match = output.split("]")[0].split()[-1] if "]" in output else ""
        return match

    def get_diff(self) -> GitDiff:
        """Get diff stats since experiment start."""
        if self._experiment_branch is None:
            return GitDiff(files_changed=0, lines_added=0, lines_removed=0)
        # diff against the merge-base with original branch
        self._git("merge-base", "--is-ancestor", "HEAD", self._original_branch or "HEAD", check=False)
        # Use diff-tree against the first commit or original branch
        ref = self._original_branch or "HEAD"
        result = self._git("diff", "--numstat", ref, "HEAD")
        files_changed = 0
        lines_added = 0
        lines_removed = 0
        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    a = int(parts[0]) if parts[0] != "-" else 0
                    r = int(parts[1]) if parts[1] != "-" else 0
                except ValueError:
                    continue
                lines_added += a
                lines_removed += r
                files_changed += 1
        return GitDiff(
            files_changed=files_changed,
            lines_added=lines_added,
            lines_removed=lines_removed,
        )

    def reset_to_start(self) -> None:
        """Reset to pre-experiment state (discard changes)."""
        if self._experiment_branch is None:
            return
        ref = self._original_branch or "HEAD"
        self._git("reset", "--hard", ref)

    def checkout_original(self) -> None:
        """Return to original branch and cleanup experiment branch."""
        if self._original_branch is None:
            return
        self._git("checkout", self._original_branch)
        if self._experiment_branch is not None:
            self._git("branch", "-D", self._experiment_branch, check=False)
        self._experiment_branch = None

    def is_clean(self) -> bool:
        """Check if working tree is clean."""
        result = self._git("status", "--porcelain")
        return len(result.stdout.strip()) == 0
