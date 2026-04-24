import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "adapters" / "targets" / "claude" / "hook-bundles" / "basic-safety" / "basic_safety_guard.py"


def run_hook(payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def test_basic_safety_hook_blocks_destructive_bash_command():
    result = run_hook({"tool_name": "Bash", "tool_input": {"command": "rm -rf node_modules"}})

    assert result.returncode == 2
    assert "FORGEFLOW BASIC SAFETY" in result.stderr


def test_basic_safety_hook_allows_normal_bash_command():
    result = run_hook({"tool_name": "Bash", "tool_input": {"command": "npm run test"}})

    assert result.returncode == 0
    assert result.stderr == ""


def test_basic_safety_hook_ignores_non_bash_tools():
    result = run_hook({"tool_name": "Read", "tool_input": {"file_path": "README.md"}})

    assert result.returncode == 0
