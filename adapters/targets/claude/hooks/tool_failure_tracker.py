#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

WINDOW_SECONDS = 60


def emit(context: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUseFailure", "additionalContext": context}}))


def state_dir(session_id: str) -> Path:
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if project:
        return Path(project) / ".forgeflow" / "claude-hook-state" / session_id
    return Path.home() / ".forgeflow" / "claude-hook-state" / session_id


def main() -> int:
    payload = json.load(sys.stdin)
    tool_name = str(payload.get("tool_name") or "")
    session_id = str(payload.get("session_id") or "")
    if not tool_name or not session_id:
        return 0
    directory = state_dir(session_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "failure-counts.json"
    now = int(time.time())
    if path.is_file():
        state = json.loads(path.read_text(encoding="utf-8"))
    else:
        state = {"failures": []}
    failures = [item for item in state.get("failures", []) if int(item.get("ts", 0)) >= now - WINDOW_SECONDS]
    failures.append({"tool": tool_name, "ts": now})
    path.write_text(json.dumps({"failures": failures}, indent=2), encoding="utf-8")
    count = sum(1 for item in failures if item.get("tool") == tool_name)
    if count >= 5:
        emit(f"STAGNATION DETECTED: The {tool_name} tool has failed {count} times in the last 60 seconds. STOP and switch strategy: re-read state, narrow scope, or report the blocker.")
    elif count >= 3:
        emit(f"REPEATED FAILURE: {tool_name} has failed {count} times recently. Re-read current state and try a different approach before retrying.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
