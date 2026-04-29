# 0001 — Absorb AI-readiness cartography as analysis discipline

- Date: 2026-04-29
- Status: accepted
- Source: `gimso2x/skills_repo/ai-readiness-cartography`

## Context

An external AI-readiness rubric scored ForgeFlow poorly as a source repository because it expected root/module context files, explicit tribal-knowledge stores, dependency maps, and zero broken path-like references.

That signal is useful, but ForgeFlow is also an installable harness/plugin. A source-only context document can help contributors, but it does not prove that installed projects receive better guidance. Chasing the external score directly would add surface area without necessarily improving the installed user experience.

## Decision

Absorb the rubric as review and validation discipline, not as a new lifecycle stage or mandatory score gate.

## Adopted

- Deterministic context-path validation for repo-local references.
- Review questions for navigation, evidence, dependency awareness, tribal knowledge, and freshness.
- A durable `docs/decisions/` home for future decisions that would otherwise become tribal knowledge.

## Adapted

- External broken-path scoring becomes a small local validator focused on ForgeFlow's real docs and context surfaces.
- AI-readiness categories become review questions in `docs/review-model.md`.
- Dependency-map pressure is handled through existing architecture/contract-map docs when it helps maintainers, not through scorecard theater.

## Rejected

- Importing the external scorer into ForgeFlow runtime core.
- Making the external `100` point score a release gate.
- Adding root/module `AGENTS.md` files only to satisfy the scorer.
- Adding a new ForgeFlow command, stage, approval gate, schema lane, or runtime state lane for AI-readiness.

## Consequences

- `make validate` can catch stale repo-local context paths cheaply.
- Reviews have sharper questions without gaining another process ceremony.
- Installed-project guidance must still be improved through generated adapters, installer outputs, and plugin help when needed; source-repo docs alone are not enough.
