from __future__ import annotations

import pytest

from forgeflow_runtime.enforcement_config import (
    EnforcementLevel,
    GateConfig,
    ProjectEnforcement,
    StageConfig,
    effective_enforcement_for_task,
    format_enforcement_report,
    is_stage_enabled,
    parse_enforcement_config,
    validate_config,
)


# ── parse_enforcement_config ─────────────────────────────────────────────

class TestParseEnforcementConfig:
    def test_basic_hard_config(self) -> None:
        text = """\
enforcement: hard
stages:
  - clarify
  - plan
  - execute
  - review
"""
        cfg = parse_enforcement_config(text)
        assert cfg.level is EnforcementLevel.HARD
        assert [s.name for s in cfg.stages] == ["clarify", "plan", "execute", "review"]
        assert all(s.enabled for s in cfg.stages)

    def test_soft_with_selective_stages(self) -> None:
        text = """\
enforcement: soft
stages:
  - plan
  - execute
"""
        cfg = parse_enforcement_config(text)
        assert cfg.level is EnforcementLevel.SOFT
        assert [s.name for s in cfg.stages] == ["plan", "execute"]

    def test_hybrid_with_gates(self) -> None:
        text = """\
enforcement: hybrid
stages:
  - clarify
  - plan
  - execute
  - review
gates:
  require_artifact: false
  allow_skip_below: small
"""
        cfg = parse_enforcement_config(text)
        assert cfg.level is EnforcementLevel.HYBRID
        assert cfg.gates.require_artifact is False
        assert cfg.gates.allow_skip_below == "small"

    def test_empty_text_returns_defaults(self) -> None:
        cfg = parse_enforcement_config("")
        assert cfg.level is EnforcementLevel.HARD
        assert [s.name for s in cfg.stages] == ["clarify", "plan", "execute", "review"]
        assert cfg.gates == GateConfig()

    def test_minimal_enforcement_only(self) -> None:
        cfg = parse_enforcement_config("enforcement: soft")
        assert cfg.level is EnforcementLevel.SOFT
        assert len(cfg.stages) == 4  # defaults


# ── is_stage_enabled ─────────────────────────────────────────────────────

class TestIsStageEnabled:
    def test_enabled_stage_returns_true(self) -> None:
        cfg = ProjectEnforcement(
            level=EnforcementLevel.HARD,
            stages=[StageConfig(name="plan"), StageConfig(name="execute")],
        )
        assert is_stage_enabled(cfg, "plan") is True

    def test_missing_stage_returns_false(self) -> None:
        cfg = ProjectEnforcement(
            level=EnforcementLevel.HARD,
            stages=[StageConfig(name="plan")],
        )
        assert is_stage_enabled(cfg, "review") is False

    def test_disabled_stage_returns_false(self) -> None:
        cfg = ProjectEnforcement(
            level=EnforcementLevel.HARD,
            stages=[StageConfig(name="plan", enabled=False)],
        )
        assert is_stage_enabled(cfg, "plan") is False


# ── effective_enforcement_for_task ───────────────────────────────────────

class TestEffectiveEnforcement:
    def test_hard_always_hard(self) -> None:
        cfg = ProjectEnforcement(level=EnforcementLevel.HARD, stages=[])
        assert effective_enforcement_for_task(cfg, "small") is EnforcementLevel.HARD
        assert effective_enforcement_for_task(cfg, "medium") is EnforcementLevel.HARD
        assert effective_enforcement_for_task(cfg, "large") is EnforcementLevel.HARD

    def test_soft_always_soft(self) -> None:
        cfg = ProjectEnforcement(level=EnforcementLevel.SOFT, stages=[])
        assert effective_enforcement_for_task(cfg, "large") is EnforcementLevel.SOFT

    def test_hybrid_small_is_soft(self) -> None:
        cfg = ProjectEnforcement(level=EnforcementLevel.HYBRID, stages=[])
        assert effective_enforcement_for_task(cfg, "small") is EnforcementLevel.SOFT

    def test_hybrid_medium_is_hard(self) -> None:
        cfg = ProjectEnforcement(level=EnforcementLevel.HYBRID, stages=[])
        assert effective_enforcement_for_task(cfg, "medium") is EnforcementLevel.HARD

    def test_hybrid_large_is_hard(self) -> None:
        cfg = ProjectEnforcement(level=EnforcementLevel.HYBRID, stages=[])
        assert effective_enforcement_for_task(cfg, "large") is EnforcementLevel.HARD


# ── validate_config ──────────────────────────────────────────────────────

class TestValidateConfig:
    def test_valid_config_no_errors(self) -> None:
        cfg = parse_enforcement_config("enforcement: hard")
        assert validate_config(cfg) == []

    def test_no_stages_enabled_returns_error(self) -> None:
        cfg = ProjectEnforcement(
            level=EnforcementLevel.HARD,
            stages=[StageConfig(name="clarify", enabled=False)],
        )
        errors = validate_config(cfg)
        assert len(errors) == 1
        assert "at least one stage" in errors[0].lower()


# ── format_enforcement_report ────────────────────────────────────────────

class TestFormatEnforcementReport:
    def test_report_contains_level_and_stage_names(self) -> None:
        cfg = parse_enforcement_config("enforcement: hard")
        report = format_enforcement_report(cfg)
        assert "hard" in report
        assert "clarify" in report
        assert "plan" in report
        assert "execute" in report
        assert "review" in report

    def test_report_shows_disabled_marker(self) -> None:
        cfg = ProjectEnforcement(
            level=EnforcementLevel.SOFT,
            stages=[StageConfig(name="plan", enabled=False)],
        )
        report = format_enforcement_report(cfg)
        assert "soft" in report
        assert "plan" in report
