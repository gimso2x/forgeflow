from __future__ import annotations

import importlib.util
import json
import py_compile
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_ci_installs_requirements_and_runs_full_pytest_suite() -> None:
    workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")

    assert "python -m pip install -r requirements.txt" in workflow
    assert "python -m pytest -q" in workflow


def test_check_environment_reports_missing_venv_support(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    check_environment = _load_module(ROOT / "scripts" / "check_environment.py", "check_environment")

    monkeypatch.setattr(check_environment, "_venv_available", lambda: False)
    monkeypatch.setattr(check_environment, "_missing_modules", lambda modules: [])
    monkeypatch.setattr(sys, "argv", ["check_environment.py", "--require-venv-support"])

    assert check_environment.main() == 1
    output = capsys.readouterr().out
    assert "Python venv/ensurepip support is unavailable" in output
    assert "sudo apt-get install python3-venv" in output


def test_all_artifact_schemas_pin_current_schema_version() -> None:
    for schema_path in (ROOT / "schemas").glob("*.schema.json"):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema_version = schema["properties"]["schema_version"]
        assert schema_version.get("const") == "0.1", schema_path.name


def test_skill_examples_use_current_artifact_schema_version() -> None:
    for skill_path in [ROOT / "skills" / "plan" / "SKILL.md", ROOT / "skills" / "review" / "SKILL.md"]:
        text = skill_path.read_text(encoding="utf-8")
        assert '"schema_version": "1.0"' not in text
        assert '"schema_version": "0.1"' in text


def test_manifest_loader_uses_real_yaml_parser_for_quoted_scalars_and_lists() -> None:
    generate_adapters = _load_module(ROOT / "scripts" / "generate_adapters.py", "generate_adapters")
    manifest = generate_adapters.load_manifest(ROOT / "adapters" / "targets" / "claude" / "manifest.yaml")

    assert isinstance(manifest["supports_roles"], list)
    assert "coordinator" in manifest["supports_roles"]
    assert isinstance(manifest["supports_generated_files"], bool)


def test_adapter_related_python_files_compile_without_syntax_warnings() -> None:
    for path in [
        ROOT / "scripts" / "generate_adapters.py",
        ROOT / "scripts" / "validate_generated.py",
        ROOT / "tests" / "test_generate_adapters.py",
    ]:
        py_compile.compile(str(path), doraise=True)
