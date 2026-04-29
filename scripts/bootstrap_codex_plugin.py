#!/usr/bin/env python3
"""Clone-free bootstrap installer for the ForgeFlow Codex plugin.

This script is meant to be safe to run from a raw GitHub URL, for example:

    curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - -- --force
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_ARCHIVE_URL = "https://github.com/gimso2x/forgeflow/archive/refs/heads/main.zip"


def die(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download ForgeFlow to a temporary directory and run its Codex plugin installer.",
    )
    parser.add_argument(
        "--archive-url",
        default=DEFAULT_ARCHIVE_URL,
        help="ForgeFlow release archive URL. Defaults to the main branch zip archive.",
    )
    parser.add_argument(
        "installer_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to scripts/install_codex_plugin.py. Prefix with -- when needed.",
    )
    args, installer_args = parser.parse_known_args(argv)
    args.installer_args = [*args.installer_args, *installer_args]
    return args


def download_archive(url: str, target: Path) -> None:
    with urllib.request.urlopen(url) as response:  # noqa: S310 - operator-provided install URL
        target.write_bytes(response.read())


def find_checkout(extract_dir: Path) -> Path:
    candidates = [
        path
        for path in extract_dir.iterdir()
        if path.is_dir() and (path / "scripts" / "install_codex_plugin.py").exists()
    ]
    if len(candidates) != 1:
        raise ValueError(f"expected one ForgeFlow checkout in {extract_dir}, found {len(candidates)}")
    return candidates[0]


def normalize_installer_args(args: list[str]) -> list[str]:
    if args and args[0] == "--":
        return args[1:]
    return args


def run_installer(checkout: Path, installer_args: list[str]) -> int:
    installer = checkout / "scripts" / "install_codex_plugin.py"
    command = [sys.executable, str(installer), *normalize_installer_args(installer_args)]
    return subprocess.run(command, cwd=checkout, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        with tempfile.TemporaryDirectory(prefix="forgeflow-codex-") as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "forgeflow.zip"
            print(f"Downloading ForgeFlow: {args.archive_url}")
            download_archive(args.archive_url, archive)
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(tmp_path / "src")
            checkout = find_checkout(tmp_path / "src")
            print(f"Running Codex plugin installer from temporary checkout: {checkout.name}")
            return run_installer(checkout, args.installer_args)
    except Exception as exc:  # noqa: BLE001 - bootstrap should fail concisely
        return die(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
