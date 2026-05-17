#!/usr/bin/env python3
"""Run a disposable ForgeFlow first-use demo.

Creates a temporary workspace, initializes a tiny low-risk task, prints the
status JSON, and deletes the workspace on exit so first-run demos never dirty the
checkout.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "scripts" / "run_orchestrator.py"


def _run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ORCHESTRATOR), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="forgeflow-demo-") as tmp:
        workspace = Path(tmp)
        task_id = "demo-readme"
        task_dir = Path(".forgeflow") / "tasks" / task_id

        print("ForgeFlow disposable demo")
        print(f"workspace: {workspace}")
        print()
        print("$ forgeflow init demo task")
        _run(
            [
                "init",
                "--task-id",
                task_id,
                "--objective",
                "Update README quickstart",
                "--risk",
                "low",
            ],
            cwd=workspace,
        )

        print("$ forgeflow status")
        status = _run(["status", "--task-dir", str(task_dir)], cwd=workspace)
        print(status.stdout.strip())
        print()
        print("Generated demo artifacts:")
        for name in ["brief.json", "run-state.json", "checkpoint.json", "session-state.json"]:
            print(f"- {task_dir / name}")
        print()
        print("Next: run /forgeflow:clarify in an agent, or use scripts/run_orchestrator.py for local runtime experiments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
