"""Tests for forgeflow_runtime.ci_gate."""

from __future__ import annotations

import os

import pytest

from forgeflow_runtime.ci_gate import (
    CIGateConfig,
    GateCheckResult,
    check_artifact_exists,
    format_gate_result,
    generate_github_actions_workflow,
    generate_pr_template,
    run_gate_check,
    scan_artifacts,
)


# ── check_artifact_exists ──────────────────────────────────────────


class TestCheckArtifactExists:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "report.json"
        f.write_text("{}")
        assert check_artifact_exists(str(f)) is True

    def test_missing_file(self, tmp_path):
        assert check_artifact_exists(str(tmp_path / "nope.json")) is False


# ── scan_artifacts ─────────────────────────────────────────────────


class TestScanArtifacts:
    def test_finds_files_in_artifact_dirs(self, tmp_path):
        d = tmp_path / ".forgeflow" / "artifacts"
        d.mkdir(parents=True)
        (d / "review-report.json").write_text("{}")
        (d / "extra.txt").write_text("hello")

        cfg = CIGateConfig(
            artifact_dirs=[str(d)],
        )
        found = scan_artifacts(cfg)
        assert sorted(found) == ["extra.txt", "review-report.json"]

    def test_empty_dirs_returns_empty(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        cfg = CIGateConfig(artifact_dirs=[str(d)])
        assert scan_artifacts(cfg) == []


# ── run_gate_check ─────────────────────────────────────────────────


class TestRunGateCheck:
    def test_all_artifacts_present_passes(self, tmp_path):
        d = tmp_path / ".forgeflow" / "artifacts"
        d.mkdir(parents=True)
        (d / "review-report.json").write_text('{"ok": true}')

        cfg = CIGateConfig(
            required_artifacts=["review-report.json"],
            artifact_dirs=[str(d)],
        )
        result = run_gate_check(cfg)
        assert result.passed is True
        assert result.missing_artifacts == []

    def test_missing_artifacts_fails(self, tmp_path):
        d = tmp_path / ".forgeflow" / "artifacts"
        d.mkdir(parents=True)

        cfg = CIGateConfig(
            required_artifacts=["review-report.json", "coverage.json"],
            artifact_dirs=[str(d)],
        )
        result = run_gate_check(cfg)
        assert result.passed is False
        assert "review-report.json" in result.missing_artifacts
        assert "coverage.json" in result.missing_artifacts

    def test_invalid_json_collected_as_error(self, tmp_path):
        d = tmp_path / ".forgeflow" / "artifacts"
        d.mkdir(parents=True)
        (d / "review-report.json").write_text("NOT VALID JSON{{{")

        cfg = CIGateConfig(
            required_artifacts=["review-report.json"],
            artifact_dirs=[str(d)],
            check_schema=True,
        )
        result = run_gate_check(cfg)
        assert result.passed is False
        assert len(result.errors) == 1
        assert "Schema error" in result.errors[0]


# ── format_gate_result ─────────────────────────────────────────────


class TestFormatGateResult:
    def test_pass_output(self):
        result = GateCheckResult(
            passed=True,
            gate_name="ci-gate",
            message="Gate check PASS",
            required_artifacts=["review-report.json"],
            missing_artifacts=[],
            errors=[],
        )
        text = format_gate_result(result)
        assert "PASS" in text

    def test_fail_output(self):
        result = GateCheckResult(
            passed=False,
            gate_name="ci-gate",
            message="Gate check FAIL",
            required_artifacts=["review-report.json"],
            missing_artifacts=["review-report.json"],
            errors=[],
        )
        text = format_gate_result(result)
        assert "FAIL" in text


# ── generate_github_actions_workflow ───────────────────────────────


class TestGenerateGitHubActionsWorkflow:
    def test_contains_name(self):
        cfg = CIGateConfig()
        yaml = generate_github_actions_workflow(cfg)
        assert "ForgeFlow Gate Check" in yaml


# ── generate_pr_template ───────────────────────────────────────────


class TestGeneratePRTemplate:
    def test_contains_stage_names(self):
        md = generate_pr_template(["review", "merge"])
        assert "review" in md
        assert "merge" in md


# ── GateCheckResult frozen immutability ────────────────────────────


class TestGateCheckResultFrozen:
    def test_frozen_immutability(self):
        result = GateCheckResult(
            passed=True,
            gate_name="ci-gate",
            message="test",
            required_artifacts=[],
            missing_artifacts=[],
            errors=[],
        )
        with pytest.raises(AttributeError):
            result.passed = False  # type: ignore[misc]
