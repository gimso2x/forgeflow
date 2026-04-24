#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys

LIMITS = {"Grep": 50_000, "Glob": 50_000, "Bash": 50_000, "WebFetch": 10_000}
ERROR_RE = re.compile(r"(Error|error|Traceback|traceback|Exception|exception|WARN|WARNING|at [a-zA-Z])")


def emit(context: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}}))


def main() -> int:
    payload = json.load(sys.stdin)
    tool_name = str(payload.get("tool_name") or "")
    limit = LIMITS.get(tool_name)
    if limit is None:
        return 0
    output = str(payload.get("tool_response") or "")
    if len(output) <= limit:
        return 0
    head_keep = min(15_000, len(output))
    tail_keep = min(5_000, max(0, len(output) - head_keep))
    removed = max(0, len(output) - head_keep - tail_keep)
    head = output[:head_keep]
    tail = output[-tail_keep:] if tail_keep else ""
    error_lines = "\n".join(line for line in output.splitlines() if ERROR_RE.search(line))
    truncated = f"{head}\n\n... [TRUNCATED: {removed} chars removed] ...\n\n{tail}"
    if error_lines and error_lines not in truncated:
        truncated += "\n\n--- [PRESERVED STDERR/ERROR LINES] ---\n" + error_lines[:20_000]
    emit(f"Tool output was truncated from {len(output)} chars to fit context limits.\n\nTruncated output:\n{truncated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
