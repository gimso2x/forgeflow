#!/usr/bin/env python3
"""Resolve ForgeFlow artifact storage locations.

Default storage is global and project-scoped:
    ~/.forgeflow/projects/<project-slug>/...

Set FORGEFLOW_STORAGE_MODE=local to use <repo>/.forgeflow for compatibility.
Set FORGEFLOW_HOME to override the global root. A repo-local
.forgeflow/defaults.md may also contain storage.mode/storage.root bootstrap
settings; environment variables take precedence.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import re


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


def _read_storage_config(project_dir: pathlib.Path) -> dict[str, str]:
    """Read minimal storage bootstrap settings from <repo>/.forgeflow/defaults.md.

    This intentionally avoids a YAML dependency. Supported forms:

        storage.mode: local
        storage.root: ~/.forgeflow

    and:

        storage:
          mode: local
          root: ~/.forgeflow
    """
    path = project_dir / ".forgeflow" / "defaults.md"
    if not path.exists():
        return {}
    config: dict[str, str] = {}
    in_storage = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line == "storage:":
            in_storage = True
            continue
        if ":" not in line:
            in_storage = False
            continue
        key, value = [part.strip().strip("'\"") for part in line.split(":", 1)]
        if not value:
            in_storage = key == "storage"
            continue
        if key.startswith("storage."):
            config[key.removeprefix("storage.")] = value
            in_storage = False
        elif in_storage and key in {"mode", "root"}:
            config[key] = value
        else:
            in_storage = False
    return config


def storage_root(project_dir: pathlib.Path | str = ".") -> pathlib.Path:
    """Return the root that owns tasks/templates/telemetry for a project."""
    project_dir = pathlib.Path(project_dir).resolve()
    config = _read_storage_config(project_dir)
    mode = os.environ.get("FORGEFLOW_STORAGE_MODE", config.get("mode", "global")).lower()
    if mode == "local":
        return project_dir / ".forgeflow"
    if mode != "global":
        raise ValueError("FORGEFLOW_STORAGE_MODE/storage.mode must be 'global' or 'local'")
    home = pathlib.Path(os.environ.get("FORGEFLOW_HOME", config.get("root", "~/.forgeflow"))).expanduser()
    return home / "projects" / project_slug(project_dir)


def tasks_dir(project_dir: pathlib.Path | str = ".") -> pathlib.Path:
    return storage_root(project_dir) / "tasks"


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
