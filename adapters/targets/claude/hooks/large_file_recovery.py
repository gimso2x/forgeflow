#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys


def emit(context: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUseFailure", "additionalContext": context}}))


def main() -> int:
    payload = json.load(sys.stdin)
    if payload.get("tool_name") != "Read":
        return 0
    error = str(payload.get("error") or "")
    file_path = ((payload.get("tool_input") or {}).get("file_path") or "<unknown>")
    if re.search(r"too large|too big|size limit|exceeds.*limit|maximum.*size|file is too long|content too large", error, re.IGNORECASE):
        emit(f"LARGE FILE RECOVERY: '{file_path}' is too large to read directly. Use chunked reads, targeted search, or a code-explorer subagent focused on the exact question.")
    elif re.search(r"binary|not a text|encoding", error, re.IGNORECASE):
        emit(f"BINARY FILE: '{file_path}' appears to be binary or non-text. Check file type before attempting text reads.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
