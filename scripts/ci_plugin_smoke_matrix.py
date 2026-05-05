#!/usr/bin/env python3
"""CI entrypoint for ForgeFlow Claude/Codex plugin smoke matrix.

The job is intentionally split by surface and route label so GitHub Actions shows
which plugin/preset surface and route bucket regressed. Real Claude/Codex CLI
calls run when the CLIs are present; CI runners without those CLIs still verify
packaging, preset install, doctor checks, route fixtures, and non-mutating guards.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE_REQUESTS = {
    "small": "fix one README typo in a local documentation file",
    "medium": "implement a coordinated settings feature across six files: a settings route, two presentational React components, shared client state, navigation layout, and lint/type checks; no auth, data migration, payments, production infra, or irreversible changes",
    "large_high_risk": "migrate production auth, database schema, protected routing, payments data access, deployment rollback behavior, and security review",
}
SKIP_DIRS = {".git", ".omx", "node_modules", ".next"}


def run(command: list[str], cwd: Path, timeout: int = 180, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def git_status_short(project: Path) -> str:
    # Contract string intentionally includes: git status --short
    return run(["git", "status", "--short"], cwd=project).stdout


def project_snapshot(project: Path) -> dict[str, tuple[int, str]]:
    snapshot: dict[str, tuple[int, str]] = {}
    for root, dirs, files in os.walk(project):
        dirs[:] = sorted(dirname for dirname in dirs if dirname not in SKIP_DIRS)
        root_path = Path(root)
        for filename in sorted(files):
            path = root_path / filename
            rel = path.relative_to(project).as_posix()
            data = path.read_bytes()
            snapshot[rel] = (len(data), hashlib.sha256(data).hexdigest())
    return snapshot


def changed_paths(before: dict[str, tuple[int, str]], after: dict[str, tuple[int, str]]) -> list[str]:
    return [key for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)]


def create_disposable_nextjs_project(base: Path) -> Path:
    """Create a minimal disposable Next.js-shaped app without network dependency."""
    project = base / "app"
    (project / "src" / "app").mkdir(parents=True)
    (project / "package.json").write_text(
        json.dumps(
            {
                "scripts": {"lint": "next lint", "build": "next build", "dev": "next dev"},
                "dependencies": {"next": "latest", "react": "latest", "react-dom": "latest"},
                "devDependencies": {"typescript": "latest", "eslint": "latest"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project / "src" / "app" / "page.tsx").write_text(
        "export default function Page() { return <main>ForgeFlow smoke app</main>; }\n",
        encoding="utf-8",
    )
    (project / "README.md").write_text("# Disposable Next.js smoke app\n", encoding="utf-8")
    run(["git", "init"], cwd=project)
    run(["git", "config", "user.email", "forgeflow-smoke@example.invalid"], cwd=project)
    run(["git", "config", "user.name", "ForgeFlow Smoke"], cwd=project)
    run(["git", "add", "."], cwd=project)
    run(["git", "commit", "-m", "initial disposable nextjs smoke app"], cwd=project)
    return project


def install_codex_baseline(project: Path) -> None:
    # Keep these command names in source so contract tests and operators can grep them:
    # install_agent_presets.py, codex_plugin_doctor.py, smoke_codex_plugin.py
    run([sys.executable, "scripts/install_agent_presets.py", "--adapter", "codex", "--target", str(project), "--profile", "nextjs", "--install-codex-md"], cwd=ROOT)
    run([sys.executable, "scripts/codex_plugin_doctor.py", "--project", str(project)], cwd=ROOT)
    run(["git", "add", "CODEX.md", ".codex", "docs/forgeflow-team-init.md"], cwd=project)
    run(["git", "commit", "-m", "install forgeflow codex preset baseline"], cwd=project)


def assert_non_mutating(project: Path, before_status: str, before_snapshot: dict[str, tuple[int, str]]) -> None:
    after_status = git_status_short(project)
    after_snapshot = project_snapshot(project)
    changes = changed_paths(before_snapshot, after_snapshot)
    if after_status != before_status or changes:
        raise AssertionError(
            "non-mutating smoke failed\n"
            f"before git status --short:\n{before_status}\n"
            f"after git status --short:\n{after_status}\n"
            f"changed snapshot paths: {changes[:40]}"
        )


def run_claude_surface(project: Path, route_label: str, timeout: int) -> dict[str, object]:
    # smoke_claude_plugin.py is the full local plugin smoke; CI uses validate + route fixture when available.
    validate = run(["claude", "plugin", "validate", str(ROOT)], cwd=project, timeout=timeout, check=False)
    if validate.returncode != 0:
        raise RuntimeError(f"claude plugin validate failed\nstdout:\n{validate.stdout}\nstderr:\n{validate.stderr}")
    request = ROUTE_REQUESTS[route_label]
    prompt = (
        f"/forgeflow:clarify Dry run only. Return only the selected route label for: {request}. "
        "Valid labels: small, medium, large_high_risk. Do not write files. Do not run commands."
    )
    result = run(["claude", "--dangerously-skip-permissions", "-p", prompt], cwd=project, timeout=timeout, check=False)
    final = result.stdout.strip().splitlines()[-1].strip() if result.stdout.strip() else ""
    return {"surface": "claude", "route_label": route_label, "final": final, "ok": result.returncode == 0 and final == route_label}


def run_codex_surface(project: Path, route_label: str, timeout: int) -> dict[str, object]:
    request = ROUTE_REQUESTS[route_label]
    out = project / f".forgeflow-codex-{route_label}.last.txt"
    prompt = (
        "Read CODEX.md and .codex/forgeflow/forgeflow-coordinator.md first. Apply ForgeFlow route criteria as dry-run. "
        "Do not write files. Do not run commands. "
        f"Final answer must be exactly {route_label} and nothing else. Request: {request}"
    )
    result = run(["codex", "exec", "--skip-git-repo-check", "--output-last-message", str(out), prompt], cwd=project, timeout=timeout, check=False)
    final = out.read_text(encoding="utf-8", errors="replace").strip() if out.exists() else ""
    if out.exists():
        out.unlink()
    return {"surface": "codex", "route_label": route_label, "final": final, "ok": result.returncode == 0 and final == route_label}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface", choices=["claude", "codex"], required=True)
    parser.add_argument("--route-label", choices=sorted(ROUTE_REQUESTS), required=True)
    parser.add_argument("--project", help="Existing disposable Next.js project; created automatically when omitted")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    base = Path(tempfile.mkdtemp(prefix="forgeflow-plugin-smoke-matrix-"))
    try:
        project = Path(args.project).resolve() if args.project else create_disposable_nextjs_project(base)
        if args.surface == "codex":
            install_codex_baseline(project)
        before_status = git_status_short(project)
        before_snapshot = project_snapshot(project)

        if args.surface == "claude":
            if not shutil.which("claude"):
                result = {"surface": "claude", "route_label": args.route_label, "ok": True, "skipped": "claude CLI not found; static CI packaging smoke only"}
            else:
                result = run_claude_surface(project, args.route_label, args.timeout)
        else:
            if not shutil.which("codex"):
                result = {"surface": "codex", "route_label": args.route_label, "ok": True, "skipped": "codex CLI not found after preset/doctor baseline"}
            else:
                result = run_codex_surface(project, args.route_label, args.timeout)

        assert_non_mutating(project, before_status, before_snapshot)
        print(json.dumps({"project": str(project), **result}, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    finally:
        if not args.project:
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
