import json
import os
from pathlib import Path

from tests.runtime.cli_helpers import ROOT, make_task_dir, run_orchestrator_cli


_make_task_dir = make_task_dir
_run_orchestrator_cli = run_orchestrator_cli


def test_cli_execute_real_codex_uses_binary_from_path_without_live_credentials(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    codex.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "assert sys.argv[1] == 'exec'\n"
        "print('FAKE_CODEX_REAL_OUTPUT')\n",
        encoding="utf-8",
    )
    codex.chmod(0o755)

    result = _run_orchestrator_cli(
        "execute",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--adapter",
        "codex",
        "--real",
        env={"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"},
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert payload["adapter"] == "codex"
    assert (task_dir / "clarify-output.md").read_text(encoding="utf-8").strip() == "FAKE_CODEX_REAL_OUTPUT"


def test_cli_execute_real_claude_uses_binary_from_path_without_live_credentials(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    claude.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "assert '-p' in sys.argv\n"
        "assert '--bare' in sys.argv\n"
        "assert '--dangerously-skip-permissions' in sys.argv\n"
        "print('FAKE_CLAUDE_REAL_OUTPUT')\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)

    result = _run_orchestrator_cli(
        "execute",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--adapter",
        "claude",
        "--real",
        env={"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"},
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert payload["adapter"] == "claude"
    assert payload["execution_mode"] == "real"
    assert (task_dir / "clarify-output.md").read_text(encoding="utf-8").strip() == "FAKE_CLAUDE_REAL_OUTPUT"


def test_cli_execute_real_unsupported_adapter_fails_explicitly(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    result = _run_orchestrator_cli(
        "execute",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--adapter",
        "cursor",
        "--real",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert payload["error"] == "real adapter unsupported: cursor; supported real adapters: claude, codex"


def test_cli_execute_real_codex_missing_binary_is_actionable(tmp_path: Path) -> None:
    task_dir = _make_task_dir(tmp_path)

    result = _run_orchestrator_cli(
        "execute",
        "--task-dir",
        str(task_dir),
        "--route",
        "small",
        "--adapter",
        "codex",
        "--real",
        env={"PATH": str(tmp_path / "empty-bin")},
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failure"
    assert payload["error"] == "codex binary not found on PATH; install/auth Codex CLI or omit --real to use the safe stub"


def test_real_adapter_boundary_doc_defines_supported_slice_and_failure_modes() -> None:
    doc = (ROOT / "docs" / "real-adapter-boundary.md").read_text(encoding="utf-8")

    assert "Supported real execution slice" in doc
    assert "Claude Code and Codex CLI" in doc
    assert "Stub execution remains the default" in doc
    assert "missing CLI" in doc
    assert "auth failure" in doc
    assert "non-zero exit" in doc
    assert "malformed output" in doc


