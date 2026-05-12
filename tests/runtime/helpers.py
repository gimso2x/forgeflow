"""Shared test helpers for runtime tests."""
from __future__ import annotations

import json
from pathlib import Path


def write_json_file(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
