#!/usr/bin/env python3
"""Install project-local Claude agent presets for ForgeFlow."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESET_ROOT = ROOT / "adapters/targets/claude/agents"
SUPPORTED_PROFILES = {"nextjs"}


def die(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def load_package_scripts(target: Path) -> dict[str, str]:
    package = target / "package.json"
    if not package.exists():
        return {}
    try:
        data = json.loads(package.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid package.json: {exc}") from exc
    scripts = data.get("scripts", {})
    if not isinstance(scripts, dict):
        return {}
    return {str(key): str(value) for key, value in scripts.items()}


def safe_target_root(raw_target: str) -> Path:
    target = Path(raw_target).expanduser().resolve()
    parts = target.parts
    if len(parts) >= 2 and parts[-2:] == (".claude", "agents"):
        raise ValueError("Refusing to install into a .claude/agents directory; pass the project root instead.")
    if target == Path.home().resolve() or target == (Path.home() / ".claude").resolve():
        raise ValueError("Refusing to install into the home Claude config; pass a project root.")
    return target


def copy_presets(target: Path, profile: str) -> list[Path]:
    if profile not in SUPPORTED_PROFILES:
        raise ValueError(f"Unsupported profile: {profile}")
    required = [
        "forgeflow-coordinator.md",
        "forgeflow-nextjs-worker.md",
        "forgeflow-quality-reviewer.md",
    ]
    agents_dir = target / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for name in required:
        src = PRESET_ROOT / name
        if not src.exists():
            raise FileNotFoundError(f"Missing preset: {src}")
        dst = agents_dir / name
        shutil.copyfile(src, dst)
        copied.append(dst)
    return copied


def verification_lines(scripts: dict[str, str]) -> list[str]:
    preferred = ["dev", "build", "lint", "test"]
    lines = []
    for script in preferred:
        if script in scripts:
            lines.append(f"- `npm run {script}` — `{scripts[script]}`")
    if not lines:
        lines.append("- No npm scripts found in `package.json`; add verification commands before documenting runnable checks.")
    return lines


def write_doc(target: Path, profile: str, copied: list[Path], scripts: dict[str, str]) -> Path:
    doc = target / "docs" / "forgeflow-team-init.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    agent_lines = [f"- `{path.relative_to(target)}`" for path in copied]
    content = "\n".join(
        [
            "# ForgeFlow Claude Team Initialization",
            "",
            f"Profile: `{profile}`",
            "",
            "## Installed project-local Claude agents",
            "",
            *agent_lines,
            "",
            "## Safety boundary",
            "",
            "These presets are installed under this project only. Do not create or update `~/.claude/agents` for project team setup.",
            "",
            "## Available package scripts",
            "",
            *verification_lines(scripts),
            "",
            "## Suggested ForgeFlow routing",
            "",
            "1. Use `forgeflow-coordinator.md` to choose the stage and required artifact.",
            "2. Use `forgeflow-nextjs-worker.md` for scoped Next.js implementation tasks.",
            "3. Use `forgeflow-quality-reviewer.md` before declaring the task complete.",
            "",
        ]
    )
    doc.write_text(content, encoding="utf-8")
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Project root to install into")
    parser.add_argument("--profile", choices=sorted(SUPPORTED_PROFILES), default="nextjs")
    args = parser.parse_args(argv)

    try:
        target = safe_target_root(args.target)
        target.mkdir(parents=True, exist_ok=True)
        scripts = load_package_scripts(target)
        copied = copy_presets(target, args.profile)
        doc = write_doc(target, args.profile, copied, scripts)
    except Exception as exc:  # noqa: BLE001 - CLI reports concise failure
        return die(str(exc))

    print(f"Installed {len(copied)} Claude agent presets into {target / '.claude/agents'}")
    print(f"Wrote {doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
