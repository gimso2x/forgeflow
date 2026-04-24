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
STARTER_DOCS_ROOT = ROOT / "templates/starter-docs"
STARTER_DOC_NAMES = ("PRD.md", "ARCHITECTURE.md", "ADR.md", "UI_GUIDE.md")


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


def copy_starter_docs(target: Path) -> list[Path]:
    docs_dir = target / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for name in STARTER_DOC_NAMES:
        src = STARTER_DOCS_ROOT / name
        if not src.exists():
            raise FileNotFoundError(f"Missing starter doc template: {src}")
        dst = docs_dir / name
        if dst.exists():
            continue
        shutil.copyfile(src, dst)
        created.append(dst)
    return created


def verification_lines(scripts: dict[str, str]) -> list[str]:
    preferred = ["dev", "build", "lint", "test"]
    lines = []
    for script in preferred:
        if script in scripts:
            lines.append(f"- `npm run {script}` — `{scripts[script]}`")
    if not lines:
        lines.append("- No npm scripts found in `package.json`; add verification commands before documenting runnable checks.")
    return lines


def write_doc(
    target: Path,
    profile: str,
    adapter: str,
    copied: list[Path],
    scripts: dict[str, str],
    spec: AdapterSpec,
    starter_docs: list[Path],
) -> Path:
    doc = target / "docs" / "forgeflow-team-init.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    preset_lines = [f"- `{path.relative_to(target)}`" for path in copied]
    starter_lines = [f"- `{path.relative_to(target)}`" for path in starter_docs]
    if not starter_lines:
        starter_lines = ["- No starter docs were created in this run. Existing project docs are preserved."]
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
            "## Starter docs",
            "",
            *starter_lines,
            "",
            "Use these as project-local inputs for ForgeFlow planning. They guide product, architecture, decisions, and UI expectations without replacing canonical artifacts like `brief.json`, `plan-ledger.json`, `run-state.json`, or `review-report.json`.",
            "",
            "## Active role prompts",
            "",
            "- `forgeflow-coordinator` — chooses stage, route, missing artifacts, and next handoff.",
            "- `forgeflow-nextjs-worker` — performs scoped implementation and records evidence.",
            "- `forgeflow-quality-reviewer` — performs independent quality review before completion claims.",
            "",
            "## Review contract",
            "",
            "- Do not claim done without fresh verification evidence.",
            "- Require independent quality review for non-trivial implementation work.",
            "- Reject changes that drift from PRD, Architecture, ADR, or ForgeFlow stage artifacts.",
            "",
            "## Failure handling",
            "",
            "- If verification fails, record the failing command and fix the smallest cause first.",
            "- If scope changes, return to `/forgeflow:clarify` instead of silently expanding the task.",
            "- If review rejects the change, update the plan/evidence before another completion claim.",
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
            "## Recommended first run",
            "",
            "1. Fill or skim `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ADR.md`, and `docs/UI_GUIDE.md` when they exist.",
            "2. Start with `/forgeflow:clarify <task>`.",
            "3. Let the agent produce the plan and then run within the approved scope.",
            "4. Run the available verification commands below and attach evidence to the final report.",
            "",
        ]
    )
    doc.write_text(content, encoding="utf-8")
    return doc


def install(target_arg: str, adapter: str, profile: str, *, with_starter_docs: bool = False) -> tuple[Path, list[Path], Path, list[Path]]:
    if adapter not in ADAPTERS:
        raise ValueError(f"Unsupported adapter: {adapter}")
    spec = ADAPTERS[adapter]
    target = safe_target_root(target_arg, spec)
    target.mkdir(parents=True, exist_ok=True)
    scripts = load_package_scripts(target)
    copied = copy_presets(target, profile, spec)
    starter_docs = copy_starter_docs(target) if with_starter_docs else []
    doc = write_doc(target, profile, adapter, copied, scripts, spec, starter_docs)
    return target, copied, doc, starter_docs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", choices=sorted(ADAPTERS), required=True)
    parser.add_argument("--target", required=True, help="Project root to install into")
    parser.add_argument("--profile", choices=sorted(SUPPORTED_PROFILES), default="nextjs")
    parser.add_argument(
        "--with-starter-docs",
        action="store_true",
        help="Create missing docs/PRD.md, ARCHITECTURE.md, ADR.md, and UI_GUIDE.md starter templates",
    )
    args = parser.parse_args(argv)

    try:
        target, copied, doc, starter_docs = install(
            args.target,
            args.adapter,
            args.profile,
            with_starter_docs=args.with_starter_docs,
        )
    except Exception as exc:  # noqa: BLE001 - CLI reports concise failure
        return die(str(exc))

    print(f"Installed {len(copied)} {args.adapter} presets into {target / ADAPTERS[args.adapter].install_subdir}")
    if args.with_starter_docs:
        print(f"Created {len(starter_docs)} starter docs under {target / 'docs'}")
    print(f"Wrote {doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
