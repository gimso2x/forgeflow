#!/usr/bin/env python3
"""Run a real, mutating ForgeFlow plugin E2E against a disposable Next.js-shaped project.

This is intentionally separate from ci_plugin_smoke_matrix.py:
- ci_plugin_smoke_matrix.py is deterministic and non-mutating enough for CI.
- real_plugin_e2e.py invokes live Claude/Codex agents and verifies actual file writes.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ci_plugin_smoke_matrix import (  # noqa: E402
    create_disposable_nextjs_project,
    install_codex_baseline,
    run,
)

TASKS = {
    "small": {
        "prompt": "Use ForgeFlow for a SMALL change. Edit README.md and add exactly this line anywhere after the title: ForgeFlow real E2E small marker. Do not change other files.",
        "checks": {"README.md": "ForgeFlow real E2E small marker"},
    },
    "medium": {
        "prompt": "Use ForgeFlow for a MEDIUM change. Implement a tiny local settings surface without installing packages: create src/lib/settings.ts exporting DEFAULT_SETTINGS with theme and density; create src/app/settings/page.tsx rendering Settings, theme, and density; update README.md with a Settings page note. Keep it static TypeScript/TSX only.",
        "checks": {
            "src/lib/settings.ts": "DEFAULT_SETTINGS",
            "src/app/settings/page.tsx": "Settings",
            "README.md": "Settings page",
        },
    },
    "high": {
        "prompt": "Use ForgeFlow for a HIGH complexity simulation, but keep changes local and safe. Create docs/migration-plan.md with sections Risk, Rollback, Security; create src/lib/audit.ts exporting AUDIT_EVENTS; create src/app/audit/page.tsx rendering Audit and rollback; update README.md with an Audit simulation note. Do not install packages or touch secrets.",
        "checks": {
            "docs/migration-plan.md": "Rollback",
            "src/lib/audit.ts": "AUDIT_EVENTS",
            "src/app/audit/page.tsx": "Audit",
            "README.md": "Audit simulation",
        },
    },
}


def sh(cmd: list[str], cwd: Path, timeout: int = 300, check: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise RuntimeError(f"failed {cmd}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return proc


def setup(surface: str, route: str) -> Path:
    base = Path(tempfile.mkdtemp(prefix=f"forgeflow-real-e2e-{surface}-{route}-"))
    project = create_disposable_nextjs_project(base)
    if surface == "codex":
        install_codex_baseline(project)
    else:
        run(
            [
                sys.executable,
                "scripts/install_agent_presets.py",
                "--adapter",
                "claude",
                "--target",
                str(project),
                "--profile",
                "nextjs",
            ],
            cwd=ROOT,
        )
        sh(["git", "add", ".claude", "docs/forgeflow-team-init.md"], project, check=True)
        sh(["git", "commit", "-m", "install forgeflow claude preset baseline"], project, check=True)
    return project


def invoke(surface: str, project: Path, route: str, timeout: int) -> subprocess.CompletedProcess[str]:
    prompt = TASKS[route]["prompt"] + "\n\nAfter editing, final answer should be one short sentence."
    if surface == "claude":
        cmd = ["claude", "--dangerously-skip-permissions", "-p", prompt]
    else:
        # On some Linux hosts, Codex workspace-write uses bubblewrap and fails with:
        #   bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
        # This script only targets freshly-created disposable /tmp projects, so bypassing
        # the sandbox here is deliberate. Do not copy this flag into real user repos.
        cmd = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            prompt,
        ]
    return sh(cmd, project, timeout=timeout)


def verify(project: Path, route: str) -> tuple[list[str], str, str]:
    failures = []
    for rel, needle in TASKS[route]["checks"].items():
        path = project / rel
        if not path.exists():
            failures.append(f"missing {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if needle.casefold() not in text.casefold():
            failures.append(f"{rel} lacks {needle!r} case-insensitively")
    status = sh(["git", "status", "--short"], project).stdout
    diffstat = sh(["git", "diff", "--stat"], project).stdout
    return failures, status, diffstat


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--surface", choices=["claude", "codex"], required=True)
    parser.add_argument("--route", choices=list(TASKS), required=True)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    project = setup(args.surface, args.route)
    started = time.time()
    proc = invoke(args.surface, project, args.route, args.timeout)
    failures, status, diffstat = verify(project, args.route)
    result = {
        "surface": args.surface,
        "route": args.route,
        "project": str(project),
        "returncode": proc.returncode,
        "elapsed_s": round(time.time() - started, 1),
        "ok": proc.returncode == 0 and not failures,
        "failures": failures,
        "git_status": status,
        "diffstat": diffstat,
        "stdout_tail": proc.stdout[-1200:],
        "stderr_tail": proc.stderr[-1200:],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
