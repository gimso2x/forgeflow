import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_STRUCTURE_PATH = ROOT / "scripts" / "validate_structure.py"


def _load_validate_structure_module():
    spec = importlib.util.spec_from_file_location("validate_structure", VALIDATE_STRUCTURE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validate_structure_tracks_runtime_and_memory_scaffold() -> None:
    validate_structure = _load_validate_structure_module()
    for rel in [
        "runtime/orchestrator",
        "runtime/ledger",
        "runtime/gates",
        "runtime/recovery",
        "memory/patterns",
        "memory/decisions",
    ]:
        assert rel in validate_structure.REQUIRED_DIRS

    for rel in [
        "runtime/README.md",
        "runtime/orchestrator/README.md",
        "runtime/ledger/README.md",
        "runtime/gates/README.md",
        "runtime/recovery/README.md",
        "memory/README.md",
        "memory/patterns/README.md",
        "memory/decisions/README.md",
    ]:
        assert rel in validate_structure.REQUIRED_FILES

    for rel in [
        "schemas/policy/workflow.schema.json",
        "schemas/policy/stages.schema.json",
        "schemas/policy/gates.schema.json",
        "schemas/policy/complexity-routing.schema.json",
    ]:
        assert rel in validate_structure.REQUIRED_FILES

    result = subprocess.run(
        [sys.executable, "scripts/validate_structure.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "STRUCTURE VALIDATION: PASS" in result.stdout


def test_validate_workflow_installs_policy_validator_dependencies() -> None:
    workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8").lower()

    assert "jsonschema" in workflow
    assert "pyyaml" in workflow
