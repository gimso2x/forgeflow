from __future__ import annotations

import importlib
from pathlib import Path


EVOLUTION_MODULES = [
    "audit",
    "observations",
    "rules",
    "cases",
    "promotion_plans",
    "doctor",
    "promotions",
    "execution",
    "promotion_gates",
    "proposals",
    "lifecycle",
]


LEGACY_EVOLUTION_MODULES = [
    "evolution_audit",
    "evolution_observations",
    "evolution_rules",
    "evolution_cases",
    "evolution_promotion_plans",
    "evolution_doctor",
    "evolution_promotions",
    "evolution_execution",
    "evolution_promotion_gates",
    "evolution_proposals",
    "evolution_lifecycle",
]


def test_evolution_subpackage_modules_are_importable() -> None:
    for module_name in EVOLUTION_MODULES:
        module = importlib.import_module(f"forgeflow_runtime.evolution.{module_name}")
        assert module.__name__ == f"forgeflow_runtime.evolution.{module_name}"


def test_legacy_evolution_module_names_remain_importable() -> None:
    for module_name in LEGACY_EVOLUTION_MODULES:
        module = importlib.import_module(f"forgeflow_runtime.{module_name}")
        assert module.__name__ == f"forgeflow_runtime.{module_name}"


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


def test_agent_instructions_document_runtime_subpackage_boundaries() -> None:
    instructions = Path("AGENTS.md").read_text(encoding="utf-8")

    assert "55 modules, 67 importable" not in instructions
    for package_name in [
        "forgeflow_runtime/evolution/",
        "forgeflow_runtime/experiment/",
        "forgeflow_runtime/orchestra/",
    ]:
        assert package_name in instructions
