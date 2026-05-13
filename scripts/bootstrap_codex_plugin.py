#!/usr/bin/env python3
"""Clone-free bootstrap installer for the ForgeFlow Codex plugin.

This script is meant to be safe to run from a raw GitHub URL, for example:

    curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - -- --force

Security features:
  - Optional SHA-256 checksum verification via --checksum.
  - Dry-run mode shows what would be done without extracting or running.
  - Zip bomb protection: refuses archives exceeding size limits.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_ARCHIVE_URL = "https://github.com/gimso2x/forgeflow/archive/refs/heads/main.zip"

# Zip bomb protection limits
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_EXTRACTED_BYTES = 500 * 1024 * 1024  # 500 MB total extracted
MAX_SINGLE_FILE_BYTES = 50 * 1024 * 1024  # 50 MB per file


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
        "--checksum",
        default=None,
        help="Expected SHA-256 hex digest of the archive. Verifies integrity when provided.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without extracting or running the installer.",
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
        data = response.read()
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError(
            f"Archive too large ({len(data)} bytes, max {MAX_ARCHIVE_BYTES}). "
            "Possible zip bomb or wrong URL."
        )
    target.write_bytes(data)


def verify_checksum(archive_path: Path, expected_hex: str) -> None:
    sha = hashlib.sha256()
    with open(archive_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    actual = sha.hexdigest()
    if actual != expected_hex:
        raise ValueError(
            f"Checksum mismatch.\n"
            f"  Expected: {expected_hex}\n"
            f"  Actual:   {actual}\n"
            "The archive may have been tampered with or the --checksum value is wrong."
        )
    print(f"Checksum verified: {actual[:16]}...")


def safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    """Extract with zip bomb protection and path traversal guard."""
    total = 0
    for info in zf.infolist():
        # Path traversal guard
        target = (dest / info.filename).resolve()
        if not str(target).startswith(str(dest.resolve())):
            raise ValueError(f"Path traversal detected: {info.filename}")

        if info.file_size > MAX_SINGLE_FILE_BYTES:
            raise ValueError(
                f"File too large: {info.filename} ({info.file_size} bytes, max {MAX_SINGLE_FILE_BYTES})"
            )
        total += info.file_size
        if total > MAX_EXTRACTED_BYTES:
            raise ValueError(
                f"Total extracted size exceeds limit ({MAX_EXTRACTED_BYTES} bytes). Possible zip bomb."
            )
    zf.extractall(dest)


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

            if args.checksum:
                verify_checksum(archive, args.checksum)

            if args.dry_run:
                print(f"[DRY-RUN] Archive downloaded: {archive.stat().st_size:,} bytes")
                with zipfile.ZipFile(archive) as zf:
                    names = zf.namelist()
                    print(f"[DRY-RUN] Archive contains {len(names)} entries")
                    installer_names = [n for n in names if "scripts/install_codex_plugin.py" in n]
                    if installer_names:
                        checkout_name = installer_names[0].split("/")[0]
                        print(f"[DRY-RUN] Checkout: {checkout_name}/")
                    print(f"[DRY-RUN] Would extract to temp dir and run:")
                    print(f"[DRY-RUN]   python scripts/install_codex_plugin.py "
                          f"{' '.join(normalize_installer_args(args.installer_args))}")
                return 0

            with zipfile.ZipFile(archive) as zf:
                safe_extract(zf, tmp_path / "src")
            checkout = find_checkout(tmp_path / "src")
            print(f"Running Codex plugin installer from temporary checkout: {checkout.name}")
            return run_installer(checkout, args.installer_args)
    except Exception as exc:  # noqa: BLE001 - bootstrap should fail concisely
        return die(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
