from __future__ import annotations

import importlib
from pathlib import Path


EVOLUTION_MODULES = [
    "audit",
    "observations",
    "rules",
    "doctor",
    "promotions",
    "execution",
    "proposals",
    "lifecycle",
]


def test_evolution_subpackage_modules_are_importable() -> None:
    for module_name in EVOLUTION_MODULES:
        module = importlib.import_module(f"forgeflow_runtime.evolution.{module_name}")
        assert module.__name__ == f"forgeflow_runtime.evolution.{module_name}"


def test_public_evolution_facade_still_exports_existing_api() -> None:
    evolution = importlib.import_module("forgeflow_runtime.evolution")

    expected_names = [
        "list_rules",
        "dry_run_rule",
        "execute_rule",
        "adopt_example_rule",
        "promotion_plan",
        "promotion_gate",
        "promotion_ready",
        "promote_rule",
        "doctor_evolution_state",
    ]
    for name in expected_names:
        assert hasattr(evolution, name), name


def test_runtime_tests_share_json_file_helper_for_orchestrator_lifecycle() -> None:
    test_source = Path("tests/runtime/test_orchestrator_lifecycle.py").read_text(encoding="utf-8")

    assert "from .helpers import" in test_source
    assert "write_json_file" in test_source
    assert "def _json_dump" not in test_source


def test_runtime_tests_share_task_directory_helpers_for_orchestrator_lifecycle() -> None:
    test_source = Path("tests/runtime/test_orchestrator_lifecycle.py").read_text(encoding="utf-8")

    assert "from .helpers import" in test_source
    assert "small_task_dir" in test_source
    assert "medium_task_dir" in test_source
    assert "add_checkpoint_and_session" in test_source
    assert "def _small_task_dir" not in test_source
    assert "def _medium_task_dir" not in test_source
    assert "def _add_checkpoint_and_session" not in test_source


def test_agent_instructions_document_runtime_subpackage_boundaries() -> None:
    instructions = Path("AGENTS.md").read_text(encoding="utf-8")

    assert "55 modules, 67 importable" not in instructions
    for package_name in [
        "forgeflow_runtime/evolution/",
        "forgeflow_runtime/experiment/",
        "forgeflow_runtime/orchestra/",
    ]:
        assert package_name in instructions
