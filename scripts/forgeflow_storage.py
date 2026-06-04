#!/usr/bin/env python3
"""Resolve ForgeFlow artifact storage locations.

Storage is always global and project-scoped:
    ~/.forgeflow/projects/<project-slug>/...

Set FORGEFLOW_HOME to override the global root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys


RUN_STATE_SCHEMA = "run-state/v1"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip("-._")
    return slug.lower() or "project"


def project_slug(project_dir: pathlib.Path) -> str:
    """Return basename slug, with a short path hash when requested.

    The default is intentionally human-readable. Set
    FORGEFLOW_PROJECT_SLUG_HASH=always when multiple same-named checkouts share
    one FORGEFLOW_HOME and collision-free paths are required up front.
    """
    resolved = project_dir.resolve()
    base = _slugify(resolved.name)
    if os.environ.get("FORGEFLOW_PROJECT_SLUG_HASH", "").lower() == "always":
        digest = hashlib.sha1(str(resolved).encode("utf-8")).hexdigest()[:7]
        return f"{base}-{digest}"
    return base


def _read_storage_root_override(project_dir: pathlib.Path) -> str | None:
    """Read storage.root override from <repo>/.forgeflow/defaults.md if present."""
    path = project_dir / ".forgeflow" / "defaults.md"
    if not path.exists():
        return None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line.startswith("storage.root:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None


def storage_root(project_dir: pathlib.Path | str = ".") -> pathlib.Path:
    """Return the root that owns tasks/templates/telemetry for a project."""
    project_dir = pathlib.Path(project_dir).resolve()
    config_root = _read_storage_root_override(project_dir)
    home = pathlib.Path(os.environ.get("FORGEFLOW_HOME", config_root or "~/.forgeflow")).expanduser()
    return home / "projects" / project_slug(project_dir)


def tasks_dir(project_dir: pathlib.Path | str = ".") -> pathlib.Path:
    return storage_root(project_dir) / "tasks"


def task_dir(project_dir: pathlib.Path | str = ".", task_id: str = "") -> pathlib.Path:
    if not task_id:
        raise ValueError("task_id is required")
    return tasks_dir(project_dir) / task_id


def telemetry_dir(project_dir: pathlib.Path | str = ".") -> pathlib.Path:
    return storage_root(project_dir) / "telemetry"


def templates_dir(project_dir: pathlib.Path | str = ".") -> pathlib.Path:
    return storage_root(project_dir) / "templates"


def defaults_file(project_dir: pathlib.Path | str = ".") -> pathlib.Path:
    return storage_root(project_dir) / "defaults.md"


def project_draft_file(project_dir: pathlib.Path | str = ".") -> pathlib.Path:
    return storage_root(project_dir) / "project-draft.md"


def worktrees_dir(project_dir: pathlib.Path | str = ".") -> pathlib.Path:
    return storage_root(project_dir) / "worktrees"


def run_state_file(project_dir: pathlib.Path | str = ".", task_id: str = "") -> pathlib.Path:
    return task_dir(project_dir, task_id) / "run-state.json"


def project_metadata(project_dir: pathlib.Path | str = ".", task_id: str | None = None) -> dict[str, str]:
    project_dir = pathlib.Path(project_dir).resolve()
    data = {
        "project_name": project_dir.name,
        "project_slug": project_slug(project_dir),
        "repo_root": str(project_dir),
        "storage_root": str(storage_root(project_dir)),
    }
    if task_id is not None:
        data["task_id"] = task_id
    return data


def run_state(project_dir: pathlib.Path | str = ".", task_id: str = "") -> dict[str, str]:
    if not task_id:
        raise ValueError("task_id is required")
    return {"schema": RUN_STATE_SCHEMA, **project_metadata(project_dir, task_id)}


def write_run_state(
    project_dir: pathlib.Path | str = ".",
    task_id: str = "",
    *,
    overwrite: bool = False,
) -> pathlib.Path:
    """Create <storage-root>/tasks/<task-id>/run-state.json with real values."""
    path = run_state_file(project_dir, task_id)
    if path.exists() and not overwrite:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run_state(project_dir, task_id), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve ForgeFlow storage paths and bootstrap task metadata.")
    parser.add_argument("--project-dir", default=".", help="Project/repo root to resolve from (default: cwd).")
    parser.add_argument("--task-id", help="Task identifier for task-specific commands.")
    parser.add_argument("--write-run-state", action="store_true", help="Create run-state.json for --task-id.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing run-state.json.")
    parser.add_argument(
        "--print",
        choices=("storage-root", "tasks-dir", "task-dir", "run-state-file", "metadata", "run-state"),
        dest="print_target",
        help="Print a resolved path or JSON payload.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    project_dir = pathlib.Path(args.project_dir)

    if args.write_run_state:
        if not args.task_id:
            raise SystemExit("ERROR: --write-run-state requires --task-id")
        print(write_run_state(project_dir, args.task_id, overwrite=args.overwrite))
        return 0

    if args.print_target == "storage-root":
        print(storage_root(project_dir))
    elif args.print_target == "tasks-dir":
        print(tasks_dir(project_dir))
    elif args.print_target == "task-dir":
        if not args.task_id:
            raise SystemExit("ERROR: --print task-dir requires --task-id")
        print(task_dir(project_dir, args.task_id))
    elif args.print_target == "run-state-file":
        if not args.task_id:
            raise SystemExit("ERROR: --print run-state-file requires --task-id")
        print(run_state_file(project_dir, args.task_id))
    elif args.print_target == "metadata":
        print(json.dumps(project_metadata(project_dir, args.task_id), ensure_ascii=False, indent=2))
    elif args.print_target == "run-state":
        if not args.task_id:
            raise SystemExit("ERROR: --print run-state requires --task-id")
        print(json.dumps(run_state(project_dir, args.task_id), ensure_ascii=False, indent=2))
    else:
        _build_parser().print_help(sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
