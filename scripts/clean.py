#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIR_NAMES = {"__pycache__", ".pytest_cache"}


def main() -> int:
    removed = 0
    for path in ROOT.rglob("*"):
        if path.is_dir() and path.name in DIR_NAMES:
            shutil.rmtree(path)
            removed += 1
    print(f"Removed {removed} cache directories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
