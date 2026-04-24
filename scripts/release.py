#!/usr/bin/env python3
"""Automate ForgeFlow release preparation and verification."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_JSON = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = ROOT / ".claude-plugin" / "marketplace.json"
CODEX_PLUGIN_JSON = ROOT / ".codex-plugin" / "plugin.json"
CURSOR_PLUGIN_JSON = ROOT / ".cursor-plugin" / "plugin.json"
PLUGIN_VERSION_JSONS = [PLUGIN_JSON, CODEX_PLUGIN_JSON, CURSOR_PLUGIN_JSON]
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and verify a ForgeFlow release.")
    parser.add_argument("version", help="Plain semver version, for example 0.1.14. Do not include a leading v.")
    parser.add_argument("--dry-run", action="store_true", help="Print the release plan without writing files or running commands.")
    parser.add_argument("--write-only", action="store_true", help="Update version files and notes, but skip checks, commit, and tag.")
    parser.add_argument("--skip-checks", action="store_true", help="Skip pytest/make verification before commit/tag.")
    parser.add_argument("--no-commit", action="store_true", help="Do not create the release commit.")
    parser.add_argument("--no-tag", action="store_true", help="Do not create the annotated release tag.")
    parser.add_argument("--notes-out", type=Path, help="Write release note draft to this path.")
    return parser.parse_args()


def validate_version(version: str) -> None:
    if not SEMVER_RE.match(version) or version.startswith("v"):
        raise ValueError("version must be plain semver like 0.1.14; do not include a leading v")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_versions(version: str) -> None:
    for path in PLUGIN_VERSION_JSONS:
        plugin = load_json(path)
        plugin["version"] = version
        dump_json(path, plugin)
    marketplace = load_json(MARKETPLACE_JSON)
    marketplace.setdefault("metadata", {})["version"] = version
    dump_json(MARKETPLACE_JSON, marketplace)


def release_notes(version: str) -> str:
    tag = f"v{version}"
    return f"""## {tag}

Verification checklist:
- `pytest -q`
- `make validate`
- `make smoke-claude-plugin`

Release commands:
- `git commit -am "chore: release {tag}"`
- `git tag -a {tag} -m "{tag}"`
- `git push origin main {tag}`
"""


def write_notes(path: Path, version: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(release_notes(version), encoding="utf-8")


def run(command: list[str]) -> None:
    print("$ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def relative_to_root(path: Path) -> Path:
    resolved = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    try:
        return resolved.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"release file must be inside repository: {path}") from exc


def release_files_to_stage(notes_out: Path | None = None) -> list[str]:
    paths = [
        PLUGIN_JSON.relative_to(ROOT),
        CODEX_PLUGIN_JSON.relative_to(ROOT),
        CURSOR_PLUGIN_JSON.relative_to(ROOT),
        MARKETPLACE_JSON.relative_to(ROOT),
    ]
    if notes_out is not None:
        paths.append(relative_to_root(notes_out))
    return [str(path) for path in paths]


def staged_paths() -> list[str]:
    result = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True, capture_output=True, check=True)
    return [line for line in result.stdout.splitlines() if line.strip()]


def release_plan(version: str) -> str:
    tag = f"v{version}"
    return "\n".join(
        [
            f"Release plan for {tag}",
            f"1. update plugin manifests version to {version}",
            f"2. update .claude-plugin/marketplace.json metadata.version to {version}",
            "3. run pytest -q",
            "4. run make validate",
            "5. run make smoke-claude-plugin",
            f"6. create git commit: chore: release {tag}",
            f"7. create annotated tag: {tag}",
            f"8. push with: git push origin main {tag}",
        ]
    )


def main() -> int:
    args = parse_args()
    try:
        validate_version(args.version)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(release_plan(args.version))
    if args.dry_run:
        if args.notes_out:
            print(f"Dry-run: would write release notes to {args.notes_out}")
        return 0
    if not args.no_commit and not args.write_only:
        staged = staged_paths()
        if staged:
            print(
                "ERROR: pre-existing staged changes would be included in the release commit: " + ", ".join(staged),
                file=sys.stderr,
            )
            return 2

    update_versions(args.version)
    if args.notes_out:
        write_notes(args.notes_out, args.version)

    if args.write_only:
        print("WRITE ONLY: updated release files; checks, commit, and tag skipped.")
        return 0

    if not args.skip_checks:
        run([sys.executable, "-m", "pytest", "-q"])
        run(["make", "validate"])
        run(["make", "smoke-claude-plugin"])

    tag = f"v{args.version}"
    if not args.no_commit:
        run(["git", "add", *release_files_to_stage(args.notes_out)])
        run(["git", "commit", "-m", f"chore: release {tag}"])

    if not args.no_tag:
        run(["git", "tag", "-a", tag, "-m", tag])

    print(f"Release {tag} prepared. Push with: git push origin main {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
