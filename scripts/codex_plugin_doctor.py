#!/usr/bin/env python3
"""Read-only ForgeFlow Codex plugin/preset doctor."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PLUGIN_NAME = "forgeflow"
DEFAULT_MARKETPLACE_PATH = Path.home() / ".agents" / "plugins" / "marketplace.json"
DEFAULT_PLUGIN_ROOT = Path.home() / "plugins" / PLUGIN_NAME


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def _status(ok: bool, warn: bool = False) -> str:
    if ok:
        return "PASS"
    if warn:
        return "WARN"
    return "FAIL"


def _run_version(command: str) -> str | None:
    binary = shutil.which(command)
    if not binary:
        return None
    for args in ([binary, "--version"], [binary, "version"]):
        result = subprocess.run(args, text=True, capture_output=True, check=False, timeout=10)
        output = (result.stdout or result.stderr).strip()
        if result.returncode == 0 and output:
            return output.splitlines()[0]
    return binary


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def marketplace_check(path: Path) -> Check:
    data = _load_json(path)
    if data is None:
        return Check("marketplace", "FAIL", f"missing or invalid JSON: {path}")
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        return Check("marketplace", "FAIL", f"plugins must be a list: {path}")
    entry = next((item for item in plugins if isinstance(item, dict) and item.get("name") == PLUGIN_NAME), None)
    if not entry:
        return Check("marketplace", "FAIL", f"no {PLUGIN_NAME!r} entry in {path}")
    source = entry.get("source", {})
    source_path = source.get("path") if isinstance(source, dict) else None
    return Check("marketplace", "PASS", f"{path} -> {source_path or '<no source.path>'}")


def plugin_root_check(path: Path) -> Check:
    manifest = path / ".codex-plugin" / "plugin.json"
    skills = path / "skills"
    if not manifest.exists():
        return Check("plugin_root", "FAIL", f"missing {manifest}")
    data = _load_json(manifest)
    if not data or data.get("name") not in {PLUGIN_NAME, "forgeflow-codex"}:
        return Check("plugin_root", "FAIL", f"invalid plugin name in {manifest}")
    if not skills.exists():
        return Check("plugin_root", "FAIL", f"missing {skills}")
    return Check("plugin_root", "PASS", str(path))


def project_check(project: Path) -> list[Check]:
    checks: list[Check] = []
    codex_md = project / "CODEX.md"
    forgeflow_dir = project / ".forgeflow"
    preset_dir = project / ".codex" / "forgeflow"
    checks.append(Check("project_CODEX", _status(codex_md.exists(), warn=True), str(codex_md)))
    checks.append(Check("project_forgeflow_dir", _status(forgeflow_dir.exists(), warn=True), str(forgeflow_dir)))
    checks.append(Check("project_codex_preset", _status(preset_dir.exists(), warn=True), str(preset_dir)))
    if codex_md.exists():
        text = codex_md.read_text(encoding="utf-8", errors="replace")
        has_artifact_policy = ".forgeflow/tasks" in text and "run-state.json" in text
        checks.append(Check("artifact_policy", _status(has_artifact_policy), "CODEX.md mentions .forgeflow/tasks and run-state.json"))
    else:
        checks.append(Check("artifact_policy", "WARN", "CODEX.md missing; cannot verify artifact policy"))
    return checks


def collect_checks(args: argparse.Namespace) -> list[Check]:
    checks = [
        Check("codex_cli", _status(_run_version("codex") is not None, warn=True), _run_version("codex") or "codex not found on PATH"),
        marketplace_check(Path(args.marketplace_path).expanduser()),
        plugin_root_check(Path(args.plugin_root).expanduser()),
    ]
    if args.project:
        checks.extend(project_check(Path(args.project).expanduser().resolve()))
    return checks


def print_text(checks: list[Check]) -> None:
    worst = "PASS"
    if any(check.status == "FAIL" for check in checks):
        worst = "FAIL"
    elif any(check.status == "WARN" for check in checks):
        worst = "WARN"
    print(f"ForgeFlow Codex doctor: {worst}")
    for check in checks:
        print(f"[{check.status}] {check.name}: {check.detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marketplace-path", default=str(DEFAULT_MARKETPLACE_PATH))
    parser.add_argument("--plugin-root", default=str(DEFAULT_PLUGIN_ROOT))
    parser.add_argument("--project", help="Project root to inspect for CODEX.md/.forgeflow/.codex/forgeflow")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    checks = collect_checks(args)
    payload = {"ok": all(check.status != "FAIL" for check in checks), "checks": [check.__dict__ for check in checks]}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_text(checks)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
