import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_GENERATED_PATH = ROOT / "scripts" / "validate_generated.py"


def _load_validate_generated_module():
    spec = importlib.util.spec_from_file_location("validate_generated", VALIDATE_GENERATED_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validate_generated_passes_when_generator_and_git_diff_are_clean(monkeypatch) -> None:
    validate_generated = _load_validate_generated_module()
    calls = []

    def fake_run(command, cwd=None, capture_output=None, text=None):
        calls.append(command)
        if command[:2] == [sys.executable, str(ROOT / "scripts" / "generate_adapters.py")]:
            return subprocess.CompletedProcess(command, 0, stdout="ADAPTER GENERATION: PASS\n", stderr="")
        if command[:3] == ["git", "diff", "--exit-code"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command[:3] == ["git", "ls-files", "--others"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(validate_generated.subprocess, "run", fake_run)

    errors = validate_generated.check_generated_outputs(ROOT)

    assert errors == []
    assert [command[:3] for command in calls] == [
        [sys.executable, str(ROOT / "scripts" / "generate_adapters.py")],
        ["git", "diff", "--exit-code"],
        ["git", "ls-files", "--others"],
    ]


def test_validate_generated_reports_git_diff_drift(monkeypatch) -> None:
    validate_generated = _load_validate_generated_module()

    def fake_run(command, cwd=None, capture_output=None, text=None):
        if command[:2] == [sys.executable, str(ROOT / "scripts" / "generate_adapters.py")]:
            return subprocess.CompletedProcess(command, 0, stdout="ADAPTER GENERATION: PASS\n", stderr="")
        if command[:3] == ["git", "diff", "--exit-code"]:
            return subprocess.CompletedProcess(command, 1, stdout="diff --git a/adapters/generated/codex/CODEX.md b/adapters/generated/codex/CODEX.md\n", stderr="")
        if command[:3] == ["git", "ls-files", "--others"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(validate_generated.subprocess, "run", fake_run)

    errors = validate_generated.check_generated_outputs(ROOT)

    assert errors == [
        "generated adapters drift from canonical sources after regeneration:\n"
        "diff --git a/adapters/generated/codex/CODEX.md b/adapters/generated/codex/CODEX.md"
    ]


def test_validate_generated_reports_untracked_generated_files(monkeypatch) -> None:
    validate_generated = _load_validate_generated_module()

    def fake_run(command, cwd=None, capture_output=None, text=None):
        if command[:2] == [sys.executable, str(ROOT / "scripts" / "generate_adapters.py")]:
            return subprocess.CompletedProcess(command, 0, stdout="ADAPTER GENERATION: PASS\n", stderr="")
        if command[:3] == ["git", "diff", "--exit-code"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command[:3] == ["git", "ls-files", "--others"]:
            return subprocess.CompletedProcess(command, 0, stdout="adapters/generated/gemini/GEMINI.md\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(validate_generated.subprocess, "run", fake_run)

    errors = validate_generated.check_generated_outputs(ROOT)

    assert errors == [
        "generated adapters drift from canonical sources after regeneration:\n"
        "untracked files:\nadapters/generated/gemini/GEMINI.md"
    ]
