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


def test_validate_generated_derives_expected_output_path_from_manifest(tmp_path: Path, monkeypatch) -> None:
    validate_generated = _load_validate_generated_module()

    root = tmp_path / "repo"
    generated_file = root / "adapters" / "generated" / "cursor" / "CUSTOM_CURSOR.md"
    generated_file.parent.mkdir(parents=True)
    generated_file.write_text(
        "\n".join(
            [
                "This file is generated from canonical harness policy.",
                "Installation guidance",
                "Target operating notes",
                "Non-negotiable rules",
                "Canonical workflow snapshot",
                "Canonical role prompts",
                "- generated_filename: CUSTOM_CURSOR.md",
                "- recommended_location: .cursor/rules/forgeflow.mdc",
                "- surface_style: cursor-rules-markdown",
                "- handoff_format: artifacts-plus-chat-summary",
                "# Planner",
                "# Worker",
                "# Spec Reviewer",
                "# Quality Reviewer",
            ]
        ),
        encoding="utf-8",
    )
    manifest = root / "adapters" / "targets" / "cursor" / "manifest.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """name: cursor
runtime_type: editor-agent
input_mode: rules-and-context
output_mode: files-and-chat
supports_roles:
  - planner
  - worker
  - spec-reviewer
  - quality-reviewer
supports_generated_files: true
generated_filename: CUSTOM_CURSOR.md
recommended_location: .cursor/rules/forgeflow.mdc
surface_style: cursor-rules-markdown
handoff_format: artifacts-plus-chat-summary
tooling_constraints:
  - rules surface may require .mdc or cursor-specific placement
  - generated artifacts must not redefine canonical semantics
""",
        encoding="utf-8",
    )
    for target, filename in {"claude": "CLAUDE.md", "codex": "CODEX.md"}.items():
        file_path = root / "adapters" / "generated" / target / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        handoff = "artifacts-plus-terminal-summary" if target == "claude" else "artifacts-plus-git-diff"
        file_path.write_text(
            "\n".join(
                [
                    "This file is generated from canonical harness policy.",
                    "Installation guidance",
                    "Target operating notes",
                    "Non-negotiable rules",
                    "Canonical workflow snapshot",
                    "Canonical role prompts",
                    f"- generated_filename: {filename}",
                    f"- recommended_location: ./{filename}",
                    "- surface_style: root-instruction-file",
                    f"- handoff_format: {handoff}",
                    "# Coordinator",
                    "# Planner",
                    "# Worker",
                    "# Spec Reviewer",
                    "# Quality Reviewer",
                ]
            ),
            encoding="utf-8",
        )
        (root / "adapters" / "targets" / target).mkdir(parents=True, exist_ok=True)
        (root / "adapters" / "targets" / target / "manifest.yaml").write_text(
            f"""name: {target}
runtime_type: cli-agent
input_mode: prompt-and-files
output_mode: markdown-and-files
supports_roles:
  - coordinator
  - planner
  - worker
  - spec-reviewer
  - quality-reviewer
supports_generated_files: true
generated_filename: {filename}
recommended_location: ./{filename}
surface_style: root-instruction-file
handoff_format: {handoff}
tooling_constraints:
  - generated artifacts must not redefine canonical semantics
""",
            encoding="utf-8",
        )

    def fake_run(command, cwd=None, capture_output=None, text=None):
        if command[:2] == [sys.executable, str(root / "scripts" / "generate_adapters.py")]:
            return subprocess.CompletedProcess(command, 0, stdout="ADAPTER GENERATION: PASS\n", stderr="")
        if command[:3] == ["git", "diff", "--exit-code"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command[:3] == ["git", "ls-files", "--others"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(validate_generated.subprocess, "run", fake_run)
    monkeypatch.setattr(validate_generated, "REQUIRED_GENERATED", {"claude": "CLAUDE.md", "codex": "CODEX.md", "cursor": "HARNESS_CURSOR.md"})

    errors = validate_generated.check_generated_outputs(root)

    assert errors == []


