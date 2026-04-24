#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys


def emit(context: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUseFailure", "additionalContext": context}}))


def main() -> int:
    payload = json.load(sys.stdin)
    if payload.get("tool_name") not in {"Edit", "Write"}:
        return 0
    error = str(payload.get("error") or "")
    if not error:
        return 0
    patterns = [
        (r"old_string.*not found|oldString.*not found|not found in file|does not contain", "EDIT RECOVERY: The old_string was not found in the file. REQUIRED: re-read the file now, then retry with the exact current content, including indentation and line endings."),
        (r"found multiple|multiple matches|not unique|ambiguous", "EDIT RECOVERY: The old_string matched multiple locations. REQUIRED: include more surrounding context, or use replace_all only if every occurrence should change."),
        (r"old_string and new_string.*same|must be different|identical", "EDIT RECOVERY: old_string and new_string are identical. Verify the replacement differs before retrying."),
        (r"file.*not found|no such file|ENOENT", "EDIT RECOVERY: The target file does not exist. Verify the path before retrying."),
        (r"permission|EACCES|read.only", "EDIT RECOVERY: Permission denied. Check file permissions or protected directory boundaries."),
    ]
    for pattern, guidance in patterns:
        if re.search(pattern, error, flags=re.IGNORECASE):
            emit(guidance)
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
