# ForgeFlow Maintainer Backlog

> **Last reviewed**: 2026-06-09 KST
> **Scope**: live maintainer tasks only. Historical design notes stay in [`docs/roadmap-improvements.md`](roadmap-improvements.md).

## How to use this backlog

- Treat GitHub issues as the source of truth for ownership and discussion.
- Use this document as the live, repo-local triage map for maintainers and autonomous improvement runs.
- Keep each item narrow enough to validate with focused targets before `make validate`.
- Do not copy old roadmap design text here unless it is still actionable in the current slim, markdown-only surface.

## Completed in v2.1.0

### #154 Improve usage audit artifact scanning and zero-signal semantics
- **Resolution**: `surface_usage_audit.py` updated to treat required_fields artifacts as always used. Template field warning mode added.

### #157 Add opt-in provider/plugin smoke validation
- **Resolution**: `smoke_local_plugins.py` extended with `--with-provider` flag. Default mode unchanged.

## Live items

### P1 — Next sprint

#### #155 Extract long Makefile document validators into scripts

- **Status**: ✅ completed
- **Resolution**: 5개 인라인 validator를 Python 스크립트로 추출 (validate-skills, validate-templates, validate-context-resume, validate-ship-safety/dogfooding-docs, validate-ci-workflows)

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
