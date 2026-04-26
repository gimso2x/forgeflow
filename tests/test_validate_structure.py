import ast
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

    assert "docs/contract-map.md" in validate_structure.REQUIRED_FILES

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
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8").lower()

    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()

    assert "run: make setup" in workflow
    assert "run: make check-env" in workflow
    assert "-r requirements.txt" in makefile
    assert "jsonschema" in requirements
    assert "pyyaml" in requirements
    assert "pytest" in requirements


def test_contract_map_names_evolution_rule_contract_surface() -> None:
    contract_map = (ROOT / "docs" / "contract-map.md").read_text(encoding="utf-8")

    for required_text in [
        "`examples/evolution/*`",
        "`schemas/evolution-rule.schema.json`",
        "python3 scripts/validate_policy.py",
        "project-local evolution rule lifecycle",
    ]:
        assert required_text in contract_map


def test_contract_map_names_generated_adapter_boundary() -> None:
    contract_map = (ROOT / "docs" / "contract-map.md").read_text(encoding="utf-8")

    for required_text in [
        "generated adapter source/generated boundary",
        "`adapters/targets/*`",
        "`adapters/generated/*`",
        "python3 scripts/generate_adapters.py",
        "python3 scripts/validate_generated.py",
    ]:
        assert required_text in contract_map


def test_contract_map_names_runtime_seam_boundaries() -> None:
    contract_map = (ROOT / "docs" / "contract-map.md").read_text(encoding="utf-8")

    for required_text in [
        "Runtime seam boundaries",
        "`forgeflow_runtime/gate_evaluation.py`",
        "`forgeflow_runtime/resume_validation.py`",
        "`forgeflow_runtime/artifact_validation.py`",
        "`forgeflow_runtime/task_identity.py`",
        "`forgeflow_runtime/plan_ledger.py`",
        "`forgeflow_runtime/stage_transition.py`",
        "`forgeflow_runtime/route_execution.py`",
        "python -m pytest tests/runtime -q",
    ]:
        assert required_text in contract_map


def test_contract_map_names_schema_version_migration_seam() -> None:
    contract_map = (ROOT / "docs" / "contract-map.md").read_text(encoding="utf-8")

    for required_text in [
        "`schemas/*.schema.json`",
        "`forgeflow_runtime/schema_versions.py`",
        "current supported artifact version",
        "future migration hook seam",
    ]:
        assert required_text in contract_map


def test_contract_map_names_script_runtime_boundary() -> None:
    contract_map = (ROOT / "docs" / "contract-map.md").read_text(encoding="utf-8")

    for required_text in [
        "Script/runtime boundary",
        "`scripts/*.py`",
        "Thin command-line and validation entrypoints",
        "reusable behavior lives in `forgeflow_runtime/`",
        "High-risk CLI wrappers",
        "`scripts/run_orchestrator.py`",
        "`scripts/forgeflow_evolution.py`",
    ]:
        assert required_text in contract_map


def test_contract_map_names_evolution_runtime_seams() -> None:
    contract_map = (ROOT / "docs" / "contract-map.md").read_text(encoding="utf-8")

    for required_text in [
        "Evolution runtime seam boundaries",
        "`forgeflow_runtime/evolution_rules.py`",
        "`forgeflow_runtime/evolution_lifecycle.py`",
        "`forgeflow_runtime/evolution_execution.py`",
        "`forgeflow_runtime/evolution_doctor.py`",
        "`forgeflow_runtime/evolution_promotion_plans.py`",
        "`forgeflow_runtime/evolution_proposals.py`",
        "`forgeflow_runtime/evolution_promotion_gates.py`",
        "`forgeflow_runtime/evolution_promotions.py`",
        "approved command execution lives with rule execution",
        "python -m pytest tests/evolution -q",
    ]:
        assert required_text in contract_map


def test_contract_map_runtime_seam_paths_exist_and_are_declared() -> None:
    contract_map = (ROOT / "docs" / "contract-map.md").read_text(encoding="utf-8")

    assert "Contract map validation checks named runtime seam files exist" in contract_map
    for rel in [
        "forgeflow_runtime/gate_evaluation.py",
        "forgeflow_runtime/resume_validation.py",
        "forgeflow_runtime/artifact_validation.py",
        "forgeflow_runtime/task_identity.py",
        "forgeflow_runtime/plan_ledger.py",
        "forgeflow_runtime/stage_transition.py",
        "forgeflow_runtime/route_execution.py",
        "forgeflow_runtime/operator_routing.py",
    ]:
        assert f"`{rel}`" in contract_map
        assert (ROOT / rel).is_file()


def test_contract_map_validation_commands_reference_existing_paths() -> None:
    contract_map = (ROOT / "docs" / "contract-map.md").read_text(encoding="utf-8")

    assert "Contract map validation checks named validation command paths exist" in contract_map
    for rel in [
        "scripts/validate_sample_artifacts.py",
        "tests/test_validate_sample_artifacts.py",
        "scripts/validate_policy.py",
        "tests/evolution",
        "tests/runtime",
        "scripts/validate_generated.py",
        "tests/test_generate_adapters.py",
        "tests/test_validate_generated.py",
        "tests/test_plugin_manifests.py",
        "scripts/validate_structure.py",
    ]:
        assert rel in contract_map
        assert (ROOT / rel).exists()


def test_script_thinness_keeps_operator_route_logic_out_of_cli_wrapper() -> None:
    script = ROOT / "scripts" / "run_orchestrator.py"
    tree = ast.parse(script.read_text(encoding="utf-8"))
    assigned_names = set()
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned_names.add(node.target.id)
        elif isinstance(node, ast.Assign):
            assigned_names.update(target.id for target in node.targets if isinstance(target, ast.Name))

    assert "operator route selection" in (ROOT / "docs" / "contract-map.md").read_text(encoding="utf-8")
    assert not {"STAGE_ROLE_MAP", "ROUTE_ORDER", "RISK_TO_ROUTE"} & assigned_names


def test_make_validate_runs_runtime_seam_tests() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "-m pytest tests/runtime -q" in makefile
