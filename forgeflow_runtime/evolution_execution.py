from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from forgeflow_runtime.evolution_audit import append_audit_event
from forgeflow_runtime.evolution_rules import dry_run_rule, failed_safety_checks

COMMAND_TIMEOUT_SECONDS = 30

AuditAppend = Callable[[Path, dict[str, Any]], None]
CommandRunner = Callable[[str, Path], subprocess.CompletedProcess[str]]


def run_approved_command(command_id: str, root: Path) -> subprocess.CompletedProcess[str]:
    if command_id == "no-env-commit":
        git_check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        if git_check.returncode != 0:
            return git_check
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        if staged.returncode != 0:
            return staged
        bad = [
            path
            for path in staged.stdout.splitlines()
            if path in {".env", ".env.local"} or path.endswith("/.env") or path.endswith("/.env.local")
        ]
        return subprocess.CompletedProcess(
            args=["forgeflow-approved-command", command_id],
            returncode=1 if bad else 0,
            stdout="\n".join(bad) + ("\n" if bad else ""),
            stderr="",
        )
    if command_id == "generated-adapter-drift":
        generate = subprocess.run(
            [sys.executable, "scripts/generate_adapters.py", "--check"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        return subprocess.CompletedProcess(
            args=["forgeflow-approved-command", command_id],
            returncode=generate.returncode,
            stdout=generate.stdout,
            stderr=generate.stderr,
        )
    raise ValueError(f"unapproved evolution command id: {command_id}")


def execute_rule(
    root: Path,
    rule_id: str,
    *,
    audit_append: AuditAppend = append_audit_event,
    command_runner: CommandRunner = run_approved_command,
) -> dict[str, Any]:
    """Execute a safety-validated project-local evolution rule command."""

    root = root.resolve()
    dry_run = dry_run_rule(root, rule_id, allow_examples=False)
    if not dry_run["safe_to_execute_later"]:
        result = {
            **dry_run,
            "executed": False,
            "passed": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "rule failed safety checks; command not executed",
        }
        audit_append(
            root,
            {
                "event": "execute",
                "rule_id": dry_run["rule_id"],
                "source": dry_run["source"],
                "path": dry_run["path"],
                "executed": False,
                "passed": False,
                "exit_code": None,
                "expected_exit_code": dry_run["expected_exit_code"],
                "failed_safety_checks": failed_safety_checks(dry_run["safety_checks"]),
            },
        )
        return result

    try:
        completed = command_runner(str(dry_run["command_id"]), root)
    except subprocess.TimeoutExpired as exc:
        result = {
            **dry_run,
            "would_execute": True,
            "executed": True,
            "passed": False,
            "exit_code": None,
            "expected_exit_code": dry_run["expected_exit_code"],
            "stdout": exc.stdout or "",
            "stderr": f"evolution rule timed out after {COMMAND_TIMEOUT_SECONDS}s",
        }
        audit_append(
            root,
            {
                "event": "execute",
                "rule_id": dry_run["rule_id"],
                "source": dry_run["source"],
                "path": dry_run["path"],
                "executed": True,
                "passed": False,
                "exit_code": None,
                "expected_exit_code": dry_run["expected_exit_code"],
                "failed_safety_checks": [],
                "timeout": True,
            },
        )
        return result

    expected_exit_code = dry_run["expected_exit_code"]
    result = {
        **dry_run,
        "would_execute": True,
        "executed": True,
        "exit_code": completed.returncode,
        "expected_exit_code": expected_exit_code,
        "passed": completed.returncode == expected_exit_code,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    audit_append(
        root,
        {
            "event": "execute",
            "rule_id": dry_run["rule_id"],
            "source": dry_run["source"],
            "path": dry_run["path"],
            "executed": True,
            "passed": result["passed"],
            "exit_code": result["exit_code"],
            "expected_exit_code": expected_exit_code,
            "failed_safety_checks": [],
        },
    )
    return result
