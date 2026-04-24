#!/usr/bin/env python3
"""Install project-local ForgeFlow presets for supported AI coding adapters."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_PROFILES = {"nextjs"}


@dataclass(frozen=True)
class AdapterSpec:
    name: str
    preset_root: Path
    install_subdir: Path
    title: str
    global_config_names: tuple[str, ...]
    forbidden_suffixes: tuple[tuple[str, ...], ...]


ADAPTERS = {
    "claude": AdapterSpec(
        name="claude",
        preset_root=ROOT / "adapters/targets/claude/agents",
        install_subdir=Path(".claude/agents"),
        title="ForgeFlow Claude Team Initialization",
        global_config_names=(".claude",),
        forbidden_suffixes=((".claude", "agents"),),
    ),
    "codex": AdapterSpec(
        name="codex",
        preset_root=ROOT / "adapters/targets/codex/agents",
        install_subdir=Path(".codex/forgeflow"),
        title="ForgeFlow Codex Preset Initialization",
        global_config_names=(".codex",),
        forbidden_suffixes=((".codex", "forgeflow"),),
    ),
    "cursor": AdapterSpec(
        name="cursor",
        preset_root=ROOT / "adapters/targets/cursor/rules",
        install_subdir=Path(".cursor/rules"),
        title="ForgeFlow Cursor Rules Initialization",
        global_config_names=(".cursor",),
        forbidden_suffixes=((".cursor", "rules"),),
    ),
}

REQUIRED_PRESETS = {
    "nextjs": {
        "claude": [
            "forgeflow-coordinator.md",
            "forgeflow-nextjs-worker.md",
            "forgeflow-quality-reviewer.md",
        ],
        "codex": [
            "forgeflow-coordinator.md",
            "forgeflow-nextjs-worker.md",
            "forgeflow-quality-reviewer.md",
        ],
        "cursor": [
            "forgeflow-coordinator.mdc",
            "forgeflow-nextjs-worker.mdc",
            "forgeflow-quality-reviewer.mdc",
        ],
    }
}


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


def has_suffix(parts: tuple[str, ...], suffix: tuple[str, ...]) -> bool:
    return len(parts) >= len(suffix) and parts[-len(suffix):] == suffix


def safe_target_root(raw_target: str, spec: AdapterSpec) -> Path:
    target = Path(raw_target).expanduser().resolve()
    parts = target.parts
    for suffix in spec.forbidden_suffixes:
        if has_suffix(parts, suffix):
            display = "/".join(suffix)
            if suffix == (".claude", "agents"):
                raise ValueError("Refusing to install into a .claude/agents directory; pass the project root instead.")
            noun = " directory" if suffix[-1] in {"agents", "forgeflow", "rules"} else ""
            raise ValueError(
                f"Refusing to install into {display}{noun}; pass the project root instead."
            )
    home = Path.home().resolve()
    if target == home:
        raise ValueError("Refusing to install into the home directory; pass a project root.")
    for config_name in spec.global_config_names:
        if target == (home / config_name).resolve():
            raise ValueError(f"Refusing to install into the home {config_name} config; pass a project root.")
    return target


def copy_presets(target: Path, profile: str, spec: AdapterSpec) -> list[Path]:
    if profile not in SUPPORTED_PROFILES:
        raise ValueError(f"Unsupported profile: {profile}")
    install_dir = target / spec.install_subdir
    install_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for name in REQUIRED_PRESETS[profile][spec.name]:
        src = spec.preset_root / name
        if not src.exists():
            raise FileNotFoundError(f"Missing preset: {src}")
        dst = install_dir / name
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


def write_doc(target: Path, profile: str, adapter: str, copied: list[Path], scripts: dict[str, str], spec: AdapterSpec) -> Path:
    doc = target / "docs" / "forgeflow-team-init.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    preset_lines = [f"- `{path.relative_to(target)}`" for path in copied]
    content = "\n".join(
        [
            f"# {spec.title}",
            "",
            f"Adapter: `{adapter}`",
            f"Profile: `{profile}`",
            "",
            "## Installed project-local ForgeFlow presets",
            "",
            *preset_lines,
            "",
            "## Safety boundary",
            "",
            f"These presets are installed under this project only. Do not create or update `{Path.home() / spec.global_config_names[0]}` for project team setup.",
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


def install(target_arg: str, adapter: str, profile: str) -> tuple[Path, list[Path], Path]:
    if adapter not in ADAPTERS:
        raise ValueError(f"Unsupported adapter: {adapter}")
    spec = ADAPTERS[adapter]
    target = safe_target_root(target_arg, spec)
    target.mkdir(parents=True, exist_ok=True)
    scripts = load_package_scripts(target)
    copied = copy_presets(target, profile, spec)
    doc = write_doc(target, profile, adapter, copied, scripts, spec)
    return target, copied, doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", choices=sorted(ADAPTERS), required=True)
    parser.add_argument("--target", required=True, help="Project root to install into")
    parser.add_argument("--profile", choices=sorted(SUPPORTED_PROFILES), default="nextjs")
    args = parser.parse_args(argv)

    try:
        target, copied, doc = install(args.target, args.adapter, args.profile)
    except Exception as exc:  # noqa: BLE001 - CLI reports concise failure
        return die(str(exc))

    print(f"Installed {len(copied)} {args.adapter} presets into {target / ADAPTERS[args.adapter].install_subdir}")
    print(f"Wrote {doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
