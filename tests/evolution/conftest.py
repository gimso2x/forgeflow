"""Evolution test fixtures.

Redirects global evolution paths to tmp_path so tests
don't pollute ~/.forgeflow/evolution/.

Uses tmp_path/.forgeflow/evolution/ to match existing test expectations
that create directories under tmp_path/.forgeflow/evolution/rules etc.

Sets FORGEFLOW_EVOLUTION_DIR env var so subprocess CLI tests also use tmp_path.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _global_evolution_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Redirect all global evolution paths to tmp_path during tests."""
    import forgeflow_runtime.evolution.paths as _paths

    _dir = tmp_path / ".forgeflow" / "evolution"

    # Monkeypatch for in-process calls
    monkeypatch.setattr(_paths, "global_evolution_dir", lambda: _dir)
    # Env var for subprocess CLI tests
    monkeypatch.setenv("FORGEFLOW_EVOLUTION_DIR", str(_dir))
