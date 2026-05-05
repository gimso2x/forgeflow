#!/usr/bin/env python3
"""Smoke-test ForgeFlow Codex route classification in a project-local preset."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALID_LABELS = {"small", "medium", "large_high_risk"}
SNAPSHOT_SKIP_DIRS = {".git", ".omx", "node_modules"}
CASES = [
    (
        "codex_small",
        "small",
        "fix one README typo in a local documentation file",
    ),
    (
        "codex_medium",
        "medium",
        "implement a coordinated settings feature across six files: a settings route, two presentational React components, shared client state, navigation layout, and lint/type checks; no auth, data migration, payments, production infra, or irreversible changes",
    ),
    (
        "codex_high",
        "large_high_risk",
        "migrate production auth, database schema, and deployment rollback behavior for payments",
    ),
]


def run(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)


def git_status(project: Path) -> str:
    return subprocess.check_output(["git", "status", "--short"], cwd=project, text=True)


def project_snapshot(project: Path) -> dict[str, tuple[int, str]]:
    """Return a content snapshot including ignored files, except agent/runtime dependency dirs."""
    snapshot: dict[str, tuple[int, str]] = {}
    for root, dirs, files in os.walk(project):
        dirs[:] = sorted(dirname for dirname in dirs if dirname not in SNAPSHOT_SKIP_DIRS)
        root_path = Path(root)
        for filename in sorted(files):
            path = root_path / filename
            relative = path.relative_to(project).as_posix()
            try:
                data = path.read_bytes()
            except OSError as exc:
                snapshot[relative] = (-1, f"<read-error:{exc.__class__.__name__}>")
                continue
            snapshot[relative] = (len(data), hashlib.sha256(data).hexdigest())
    return snapshot


def snapshot_changed(before: dict[str, tuple[int, str]], after: dict[str, tuple[int, str]]) -> list[str]:
    keys = sorted(set(before) | set(after))
    return [key for key in keys if before.get(key) != after.get(key)]


def assert_project_ready(project: Path) -> None:
    missing = [
        str(path.relative_to(project))
        for path in [project / "CODEX.md", project / ".codex" / "forgeflow"]
        if not path.exists()
    ]
    if missing:
        raise AssertionError(
            "Codex smoke requires project-local ForgeFlow preset; missing "
            + ", ".join(missing)
            + ". Run: python3 scripts/install_agent_presets.py --adapter codex --target "
            + str(project)
            + " --profile nextjs --install-codex-md"
        )


def smoke_case(project: Path, name: str, expected: str, request: str, timeout: int, out_dir: Path) -> dict[str, object]:
    last_message = out_dir / f"{name}.last.txt"
    prompt = (
        "Read CODEX.md and .codex/forgeflow/forgeflow-coordinator.md first. Then apply the ForgeFlow /forgeflow:clarify route criteria as a dry-run route-label check. "
        "Do not write files. Do not run commands. "
        "Your final answer must be exactly one route label and nothing else: small, medium, or large_high_risk. "
        f"Request: {request}"
    )
    before = git_status(project)
    before_snapshot = project_snapshot(project)
    started = time.monotonic()
    result = run(
        [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--output-last-message",
            str(last_message),
            prompt,
        ],
        cwd=project,
        timeout=timeout,
    )
    duration = round(time.monotonic() - started, 1)
    final = last_message.read_text(encoding="utf-8", errors="replace").strip() if last_message.exists() else ""
    after = git_status(project)
    changed_paths = snapshot_changed(before_snapshot, project_snapshot(project))
    final_is_valid = final in VALID_LABELS
    ok = result.returncode == 0 and final_is_valid and final == expected and after == before and not changed_paths
    return {
        "name": name,
        "expected": expected,
        "final": final,
        "returncode": result.returncode,
        "duration_seconds": duration,
        "git_status_unchanged": after == before,
        "project_snapshot_unchanged": not changed_paths,
        "changed_paths": changed_paths[:20],
        "final_is_valid_label": final_is_valid,
        "ok": ok,
        "stderr_tail": "\n".join(result.stderr.splitlines()[-20:]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project root containing CODEX.md and .codex/forgeflow")
    parser.add_argument("--timeout", type=int, default=180, help="per-Codex-call timeout seconds")
    parser.add_argument("--json-output", help="Optional path for machine-readable result JSON")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary last-message files")
    args = parser.parse_args()

    if not shutil.which("codex"):
        print("CODEX PLUGIN SMOKE: SKIP - codex CLI not found")
        return 77

    project = Path(args.project).expanduser().resolve()
    out_dir = Path(tempfile.mkdtemp(prefix="forgeflow-codex-plugin-smoke-"))
    payload: dict[str, object] = {"project": str(project), "results": []}

    try:
        assert_project_ready(project)
        before_all = git_status(project)
        before_snapshot_all = project_snapshot(project)
        results = [smoke_case(project, name, expected, request, args.timeout, out_dir) for name, expected, request in CASES]
        payload["results"] = results
        payload["ok"] = (
            all(result["ok"] for result in results)
            and git_status(project) == before_all
            and not snapshot_changed(before_snapshot_all, project_snapshot(project))
        )
        for result in results:
            print(f"{result['name']}: expected={result['expected']} final={result['final']} ok={result['ok']}")
        if args.json_output:
            Path(args.json_output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OUT_DIR={out_dir}")
        print("CODEX PLUGIN SMOKE: PASS" if payload["ok"] else "CODEX PLUGIN SMOKE: FAIL")
        return 0 if payload["ok"] else 1
    except Exception as exc:  # noqa: BLE001 - command-line smoke should print concise failure.
        payload["ok"] = False
        payload["error"] = str(exc)
        if args.json_output:
            Path(args.json_output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("CODEX PLUGIN SMOKE: FAIL", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(f"OUT_DIR={out_dir}", file=sys.stderr)
        return 1
    finally:
        if not args.keep_temp:
            shutil.rmtree(out_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
