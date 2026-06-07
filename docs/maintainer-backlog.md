# ForgeFlow Maintainer Backlog

> **Last reviewed**: 2026-06-07 KST
> **Scope**: live maintainer tasks only. Historical design notes stay in [`docs/roadmap-improvements.md`](roadmap-improvements.md).

## How to use this backlog

- Treat GitHub issues as the source of truth for ownership and discussion.
- Use this document as the live, repo-local triage map for maintainers and autonomous improvement runs.
- Keep each item narrow enough to validate with focused targets before `make validate`.
- Do not copy old roadmap design text here unless it is still actionable in the current slim, markdown-only surface.

## Live items

### P0 — Immediate

#### #154 Improve usage audit artifact scanning and zero-signal semantics

- **Status**: open
- **Affected surface**: `scripts/surface_usage_audit.py`, `Makefile` `usage-audit`, audit output semantics
- **Validation target**: `make usage-audit`, then `make validate`
- **Risk**: medium — audit false positives can train maintainers to ignore real drift; false zero-signal can hide dead surfaces.
- **Notes**: Tighten artifact scanning around active docs/templates/skills and make no-op output explicit instead of ambiguous silence.

#### #155 Extract long Makefile document validators into scripts

- **Status**: in progress locally
- **Affected surface**: `Makefile`, `scripts/validate_agent_docs.py`, any remaining long inline validator targets
- **Validation target**: `make validate-agent-docs`, then `make validate`
- **Risk**: low — refactor-only if output stays equivalent.
- **Notes**: First extraction moved AGENTS/preflight checks into `scripts/validate_agent_docs.py`; continue only if more large inline validators remain worth extracting.

### P1 — Next sprint

#### #157 Add opt-in provider/plugin smoke validation

- **Status**: open
- **Affected surface**: README validation docs, optional smoke guidance, adapter config docs; scripts only if opt-in and dependency-free
- **Validation target**: focused smoke target if added, plus `make validate`
- **Risk**: high — live provider/plugin checks can overclaim, mutate user state, or depend on unavailable credentials.
- **Notes**: Must stay opt-in. Default `make validate` must not run live provider/plugin E2E.

#### #159 Elevate standalone review workflow as a first-class surface

- **Status**: open
- **Affected surface**: `skills/ff-review/SKILL.md`, `docs/review-runtime-contract.md`, README standalone review section, eval fixtures
- **Validation target**: `make validate-evals`, `make validate-stage-tool-boundaries`, then `make validate`
- **Risk**: medium — standalone review must stay read-only and adapter-neutral.
- **Notes**: Preserve `input-source.md` and `normalized-input.md` as the handoff boundary; no adapter-specific hidden approval path.

### P2 — Nice to have

#### #158 Modularize large skill documents into shared references

- **Status**: open
- **Affected surface**: large `skills/*/SKILL.md` files, `skills/*/references/`, `skills/SKILLS.md`
- **Validation target**: `make validate-skills`, `make validate-template-refs`, then `make validate`
- **Risk**: medium — modularization can bury mandatory contract text if references are not explicit.
- **Notes**: Move reusable detail into references only when the top-level SKILL.md still states trigger, required artifacts, and validation contract clearly.

## Recently completed / archival handoff

- Historical roadmap phases P1–P7 are archived in [`docs/roadmap-improvements.md`](roadmap-improvements.md). Do not treat those completed phase tables as the live maintainer queue.
