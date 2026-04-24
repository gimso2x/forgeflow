#!/usr/bin/env python3
"""ForgeFlow project-local basic safety guard for Claude Code Bash calls."""

from __future__ import annotations

import json
import re
import sys

DANGEROUS_PATTERNS = [
    (re.compile(r"\brm\s+[^\n;]*-[^\n;]*[rR][^\n;]*[fF]|\brm\s+[^\n;]*-[^\n;]*[fF][^\n;]*[rR]"), "recursive force removal"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "hard git reset"),
    (re.compile(r"\bgit\s+push\b[^\n;]*\s--force(?:-with-lease)?\b"), "force push"),
    (re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE), "destructive SQL"),
]


def load_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def main() -> int:
    payload = load_payload()
    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = str(tool_input.get("command") or "")
    for pattern, reason in DANGEROUS_PATTERNS:
        if pattern.search(command):
            print(
                "FORGEFLOW BASIC SAFETY: blocked Bash command "
                f"because it looks like {reason}. This project-local hook is a guardrail, "
                "not a complete sandbox. If this is intentional, perform the action manually "
                "after reviewing scope and dirty working tree state.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
