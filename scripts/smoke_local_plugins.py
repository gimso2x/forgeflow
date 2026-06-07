#!/usr/bin/env python3
"""Opt-in local plugin/provider-boundary smoke checks.

This smoke intentionally avoids live provider CLIs. It validates the local plugin
manifests, command namespace mapping, and dry-run install surfaces that users hit
before any real Claude/Codex/Cursor/Gemini execution.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(".")
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
CANONICAL_COMMANDS = [
    "clarify",
    "ff-plan",
    "execute",
    "ff-review",
    "ship",
    "long-run",
    "benchmark",
    "ff-config",
]
NAMESPACED = {f"/forgeflow:{command}" for command in CANONICAL_COMMANDS}
COLONLESS = {f"/{command}" for command in CANONICAL_COMMANDS}
REQUIRED_INSTALL_ARTIFACTS = [
    "skills/clarify/SKILL.md",
    "skills/ff-plan/SKILL.md",
    "skills/execute/SKILL.md",
    "skills/ff-review/SKILL.md",
    "skills/ship/SKILL.md",
    "skills/long-run/SKILL.md",
    "skills/benchmark/SKILL.md",
    "skills/ff-config/SKILL.md",
    "templates/brief.md",
    "templates/plan.md",
    "templates/implementation-notes.md",
    "templates/review-report.md",
    "templates/ledger.md",
    "templates/checkpoint.md",
    "templates/run-state.json",
]

failures: list[str] = []


def load_json(path: str) -> dict:
    file = ROOT / path
    if not file.exists():
        failures.append(f"{path}: missing")
        return {}
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"{path}: invalid JSON: {exc}")
        return {}


def command_token(prompt: str) -> str:
    return prompt.split()[0]


def validate_manifest(path: str, *, cursor: bool = False) -> None:
    data = load_json(path)
    if not data:
        return
    if data.get("name") != "forgeflow":
        failures.append(f"{path}: name must be forgeflow")
    if data.get("version") != VERSION:
        failures.append(f"{path}: version must match VERSION={VERSION}")
    prompts = data.get("interface", {}).get("defaultPrompt")
    if not isinstance(prompts, list) or not prompts:
        failures.append(f"{path}: interface.defaultPrompt must be a non-empty list")
        return
    tokens = {command_token(prompt) for prompt in prompts if isinstance(prompt, str)}
    expected = COLONLESS if cursor else NAMESPACED
    if tokens != expected:
        failures.append(
            f"{path}: defaultPrompt command set mismatch; expected {sorted(expected)}, got {sorted(tokens)}"
        )
    for prompt in prompts:
        if not isinstance(prompt, str) or not prompt.startswith("/"):
            failures.append(f"{path}: defaultPrompt entry must be a slash command: {prompt!r}")
            continue
        token = command_token(prompt)
        if cursor and ":" in token:
            failures.append(f"{path}: Cursor commands must be colonless: {prompt!r}")
        if not cursor and not token.startswith("/forgeflow:"):
            failures.append(f"{path}: provider plugin command must use /forgeflow: namespace: {prompt!r}")


def validate_marketplaces() -> None:
    agents = load_json(".agents/plugins/marketplace.json")
    if agents:
        plugins = agents.get("plugins")
        path = (((plugins or [{}])[0]).get("source") or {}).get("path") if isinstance(plugins, list) else None
        if path != "./plugins/forgeflow":
            failures.append(".agents/plugins/marketplace.json: source.path must be ./plugins/forgeflow")

    claude = load_json(".claude-plugin/marketplace.json")
    if claude:
        if claude.get("metadata", {}).get("version") != VERSION:
            failures.append(".claude-plugin/marketplace.json: metadata.version must match VERSION")
        plugins = claude.get("plugins")
        source = (plugins or [{}])[0].get("source") if isinstance(plugins, list) else None
        if source != "./":
            failures.append(".claude-plugin/marketplace.json: plugin source must be ./")


def validate_gemini_extension() -> None:
    data = load_json("gemini-extension.json")
    if not data:
        return
    if data.get("version") != VERSION:
        failures.append("gemini-extension.json: version must match VERSION")
    context = data.get("contextFileName")
    if context != "GEMINI.md" or not (ROOT / "GEMINI.md").exists():
        failures.append("gemini-extension.json: contextFileName must point to tracked GEMINI.md")
    gemini_text = (ROOT / "GEMINI.md").read_text(encoding="utf-8") if (ROOT / "GEMINI.md").exists() else ""
    for command in CANONICAL_COMMANDS:
        skill_ref = f"@./skills/{command}/SKILL.md"
        if skill_ref not in gemini_text:
            failures.append(f"GEMINI.md: missing Gemini context import {skill_ref}")


def validate_required_artifacts(base: Path, label: str) -> None:
    for rel in REQUIRED_INSTALL_ARTIFACTS:
        path = base / rel
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(f"{label}: missing or empty install artifact {rel}")


def validate_install_surfaces() -> None:
    validate_required_artifacts(ROOT, "repo root")
    validate_required_artifacts(ROOT / ".codex-plugin", ".codex-plugin package")
    with tempfile.TemporaryDirectory(prefix="forgeflow-smoke-") as tmp:
        dest = Path(tmp) / "codex-local" / "forgeflow"
        dest.mkdir(parents=True)
        shutil.copy2(ROOT / ".codex-plugin" / "plugin.json", dest / "plugin.json")
        shutil.copytree(ROOT / "skills", dest / "skills")
        shutil.copytree(ROOT / "templates", dest / "templates")
        validate_required_artifacts(dest, "dry-run codex local install")


def main() -> int:
    validate_manifest(".claude-plugin/plugin.json")
    validate_manifest(".codex-plugin/plugin.json")
    validate_manifest(".cursor-plugin/plugin.json", cursor=True)
    validate_marketplaces()
    validate_gemini_extension()
    validate_install_surfaces()

    if failures:
        print("ERROR: local plugin smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("OK: local plugin manifests, command namespaces, and dry-run install surfaces are coherent")
    print("OK: live provider CLIs were not invoked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
