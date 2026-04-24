#!/usr/bin/env python3
"""Compatibility wrapper for installing Claude ForgeFlow presets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from install_agent_presets import install  # noqa: E402


def die(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Project root to install into")
    parser.add_argument("--profile", choices=["nextjs"], default="nextjs")
    args = parser.parse_args(argv)

    try:
        target, copied, doc, _starter_docs, _hook_bundles = install(args.target, "claude", args.profile)
    except Exception as exc:  # noqa: BLE001 - CLI reports concise failure
        return die(str(exc))

    print(f"Installed {len(copied)} Claude agent presets into {target / '.claude/agents'}")
    print(f"Wrote {doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
