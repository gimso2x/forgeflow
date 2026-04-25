from __future__ import annotations

import json
from pathlib import Path

from forgeflow_runtime.evolution import dry_run_rule


ROOT = Path(__file__).resolve().parents[2]


def test_generated_adapter_drift_command_uses_non_mutating_check() -> None:
    script = (ROOT / "scripts" / "generate_adapters.py").read_text(encoding="utf-8")
    commands = (ROOT / "forgeflow_runtime" / "evolution_execution.py").read_text(encoding="utf-8")

    assert "--check" in script
    assert "out_file.write_text" in script
    assert "if args.check" in script
    assert '[sys.executable, "scripts/generate_adapters.py", "--check"]' in commands


def test_dry_run_rule_rejects_project_rule_with_mismatched_command_contract(tmp_path: Path) -> None:
    project_rule_dir = tmp_path / ".forgeflow" / "evolution" / "rules"
    project_rule_dir.mkdir(parents=True)
    rule = json.loads((ROOT / "examples" / "evolution" / "no-env-commit-rule.json").read_text(encoding="utf-8"))
    rule["check"]["command"] = "echo totally different preview"
    (project_rule_dir / "no-env-commit-rule.json").write_text(json.dumps(rule), encoding="utf-8")

    result = dry_run_rule(tmp_path, "no-env-commit", allow_examples=False)

    assert result["safe_to_execute_later"] is False
    assert result["safety_checks"]["approved_command"] is True
    assert result["safety_checks"]["approved_command_contract"] is False


def test_generated_adapter_drift_example_previews_non_mutating_check_command() -> None:
    rule = json.loads((ROOT / "examples" / "evolution" / "generated-adapter-drift-rule.json").read_text(encoding="utf-8"))

    assert rule["check"]["command"] == "python3 scripts/generate_adapters.py --check"


def test_generated_adapter_drift_execute_has_no_hidden_git_diff_contract() -> None:
    commands = (ROOT / "forgeflow_runtime" / "evolution_execution.py").read_text(encoding="utf-8")
    block = commands.split('if command_id == "generated-adapter-drift":', 1)[1].split('raise ValueError', 1)[0]

    assert '[sys.executable, "scripts/generate_adapters.py", "--check"]' in block
    assert 'git", "diff"' not in block
    assert 'adapters/generated' not in block
