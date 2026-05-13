"""TDD failing tests for Issue #135 — specialist agent runtime wiring.

These tests assert that spec-based specialist agents (security, backend,
frontend, infra, ux, perf) are fully wired into the runtime execution path:
  1. generator ROLE_TO_FILENAME mapping
  2. plugin.json manifest (agents + supports_roles)
  3. specialists_from_brief() domain→stage conversion
  4. operator_routing specialist role resolution
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from forgeflow_runtime import generator as gen_mod
from forgeflow_runtime.operator_routing import (
    STAGE_ROLE_MAP,
    role_for_stage,
    specialists_from_brief,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_JSON = REPO_ROOT / "adapters" / "targets" / "codex" / "plugin.json"
AGENTS_DIR = REPO_ROOT / "adapters" / "targets" / "codex" / "agents"

# ── 1. generator ROLE_TO_FILENAME specialist mapping ───────────────────

SPECIALIST_ROLES = [
    "security-reviewer",
    "ux-reviewer",
    "perf-reviewer",
    "frontend-worker",
    "backend-worker",
    "infra-worker",
]


@pytest.mark.parametrize("role", SPECIALIST_ROLES)
def test_role_to_filename_has_specialist(role: str) -> None:
    """Each specialist role must have a ROLE_TO_FILENAME entry."""
    assert role in gen_mod.ROLE_TO_FILENAME, (
        f"ROLE_TO_FILENAME missing specialist role: {role}"
    )


@pytest.mark.parametrize("role", SPECIALIST_ROLES)
def test_role_to_filename_points_to_existing_file(role: str) -> None:
    """ROLE_TO_FILENAME entry must point to a file that actually exists in prompts/canonical/."""
    filename = gen_mod.ROLE_TO_FILENAME.get(role)
    assert filename is not None, f"ROLE_TO_FILENAME has no entry for {role}"
    # specialist agent md files live in agents dir, prompt files in canonical
    # At minimum the referenced file must resolve
    prompt_path = gen_mod.CANONICAL_PROMPT_DIR / filename
    agents_path = AGENTS_DIR / f"forgeflow-{role}.md"
    assert prompt_path.exists() or agents_path.exists(), (
        f"Neither prompt file ({prompt_path}) nor agent file ({agents_path}) exists for {role}"
    )


# ── 2. plugin.json manifest ───────────────────────────────────────────

def test_plugin_json_loads() -> None:
    """plugin.json must be valid JSON."""
    payload = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)


@pytest.mark.parametrize("role", SPECIALIST_ROLES)
def test_plugin_json_supports_specialist_roles(role: str) -> None:
    """plugin.json supports_roles must list all specialist roles."""
    payload = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    supported = payload.get("supports_roles", [])
    assert role in supported, (
        f"plugin.json supports_roles missing: {role} (has: {supported})"
    )


@pytest.mark.parametrize("role", SPECIALIST_ROLES)
def test_plugin_json_agents_list_specialists(role: str) -> None:
    """plugin.json agents must reference specialist agent md files."""
    payload = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    agents = payload.get("agents", [])
    expected = f"adapters/targets/codex/agents/forgeflow-{role}.md"
    assert expected in agents, (
        f"plugin.json agents missing: {expected} (has: {agents})"
    )


@pytest.mark.parametrize("role", SPECIALIST_ROLES)
def test_specialist_agent_md_file_exists(role: str) -> None:
    """Each specialist agent markdown file must physically exist."""
    agent_file = AGENTS_DIR / f"forgeflow-{role}.md"
    assert agent_file.exists(), f"Missing agent file: {agent_file}"


# ── 3. specialists_from_brief() domain→stage conversion ────────────────

DOMAIN_VOCABULARY = {
    "security": "security-review",
    "backend": "backend-execute",
    "frontend": "frontend-execute",
    "infra": "infra-execute",
    "ux": "ux-review",
    "perf": "perf-review",
}


def test_specialists_from_brief_with_domain_names(tmp_path: Path) -> None:
    """brief.json with domain names (security, backend, ...) must resolve to stages."""
    brief = {"required_specialists": ["security", "backend"]}
    (tmp_path / "brief.json").write_text(json.dumps(brief), encoding="utf-8")

    result = specialists_from_brief(tmp_path)
    # Should map domain names to stage names recognized by STAGE_ROLE_MAP
    assert "security-review" in result or "security" in result, (
        f"specialists_from_brief did not resolve 'security': got {result}"
    )
    assert "backend-execute" in result or "backend" in result, (
        f"specialists_from_brief did not resolve 'backend': got {result}"
    )


def test_specialists_from_brief_with_stage_names(tmp_path: Path) -> None:
    """brief.json with stage names (security-review, backend-execute) must pass through."""
    brief = {"required_specialists": ["security-review", "backend-execute"]}
    (tmp_path / "brief.json").write_text(json.dumps(brief), encoding="utf-8")

    result = specialists_from_brief(tmp_path)
    assert "security-review" in result
    assert "backend-execute" in result


def test_specialists_from_brief_ignores_unknown(tmp_path: Path) -> None:
    """brief.json with unknown specialist names must filter them out."""
    brief = {"required_specialists": ["security", "nonexistent"]}
    (tmp_path / "brief.json").write_text(json.dumps(brief), encoding="utf-8")

    result = specialists_from_brief(tmp_path)
    assert "nonexistent" not in result


def test_specialists_from_brief_no_file(tmp_path: Path) -> None:
    """Missing brief.json returns empty list."""
    result = specialists_from_brief(tmp_path)
    assert result == []


# ── 4. operator_routing specialist role resolution ─────────────────────

SPECIALIST_STAGE_ROLE_PAIRS = [
    ("security-review", "security-reviewer"),
    ("ux-review", "ux-reviewer"),
    ("perf-review", "perf-reviewer"),
    ("frontend-execute", "frontend-worker"),
    ("backend-execute", "backend-worker"),
    ("infra-execute", "infra-worker"),
]


@pytest.mark.parametrize("stage,expected_role", SPECIALIST_STAGE_ROLE_PAIRS)
def test_stage_role_map_specialists(stage: str, expected_role: str) -> None:
    """STAGE_ROLE_MAP must map specialist stages to correct roles."""
    assert STAGE_ROLE_MAP.get(stage) == expected_role


@pytest.mark.parametrize("stage,expected_role", SPECIALIST_STAGE_ROLE_PAIRS)
def test_role_for_stage_specialists(stage: str, expected_role: str) -> None:
    """role_for_stage() must resolve specialist stages without workflow."""
    assert role_for_stage(stage) == expected_role


# ── 5. Integration: brief→stages→roles end-to-end ──────────────────────

def test_end_to_end_brief_to_roles(tmp_path: Path) -> None:
    """Full path: brief domains → specialists_from_brief → role_for_stage for each."""
    brief = {"required_specialists": ["security", "frontend", "perf"]}
    (tmp_path / "brief.json").write_text(json.dumps(brief), encoding="utf-8")

    stages = specialists_from_brief(tmp_path)
    # Must resolve to at least the stage names
    assert len(stages) >= 3, f"Expected >=3 specialists, got {stages}"

    for stage in stages:
        role = role_for_stage(stage)
        assert role in SPECIALIST_ROLES, (
            f"Stage {stage} resolved to unknown role: {role}"
        )
