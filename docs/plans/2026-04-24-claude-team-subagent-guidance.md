# Claude Team/Subagent Guidance Implementation Plan

> **For Hermes:** Implement directly with TDD; keep this as the task record.

**Goal:** Add Claude-only team/subagent execution guidance inspired by revfactory/harness without changing ForgeFlow core semantics.

**Architecture:** ForgeFlow remains artifact-first. Claude adapter may expose team execution capabilities, but subagents/agent teams are execution mechanisms only. Generated Claude output should document Producer-Reviewer, Fan-out/Fan-in, and Expert Pool patterns and require all outputs to land in ForgeFlow artifacts.

**Tech Stack:** Python generator + YAML manifest + pytest.

---

## Task 1: Add regression tests for Claude-only team guidance

**Objective:** Ensure Claude generated adapter includes team/subagent guidance while Codex/Codex remain adapter-neutral.

**Files:**
- Modify: `tests/test_generate_adapters.py`
- Modify: `tests/test_validate_generated.py`

**Verification:**
- `pytest tests/test_generate_adapters.py tests/test_validate_generated.py -q` should fail before implementation.

## Task 2: Extend adapter manifest contract

**Objective:** Add optional `team_execution` metadata to adapter manifests.

**Files:**
- Modify: `adapters/manifest.schema.json`
- Modify: `adapters/targets/claude/manifest.yaml`

**Contract:**
- `supports_subagents: boolean`
- `supports_agent_teams: boolean`
- `preferred_review_pattern: string`
- `supported_patterns: string[]`
- `guidance: string[]`

## Task 3: Render Claude team execution guidance

**Objective:** Teach `scripts/generate_adapters.py` to render team guidance only when manifest metadata exists.

**Files:**
- Modify: `scripts/generate_adapters.py`
- Generated: `adapters/generated/claude/CLAUDE.md`

**Rules:**
- Include: `Subagents are an execution mechanism, not a ForgeFlow workflow primitive.`
- Include: `Subagents may produce evidence, but artifacts remain the source of truth.`
- Include supported patterns: Producer-Reviewer, Fan-out/Fan-in, Expert Pool.
- Do not add the section to Codex/Codex unless their manifest opts in later.

## Task 4: Document adapter boundary

**Objective:** Explain the Claude-specific boundary in docs.

**Files:**
- Modify: `docs/adapter-model.md` or `docs/review-model.md`

**Verification:**
- Generated adapter and docs both say subagents cannot bypass artifact contracts.

## Task 5: Full validation and commit

**Commands:**
- `python3 scripts/generate_adapters.py`
- `pytest tests/test_generate_adapters.py tests/test_validate_generated.py -q`
- `make validate`
- `pytest tests/ -q`

**Commit:**
- `feat: add claude team execution guidance`
