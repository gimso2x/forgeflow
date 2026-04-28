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
        if command == ["git", "ls-files", "--", "adapters/generated"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(validate_generated.subprocess, "run", fake_run)

    errors = validate_generated.check_generated_outputs(ROOT)

    assert errors == []
    assert calls == [
        [sys.executable, str(ROOT / "scripts" / "generate_adapters.py")],
        ["git", "diff", "--exit-code", "--", "adapters/generated"],
        ["git", "ls-files", "--others", "--exclude-standard", "--", "adapters/generated"],
        ["git", "ls-files", "--", "adapters/generated"],
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
        if command == ["git", "ls-files", "--", "adapters/generated"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(validate_generated.subprocess, "run", fake_run)

    errors = validate_generated.check_generated_outputs(ROOT)

    assert errors == [
        "generated adapters drift from canonical sources after regeneration:\n"
        "diff --git a/adapters/generated/codex/CODEX.md b/adapters/generated/codex/CODEX.md"
    ]


def test_validate_generated_rejects_stale_tracked_generated_files_after_manifest_rename(tmp_path: Path, monkeypatch) -> None:
    validate_generated = _load_validate_generated_module()

    root = tmp_path / "repo"
    manifest = root / "adapters" / "targets" / "codex" / "manifest.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        """name: codex
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
generated_filename: CUSTOM_CODEX.md
recommended_location: ./CODEX.md
surface_style: root-instruction-file
handoff_format: artifacts-plus-git-diff
session_persistence: root instruction file persists across repo sessions until regenerated
workspace_boundary: repo root instruction file steers CLI work while emphasizing git-visible workspace changes
review_delivery: git-diff-centric summary plus artifact files checked in the repo
installation_steps:
  - Copy the generated adapter to ./CODEX.md at the repo root.
  - Preserve the canonical review order even when Codex returns git-oriented summaries.
tooling_constraints:
  - generated artifacts must not redefine canonical semantics
""",
        encoding="utf-8",
    )
    for target, filename, handoff in [
        ("claude", "CLAUDE.md", "artifacts-plus-terminal-summary"),
    ]:
        file_path = root / "adapters" / "generated" / target / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        install_1 = f"1. Copy the generated adapter to ./{filename} at the repo root." if target == "claude" else "1. Place the generated content in .codex/rules/forgeflow.mdc."
        install_2 = (
            "2. Keep Claude-specific helper notes in surrounding docs, not by changing ForgeFlow semantics."
            if target == "claude"
            else "2. Keep ForgeFlow workflow semantics in this rule file and avoid per-chat rewrites."
        )
        location = f"./{filename}" if target == "claude" else ".codex/rules/forgeflow.mdc"
        surface = "root-instruction-file" if target == "claude" else "codex-rules-markdown"
        file_path.write_text(
            "\n".join(
                [
                    "This file is generated from canonical harness policy.",
                    "Installation guidance",
                    "Target operating notes",
                    "Runtime realism contract",
                    "Non-negotiable rules",
                    "Canonical workflow snapshot",
                    "Canonical role prompts",
                    f"- generated_filename: {filename}",
                    f"- recommended_location: {location}",
                    "## Installation steps",
                    install_1,
                    install_2,
                    f"- surface_style: {surface}",
                    f"- handoff_format: {handoff}",
                    "- session_persistence: root instruction file persists across repo sessions until regenerated" if target == "claude" else "- session_persistence: rule file persists across chat sessions until regenerated",
                    "- workspace_boundary: repo root instruction file shapes CLI runs but artifacts still live in the project workspace" if target == "claude" else "- workspace_boundary: project rules live under .codex/rules and guide editor-native runs",
                    "- review_delivery: terminal-oriented summary plus artifact files checked in the repo" if target == "claude" else "- review_delivery: chat summary plus artifact file updates inside the workspace",
                    "# Coordinator" if target == "claude" else "# Planner",
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
runtime_type: {'cli-agent' if target == 'claude' else 'editor-agent'}
input_mode: {'prompt-and-files' if target == 'claude' else 'rules-and-context'}
output_mode: {'markdown-and-files' if target == 'claude' else 'files-and-chat'}
supports_roles:
  - {'coordinator' if target == 'claude' else 'planner'}
  - planner
  - worker
  - spec-reviewer
  - quality-reviewer
supports_generated_files: true
generated_filename: {filename}
recommended_location: {location}
surface_style: {surface}
handoff_format: {handoff}
session_persistence: {'rule file persists across chat sessions until regenerated' if target == 'codex' else 'root instruction file persists across repo sessions until regenerated'}
workspace_boundary: {'project rules live under .codex/rules and guide editor-native runs' if target == 'codex' else ('repo root instruction file shapes CLI runs but artifacts still live in the project workspace' if target == 'claude' else 'repo root instruction file steers CLI work while emphasizing git-visible workspace changes')}
review_delivery: {'chat summary plus artifact file updates inside the workspace' if target == 'codex' else ('terminal-oriented summary plus artifact files checked in the repo' if target == 'claude' else 'git-diff-centric summary plus artifact files checked in the repo')}
installation_steps:
  - {install_1[3:]}
  - {install_2[3:]}
tooling_constraints:

""",
            encoding="utf-8",
        )

    generated_dir = root / "adapters" / "generated" / "codex"
    generated_dir.mkdir(parents=True, exist_ok=True)
    (generated_dir / "CUSTOM_CODEX.md").write_text(
        "\n".join(
            [
                "This file is generated from canonical harness policy.",
                "Installation guidance",
                "Target operating notes",
                "Runtime realism contract",
                "Non-negotiable rules",
                "Canonical workflow snapshot",
                "Canonical role prompts",
                "- generated_filename: CUSTOM_CODEX.md",
                "- recommended_location: ./CODEX.md",
                "## Installation steps",
                "1. Copy the generated adapter to ./CODEX.md at the repo root.",
                "2. Preserve the canonical review order even when Codex returns git-oriented summaries.",
                "- surface_style: root-instruction-file",
                "- handoff_format: artifacts-plus-git-diff",
                "- session_persistence: root instruction file persists across repo sessions until regenerated",
                "- workspace_boundary: repo root instruction file steers CLI work while emphasizing git-visible workspace changes",
                "- review_delivery: git-diff-centric summary plus artifact files checked in the repo",
                "# Coordinator",
                "# Planner",
                "# Worker",
                "# Spec Reviewer",
                "# Quality Reviewer",
            ]
        ),
        encoding="utf-8",
    )
    (generated_dir / "CODEX.md").write_text("stale tracked file\n", encoding="utf-8")

    def fake_run(command, cwd=None, capture_output=None, text=None):
        if command[:2] == [sys.executable, str(root / "scripts" / "generate_adapters.py")]:
            return subprocess.CompletedProcess(command, 0, stdout="ADAPTER GENERATION: PASS\n", stderr="")
        if command[:3] == ["git", "diff", "--exit-code"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command[:3] == ["git", "ls-files", "--others"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command == ["git", "ls-files", "--", "adapters/generated"]:
            return subprocess.CompletedProcess(command, 0, stdout="adapters/generated/codex/CODEX.md\nadapters/generated/codex/CUSTOM_CODEX.md\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(validate_generated.subprocess, "run", fake_run)
    monkeypatch.setattr(validate_generated, "REQUIRED_GENERATED", {"claude": "CLAUDE.md", "codex": "CUSTOM_CODEX.md"})

    errors = validate_generated.check_generated_outputs(root)

    assert errors == ["stale generated file tracked outside canonical manifest set: adapters/generated/codex/CODEX.md"]


def test_validate_generated_rejects_stale_tracked_generated_files_for_removed_target(tmp_path: Path, monkeypatch) -> None:
    validate_generated = _load_validate_generated_module()

    root = tmp_path / "repo"
    for target, filename, handoff in [
        ("claude", "CLAUDE.md", "artifacts-plus-terminal-summary"),
        ("codex", "HARNESS_CODEX.md", "artifacts-plus-chat-summary"),
    ]:
        file_path = root / "adapters" / "generated" / target / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        install_1 = f"1. Copy the generated adapter to ./{filename} at the repo root." if target != "codex" else "1. Place the generated content in .codex/rules/forgeflow.mdc."
        install_2 = (
            f"2. Preserve the canonical review order even when {target.capitalize()} returns specialized summaries."
            if target != "codex"
            else "2. Keep ForgeFlow workflow semantics in this rule file and avoid per-chat rewrites."
        )
        location = f"./{filename}" if target != "codex" else ".codex/rules/forgeflow.mdc"
        surface = "root-instruction-file" if target != "codex" else "codex-rules-markdown"
        roles = ["# Planner", "# Worker", "# Spec Reviewer", "# Quality Reviewer"]
        if target != "codex":
            roles.insert(0, "# Coordinator")
        file_path.write_text(
            "\n".join(
                [
                    "This file is generated from canonical harness policy.",
                    "Installation guidance",
                    "Target operating notes",
                    "Runtime realism contract",
                    "Non-negotiable rules",
                    "Canonical workflow snapshot",
                    "Canonical role prompts",
                    f"- generated_filename: {filename}",
                    f"- recommended_location: {location}",
                    "## Installation steps",
                    install_1,
                    install_2,
                    f"- surface_style: {surface}",
                    f"- handoff_format: {handoff}",
                    "- session_persistence: rule file persists across chat sessions until regenerated" if target == "codex" else "- session_persistence: root instruction file persists across repo sessions until regenerated",
                    "- workspace_boundary: project rules live under .codex/rules and guide editor-native runs" if target == "codex" else ("- workspace_boundary: repo root instruction file shapes CLI runs but artifacts still live in the project workspace" if target == "claude" else "- workspace_boundary: repo root instruction file steers CLI work while emphasizing git-visible workspace changes"),
                    "- review_delivery: chat summary plus artifact file updates inside the workspace" if target == "codex" else ("- review_delivery: terminal-oriented summary plus artifact files checked in the repo" if target == "claude" else "- review_delivery: git-diff-centric summary plus artifact files checked in the repo"),
                    *roles,
                ]
            ),
            encoding="utf-8",
        )
        manifest_path = root / "adapters" / "targets" / target / "manifest.yaml"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            f"""name: {target}
runtime_type: {'editor-agent' if target == 'codex' else 'cli-agent'}
input_mode: {'rules-and-context' if target == 'codex' else 'prompt-and-files'}
output_mode: {'files-and-chat' if target == 'codex' else 'markdown-and-files'}
supports_roles:
  - {'planner' if target == 'codex' else 'coordinator'}
  - planner
  - worker
  - spec-reviewer
  - quality-reviewer
supports_generated_files: true
generated_filename: {filename}
recommended_location: {location}
surface_style: {surface}
handoff_format: {handoff}
session_persistence: {'rule file persists across chat sessions until regenerated' if target == 'codex' else 'root instruction file persists across repo sessions until regenerated'}
workspace_boundary: {'project rules live under .codex/rules and guide editor-native runs' if target == 'codex' else ('repo root instruction file shapes CLI runs but artifacts still live in the project workspace' if target == 'claude' else 'repo root instruction file steers CLI work while emphasizing git-visible workspace changes')}
review_delivery: {'chat summary plus artifact file updates inside the workspace' if target == 'codex' else ('terminal-oriented summary plus artifact files checked in the repo' if target == 'claude' else 'git-diff-centric summary plus artifact files checked in the repo')}
installation_steps:
  - {install_1[3:]}
  - {install_2[3:]}
tooling_constraints:

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
        if command == ["git", "ls-files", "--", "adapters/generated"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="adapters/generated/claude/CLAUDE.md\nadapters/generated/codex/HARNESS_CODEX.md\nadapters/generated/retired/LEGACY.md\n",
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(validate_generated.subprocess, "run", fake_run)

    errors = validate_generated.check_generated_outputs(root)

    assert errors == ["stale generated file tracked outside canonical manifest set: adapters/generated/retired/LEGACY.md"]


def test_validate_generated_reports_untracked_file_lookup_failure(monkeypatch) -> None:
    validate_generated = _load_validate_generated_module()

    def fake_run(command, cwd=None, capture_output=None, text=None):
        if command[:2] == [sys.executable, str(ROOT / "scripts" / "generate_adapters.py")]:
            return subprocess.CompletedProcess(command, 0, stdout="ADAPTER GENERATION: PASS\n", stderr="")
        if command[:3] == ["git", "diff", "--exit-code"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command[:3] == ["git", "ls-files", "--others"]:
            return subprocess.CompletedProcess(command, 128, stdout="", stderr="fatal: not a git repository")
        if command == ["git", "ls-files", "--", "adapters/generated"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(validate_generated.subprocess, "run", fake_run)

    errors = validate_generated.check_generated_outputs(ROOT)

    assert errors == ["generator untracked-file lookup failed", "fatal: not a git repository"]


def test_validate_generated_reports_tracked_file_lookup_failure(monkeypatch) -> None:
    validate_generated = _load_validate_generated_module()

    def fake_run(command, cwd=None, capture_output=None, text=None):
        if command[:2] == [sys.executable, str(ROOT / "scripts" / "generate_adapters.py")]:
            return subprocess.CompletedProcess(command, 0, stdout="ADAPTER GENERATION: PASS\n", stderr="")
        if command[:3] == ["git", "diff", "--exit-code"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command[:3] == ["git", "ls-files", "--others"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command == ["git", "ls-files", "--", "adapters/generated"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="fatal: not a git repository")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(validate_generated.subprocess, "run", fake_run)

    errors = validate_generated.check_generated_outputs(ROOT)

    assert errors == ["generator tracked-file lookup failed", "fatal: not a git repository"]


def test_validate_generated_derives_expected_output_path_from_manifest(tmp_path: Path, monkeypatch) -> None:
    validate_generated = _load_validate_generated_module()

    root = tmp_path / "repo"
    generated_file = root / "adapters" / "generated" / "codex" / "CUSTOM_CODEX.md"
    generated_file.parent.mkdir(parents=True)
    generated_file.write_text(
        "\n".join(
            [
                "This file is generated from canonical harness policy.",
                "Installation guidance",
                "Target operating notes",
                "Runtime realism contract",
                "Non-negotiable rules",
                "Canonical workflow snapshot",
                "Canonical role prompts",
                "- generated_filename: CUSTOM_CODEX.md",
                "- recommended_location: .codex/rules/forgeflow.mdc",
                "## Installation steps",
                "1. Place the generated content in .codex/rules/forgeflow.mdc.",
                "2. Keep ForgeFlow workflow semantics in this rule file and avoid per-chat rewrites.",
                "- surface_style: codex-rules-markdown",
                "- handoff_format: artifacts-plus-chat-summary",
                "- session_persistence: rule file persists across chat sessions until regenerated",
                "- workspace_boundary: project rules live under .codex/rules and guide editor-native runs",
                "- review_delivery: chat summary plus artifact file updates inside the workspace",
                "# Planner",
                "# Worker",
                "# Spec Reviewer",
                "# Quality Reviewer",
            ]
        ),
        encoding="utf-8",
    )
    manifest = root / "adapters" / "targets" / "codex" / "manifest.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """name: codex
runtime_type: editor-agent
input_mode: rules-and-context
output_mode: files-and-chat
supports_roles:
  - planner
  - worker
  - spec-reviewer
  - quality-reviewer
supports_generated_files: true
generated_filename: CUSTOM_CODEX.md
recommended_location: .codex/rules/forgeflow.mdc
surface_style: codex-rules-markdown
handoff_format: artifacts-plus-chat-summary
session_persistence: rule file persists across chat sessions until regenerated
workspace_boundary: project rules live under .codex/rules and guide editor-native runs
review_delivery: chat summary plus artifact file updates inside the workspace
installation_steps:
  - Place the generated content in .codex/rules/forgeflow.mdc.
  - Keep ForgeFlow workflow semantics in this rule file and avoid per-chat rewrites.
tooling_constraints:
  - rules surface may require .mdc or codex-specific placement
  - generated artifacts must not redefine canonical semantics
""",
        encoding="utf-8",
    )
    for target, filename in {"claude": "CLAUDE.md", "codex": "CODEX.md"}.items():
        file_path = root / "adapters" / "generated" / target / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        handoff = "artifacts-plus-terminal-summary" if target == "claude" else "artifacts-plus-git-diff"
        workspace_boundary = (
            "repo root instruction file shapes CLI runs but artifacts still live in the project workspace"
            if target == "claude"
            else "repo root instruction file steers CLI work while emphasizing git-visible workspace changes"
        )
        review_delivery = (
            "terminal-oriented summary plus artifact files checked in the repo"
            if target == "claude"
            else "git-diff-centric summary plus artifact files checked in the repo"
        )
        file_path.write_text(
            "\n".join(
                [
                    "This file is generated from canonical harness policy.",
                    "Installation guidance",
                    "Target operating notes",
                    "Runtime realism contract",
                    "Non-negotiable rules",
                    "Canonical workflow snapshot",
                    "Canonical role prompts",
                    f"- generated_filename: {filename}",
                    f"- recommended_location: ./{filename}",
                    "## Installation steps",
                    f"1. Copy the generated adapter to ./{filename} at the repo root.",
                    f"2. Preserve the canonical review order even when {target.capitalize()} returns specialized summaries.",
                    "- surface_style: root-instruction-file",
                    f"- handoff_format: {handoff}",
                    "- session_persistence: root instruction file persists across repo sessions until regenerated",
                    f"- workspace_boundary: {workspace_boundary}",
                    f"- review_delivery: {review_delivery}",
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
session_persistence: root instruction file persists across repo sessions until regenerated
workspace_boundary: {workspace_boundary}
review_delivery: {review_delivery}
installation_steps:
  - Copy the generated adapter to ./{filename} at the repo root.
  - Preserve the canonical review order even when {target.capitalize()} returns specialized summaries.
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
        if command == ["git", "ls-files", "--", "adapters/generated"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(validate_generated.subprocess, "run", fake_run)
    monkeypatch.setattr(validate_generated, "REQUIRED_GENERATED", {"claude": "CLAUDE.md", "codex": "CODEX.md", "codex": "HARNESS_CODEX.md"})

    errors = validate_generated.check_generated_outputs(root)

    assert errors == []


