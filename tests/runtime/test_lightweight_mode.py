"""Tests for forgeflow_runtime.lightweight_mode."""

from __future__ import annotations

import dataclasses

import pytest

from forgeflow_runtime.lightweight_mode import (
    EnforcementMode,
    LightweightConfig,
    RuntimeAvailability,
    build_lightweight_prompt,
    check_runtime_availability,
    format_mode_report,
    load_skill_md,
    resolve_effective_mode,
    should_use_gate,
)


# ---------------------------------------------------------------------------
# check_runtime_availability
# ---------------------------------------------------------------------------

class TestCheckRuntimeAvailability:
    def test_runtime_present_returns_available_true(self) -> None:
        avail = check_runtime_availability()
        assert avail.runtime_available is True
        assert avail.python_version is not None
        assert isinstance(avail.missing_modules, list)


# ---------------------------------------------------------------------------
# resolve_effective_mode
# ---------------------------------------------------------------------------

class TestResolveEffectiveMode:
    def test_hard_plus_available_stays_hard(self) -> None:
        config = LightweightConfig(mode=EnforcementMode.HARD)
        avail = RuntimeAvailability(runtime_available=True, python_version="3.12.0")
        assert resolve_effective_mode(config, avail) is EnforcementMode.HARD

    def test_hard_plus_unavailable_with_fallback_becomes_soft(self) -> None:
        config = LightweightConfig(
            mode=EnforcementMode.HARD,
            fallback_to_soft=True,
        )
        avail = RuntimeAvailability(
            runtime_available=False,
            python_version="3.12.0",
            missing_modules=["forgeflow_runtime.gate_evaluation"],
        )
        assert resolve_effective_mode(config, avail) is EnforcementMode.SOFT

    def test_hybrid_always_remains_hybrid(self) -> None:
        config = LightweightConfig(mode=EnforcementMode.HYBRID)
        avail_ok = RuntimeAvailability(runtime_available=True, python_version="3.12.0")
        avail_bad = RuntimeAvailability(
            runtime_available=False,
            python_version="3.12.0",
            missing_modules=["forgeflow_runtime.gate_evaluation"],
        )
        assert resolve_effective_mode(config, avail_ok) is EnforcementMode.HYBRID
        assert resolve_effective_mode(config, avail_bad) is EnforcementMode.HYBRID

    def test_fallback_disabled_keeps_configured_mode(self) -> None:
        config = LightweightConfig(
            mode=EnforcementMode.HARD,
            fallback_to_soft=False,
        )
        avail = RuntimeAvailability(
            runtime_available=False,
            python_version="3.12.0",
            missing_modules=["x"],
        )
        assert resolve_effective_mode(config, avail) is EnforcementMode.HARD


# ---------------------------------------------------------------------------
# load_skill_md
# ---------------------------------------------------------------------------

class TestLoadSkillMd:
    def test_existing_file_returns_content(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(tmp_path) / "SKILL.md"  # type: ignore[arg-type]
        p.write_text("# Hello\nWorld", encoding="utf-8")
        assert load_skill_md(str(p)) == "# Hello\nWorld"

    def test_missing_file_returns_empty_string(self) -> None:
        assert load_skill_md("/tmp/__nonexistent_skill_md_12345.md") == ""


# ---------------------------------------------------------------------------
# build_lightweight_prompt
# ---------------------------------------------------------------------------

class TestBuildLightweightPrompt:
    def test_contains_skill_content_and_task_context(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(tmp_path) / "SKILL.md"  # type: ignore[arg-type]
        p.write_text("Follow these rules.", encoding="utf-8")
        result = build_lightweight_prompt([str(p)], "Fix the bug")
        assert "Follow these rules." in result
        assert "Fix the bug" in result

    def test_empty_paths_yields_context_only(self) -> None:
        result = build_lightweight_prompt([], "Do stuff")
        assert "Do stuff" in result


# ---------------------------------------------------------------------------
# should_use_gate
# ---------------------------------------------------------------------------

class TestShouldUseGate:
    def test_hard_always_true(self) -> None:
        assert should_use_gate(EnforcementMode.HARD, "small") is True

    def test_soft_always_false(self) -> None:
        assert should_use_gate(EnforcementMode.SOFT, "large") is False

    def test_hybrid_small_false(self) -> None:
        assert should_use_gate(EnforcementMode.HYBRID, "small") is False

    def test_hybrid_medium_true(self) -> None:
        assert should_use_gate(EnforcementMode.HYBRID, "medium") is True

    def test_hybrid_large_true(self) -> None:
        assert should_use_gate(EnforcementMode.HYBRID, "large") is True


# ---------------------------------------------------------------------------
# format_mode_report
# ---------------------------------------------------------------------------

class TestFormatModeReport:
    def test_report_contains_mode_name(self) -> None:
        config = LightweightConfig(mode=EnforcementMode.HARD)
        avail = RuntimeAvailability(runtime_available=True, python_version="3.12.0")
        report = format_mode_report(config, avail, EnforcementMode.HARD)
        assert "hard" in report

    def test_report_contains_stages(self) -> None:
        config = LightweightConfig(mode=EnforcementMode.SOFT)
        avail = RuntimeAvailability(runtime_available=False, python_version="3.11.0")
        report = format_mode_report(config, avail, EnforcementMode.SOFT)
        assert "clarify" in report
        assert "plan" in report


# ---------------------------------------------------------------------------
# RuntimeAvailability immutability
# ---------------------------------------------------------------------------

class TestRuntimeAvailabilityFrozen:
    def test_frozen_dataclass_raises_on_assignment(self) -> None:
        avail = RuntimeAvailability(
            runtime_available=True,
            python_version="3.12.0",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            avail.runtime_available = False  # type: ignore[misc]
