from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "adapters" / "targets" / "claude" / "hooks"


def run_hook(name: str, payload: dict, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["python3", str(HOOKS / name)],
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=merged_env,
        timeout=10,
        check=False,
    )


def hook_context(result: subprocess.CompletedProcess[str]) -> str:
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    return data["hookSpecificOutput"]["additionalContext"]


def test_edit_error_recovery_guides_old_string_not_found() -> None:
    result = run_hook(
        "edit_error_recovery.py",
        {"tool_name": "Edit", "error": "old_string not found in file", "tool_input": {"file_path": "README.md"}},
    )

    context = hook_context(result)
    assert "EDIT RECOVERY" in context
    assert "re-read the file" in context


def test_large_file_recovery_guides_read_size_limit() -> None:
    result = run_hook(
        "large_file_recovery.py",
        {"tool_name": "Read", "error": "content too large; exceeds size limit", "tool_input": {"file_path": "big.log"}},
    )

    context = hook_context(result)
    assert "LARGE FILE RECOVERY" in context
    assert "big.log" in context


def test_tool_failure_tracker_escalates_on_third_failure(tmp_path: Path) -> None:
    payload = {"tool_name": "Edit", "session_id": "session-1", "error": "failed"}
    env = {"CLAUDE_PROJECT_DIR": str(tmp_path)}

    first = run_hook("tool_failure_tracker.py", payload, env=env)
    second = run_hook("tool_failure_tracker.py", payload, env=env)
    third = run_hook("tool_failure_tracker.py", payload, env=env)

    assert first.returncode == 0 and first.stdout.strip() == ""
    assert second.returncode == 0 and second.stdout.strip() == ""
    context = hook_context(third)
    assert "REPEATED FAILURE" in context
    assert "Edit" in context


def test_tool_output_truncator_limits_large_output_and_preserves_errors() -> None:
    output = "A" * 60000 + "\nTraceback: important failure\n" + "B" * 6000
    result = run_hook("tool_output_truncator.py", {"tool_name": "Bash", "tool_response": output})

    context = hook_context(result)
    assert "Tool output was truncated" in context
    assert "TRUNCATED" in context
    assert "Traceback: important failure" in context


def test_hook_manifest_references_existing_scripts() -> None:
    manifest = json.loads((HOOKS / "hooks.json").read_text())
    commands: list[str] = []
    for groups in manifest["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                commands.append(hook["command"])
    assert commands
    for command in commands:
        assert command.startswith("${CLAUDE_PLUGIN_ROOT}/hooks/")
        script = command.rsplit("/", 1)[-1]
        assert (HOOKS / script).is_file(), script
