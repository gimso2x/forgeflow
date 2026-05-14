import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_contract_map.py"

VALID_MAP = """# ForgeFlow Contract Map

## Contract surfaces

| Surface | Source of truth / owner | Regeneration command | Validation command | Known consumers |
| --- | --- | --- | --- | --- |
| `schemas/*.json` | `forgeflow_runtime/engine.py` | Hand-maintained | `python3 scripts/validate_policy.py` and `python -m pytest tests/runtime -q` | Runtime |
| `scripts/validate_contract_map.py` | `scripts/validate_contract_map.py` | Hand-maintained | `python3 scripts/validate_contract_map.py` | CI |
"""

INVALID_MAP_MISSING_FILE = """# ForgeFlow Contract Map

## Contract surfaces

| Surface | Source of truth / owner | Regeneration command | Validation command | Known consumers |
| --- | --- | --- | --- | --- |
| `non_existent_file.json` | `forgeflow_runtime/engine.py` | Hand-maintained | `python3 scripts/validate_policy.py` | Runtime |
"""

INVALID_MAP_MISSING_VALIDATION_SCRIPT = """# ForgeFlow Contract Map

## Contract surfaces

| Surface | Source of truth / owner | Regeneration command | Validation command | Known consumers |
| --- | --- | --- | --- | --- |
| `schemas/*.json` | `forgeflow_runtime/engine.py` | Hand-maintained | `python3 scripts/missing_script.py` | Runtime |
"""

@pytest.fixture
def temp_map_file(tmp_path):
    def _create_map(content):
        map_file = tmp_path / "contract-map.md"
        map_file.write_text(content, encoding="utf-8")
        return map_file
    return _create_map

def test_validate_contract_map_success(temp_map_file):
    # Ensure schemas dir and engine.py exist for this test to pass if it uses ROOT
    # But the script should be testable by pointing it to a specific file.
    map_path = temp_map_file(VALID_MAP)
    
    # We need to make sure the paths in VALID_MAP actually exist relative to ROOT
    # schemas/*.json -> schemas exists
    # forgeflow_runtime/engine.py exists
    # scripts/validate_policy.py exists
    # tests/runtime exists
    
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(map_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False
    )
    
    assert result.returncode == 0
    assert "CONTRACT MAP VALIDATION: PASS" in result.stdout

def test_validate_contract_map_missing_file(temp_map_file):
    map_path = temp_map_file(INVALID_MAP_MISSING_FILE)
    
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(map_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False
    )
    
    assert result.returncode != 0
    assert "non_existent_file.json" in result.stderr

def test_validate_contract_map_missing_validation_script(temp_map_file):
    map_path = temp_map_file(INVALID_MAP_MISSING_VALIDATION_SCRIPT)
    
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(map_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False
    )
    
    assert result.returncode != 0
    assert "scripts/missing_script.py" in result.stderr
