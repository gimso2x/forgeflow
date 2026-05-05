#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "examples" / "runtime-fixtures" / "small-doc-task"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the ForgeFlow runtime sample against a disposable copy of a fixture task directory."
    )
    parser.add_argument(
        "--fixture-dir",
        default=str(DEFAULT_FIXTURE),
        help="fixture task directory to copy before running the sample (must be a directory)",
    )
    parser.add_argument("--route", default="small", help="route name to execute")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    fixture_dir = Path(args.fixture_dir).resolve()
    if not fixture_dir.exists():
        print(f"ERROR: fixture directory not found: {fixture_dir}", file=sys.stderr)
        return 1
    if not fixture_dir.is_dir():
        print(f"ERROR: fixture directory is not a directory: {fixture_dir}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="forgeflow-runtime-sample-") as td:
        workspace = Path(td)
        task_dir = workspace / fixture_dir.name
        shutil.copytree(fixture_dir, task_dir)

        command = [
            sys.executable,
            str(ROOT / "scripts" / "run_orchestrator.py"),
            "run",
            "--task-dir",
            str(task_dir),
            "--route",
            args.route,
        ]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
            return result.returncode

        payload = json.loads(result.stdout)
        if fixture_dir.is_relative_to(ROOT):
            payload["sample_source_fixture"] = fixture_dir.relative_to(ROOT).as_posix()
        else:
            payload["sample_source_fixture"] = fixture_dir.as_posix()
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
