#!/usr/bin/env python3
"""Run ForgeFlow eval suites from one documented entry point."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_suite(name: str, command: list[str]) -> int:
    print(f"EVAL SUITE: {name}", flush=True)
    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        print(f"EVAL SUITE: {name} FAIL exit_code={completed.returncode}", flush=True)
        return completed.returncode
    print(f"EVAL SUITE: {name} PASS", flush=True)
    return 0


def main() -> int:
    suites = [("adherence", [sys.executable, "scripts/run_adherence_evals.py"])]
    failures = []
    for name, command in suites:
        code = _run_suite(name, command)
        if code != 0:
            failures.append((name, code))

    if failures:
        print("FORGEFLOW EVALS: FAIL")
        for name, code in failures:
            print(f"- {name}: exit_code={code}")
        return 1

    print("FORGEFLOW EVALS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
