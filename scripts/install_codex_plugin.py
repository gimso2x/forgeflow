#!/usr/bin/env python3
"""Install ForgeFlow as a home-local Codex plugin marketplace entry."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "forgeflow"
DEFAULT_PLUGIN_PARENT = Path.home() / "plugins"
DEFAULT_MARKETPLACE_PATH = Path.home() / ".agents" / "plugins" / "marketplace.json"
DEFAULT_SOURCE_PATH = f"./plugins/{PLUGIN_NAME}"

IGNORE_NAMES = {
    ".git",
    ".venv",
    ".forgeflow",
    "__pycache__",
    ".pytest_cache",
}


def die(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plugin-parent",
        default=str(DEFAULT_PLUGIN_PARENT),
        help="Directory that will receive the forgeflow plugin copy. Defaults to ~/plugins.",
    )
    parser.add_argument(
        "--marketplace-path",
        default=str(DEFAULT_MARKETPLACE_PATH),
        help="Codex marketplace file to create/update. Defaults to ~/.agents/plugins/marketplace.json.",
    )
    parser.add_argument(
        "--source-path",
        default=DEFAULT_SOURCE_PATH,
        help="Marketplace source.path for ForgeFlow. Defaults to ./plugins/forgeflow.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing home-local plugin copy or differing marketplace entry.",
    )
    parser.add_argument(
        "--skip-copy",
        action="store_true",
        help="Only update the marketplace entry; assumes source.path already points at a valid plugin.",
    )
    return parser.parse_args(argv)


def ignore(_dir: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in IGNORE_NAMES}
    ignored.update(name for name in names if name.endswith(".pyc") or name.endswith(".pyo"))
    return ignored


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "name": "local-codex-plugins",
            "interface": {"displayName": "Local Codex Plugins"},
            "plugins": [],
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    data.setdefault("name", "local-codex-plugins")
    interface = data.setdefault("interface", {})
    if not isinstance(interface, dict):
        raise ValueError(f"{path}: interface must be an object")
    interface.setdefault("displayName", "Local Codex Plugins")
    plugins = data.setdefault("plugins", [])
    if not isinstance(plugins, list):
        raise ValueError(f"{path}: plugins must be a list")
    return data


def plugin_entry(source_path: str) -> dict[str, Any]:
    return {
        "name": PLUGIN_NAME,
        "source": {
            "source": "local",
            "path": source_path,
        },
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        },
        "category": "Coding",
    }


def update_marketplace(path: Path, entry: dict[str, Any], *, force: bool) -> str:
    marketplace = load_json(path)
    plugins = marketplace["plugins"]
    existing_index = next(
        (index for index, plugin in enumerate(plugins) if isinstance(plugin, dict) and plugin.get("name") == PLUGIN_NAME),
        None,
    )

    if existing_index is None:
        plugins.append(entry)
        action = "added"
    elif plugins[existing_index] == entry:
        action = "unchanged"
    elif force:
        plugins[existing_index] = entry
        action = "updated"
    else:
        raise ValueError(
            f"{path} already has a different {PLUGIN_NAME} entry; re-run with --force to replace it"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return action


def install_plugin_copy(plugin_parent: Path, *, force: bool) -> Path:
    target = (plugin_parent / PLUGIN_NAME).resolve()
    if target == ROOT:
        return target
    if target.exists():
        if not force:
            raise ValueError(f"{target} already exists; re-run with --force to replace it")
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT, target, ignore=ignore)
    return target


def validate_plugin_root(path: Path) -> None:
    manifest = path / ".codex-plugin" / "plugin.json"
    skills = path / "skills"
    if not manifest.exists():
        raise ValueError(f"{path} is not a Codex plugin root: missing .codex-plugin/plugin.json")
    if not skills.exists():
        raise ValueError(f"{path} is not a Codex plugin root: missing skills/")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("name") != PLUGIN_NAME:
        raise ValueError(f"{manifest} name must be {PLUGIN_NAME!r}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    plugin_parent = Path(args.plugin_parent).expanduser().resolve()
    marketplace_path = Path(args.marketplace_path).expanduser().resolve()

    try:
        if args.skip_copy:
            plugin_root = plugin_parent / PLUGIN_NAME
        else:
            plugin_root = install_plugin_copy(plugin_parent, force=args.force)
        validate_plugin_root(plugin_root)
        action = update_marketplace(
            marketplace_path,
            plugin_entry(args.source_path),
            force=args.force,
        )
    except Exception as exc:  # noqa: BLE001 - CLI reports concise failure
        return die(str(exc))

    print(f"ForgeFlow plugin root: {plugin_root}")
    print(f"Marketplace entry {action}: {marketplace_path}")
    print("Restart Codex Desktop, install or enable ForgeFlow from the local marketplace if prompted, then use /forgeflow:clarify or /forgeflow:init.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
