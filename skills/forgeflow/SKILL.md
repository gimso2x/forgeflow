---
name: forgeflow
description: Artifact-first delivery workflow for AI coding agents. Use when a user types /forgeflow, /forgeflow:<stage>, or asks to implement, refactor, debug, review, or ship code through clarify, route selection, artifacts, gates, and independent review.
validate_prompt: |
  Must route work through explicit ForgeFlow stages and artifact-backed gates.
  Must preserve stage boundaries, verification evidence, and independent review semantics.
  Must not treat ForgeFlow as a chat-only ritual when task artifacts are required.
---

# ForgeFlow

ForgeFlow turns agent work into explicit stages with Markdown artifacts, gates, and independent review. It enforces **Deep Architecture Discipline** (Depth, Seam, Locality, Deletion test) and a **Grilling loop** (Socratic interviewing with recommended answers) to ensure rigorous design and maintainable code.

## Slash-style entrypoints

- `/forgeflow` -> this overview workflow skill
- `/forgeflow-init ...` -> `forgeflow-init`
- `/forgeflow:clarify ...` -> `clarify`
- `/forgeflow:plan` -> `plan`
- `/forgeflow:execute` -> `run`
- `/forgeflow:review` -> `review`
- `/forgeflow:ship` -> `ship`
- `/forgeflow:finish` -> `finish`

## Input

- User request or issue
- Target repository/path
- Constraints, acceptance criteria, and risk notes if available
- Existing artifacts if the task is already in progress

## Route model

| Route | Stages | When |
|-------|--------|------|
| small | clarify -> execute -> quality-review -> ship -> finish | 1-2 files, low risk, easy rollback |
| medium | clarify -> plan -> execute -> quality-review -> ship -> finish | Several coordinated files, shared state, moderate test surface |
| high | clarify -> plan -> execute -> spec-review -> quality-review -> ship -> long-run -> finish | Auth/security, data migration, infra, irreversible changes |
| epic | clarify -> milestone -> (per milestone) plan -> execute -> spec-review -> quality-review -> ship -> long-run -> finish | Massive scope, hierarchical milestones, multi-week effort |

Complexity thresholds (rough guide, not rigid):

| Score | Route |
|-------|-------|
| 5-8 | small |
| 9-16 | medium (light 9-12, full 13-16) |
| 17-24 | high |
| 25+ | epic |

## Output Artifacts

All artifacts are Markdown files written to `.forgeflow/tasks/<task-id>/`:

- `brief.md` — clarified objective, constraints, risk, route (template: `templates/brief.md`)
- `plan.md` — task decomposition with steps, verification, contracts (template: `templates/plan.md`)
- `implementation-notes.md` — real-time execution log (template: `templates/implementation-notes.md`)
- `review-report.md` — independent review result (template: `templates/review-report.md`)
- `roadmap.md` for epic route: milestone DAG and statuses (template: `templates/roadmap.md`)
- `ship-summary.md` — final handoff summary (created by ship)
- `eval-record.md` — reusable learnings for high/epic routes (template: `templates/eval-record.md`)
- `evolution-rule.md` — reusable rule candidate or active rule (template: `templates/evolution-rule.md`)

## Status analysis before routing

Before choosing the next stage for an existing task, inspect the active task directory (`<task-dir>/implementation-notes.md`) for current stage, status, progress, and blockers. Check `review-report.md` for verdicts and open blockers.

## File write and output discipline

Default to **artifact-first mode**. Unless the user explicitly asks for a dry run, exact-output response, or no-write simulation, create/update Markdown artifacts under `.forgeflow/tasks/<task-id>/`.

If the task directory does not exist yet, bootstrap it first (create `.forgeflow/tasks/<task-id>/` with the appropriate template). Do not skip straight to source edits when the artifact workspace is missing.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts are mentioned without an explicit path, assume `.forgeflow/tasks/<task-id>/`, not chat-only fallback. Write only under the current project workspace or the active task directory. Never write inside `skills/<skill>/`.

## Role Boundaries

ForgeFlow separates responsibilities across stages. The implementing session must not approve its own work.

### Canonical responsibilities

| Role | Stages | Responsibility |
|------|--------|----------------|
| planning | clarify, plan, milestone | scope, decompose, write/update artifacts, define file boundaries |
| implementation | execute | edit code only inside assigned scope, run validation, update evidence |
| review | review | inspect artifacts independently, separate reported from observed evidence |
| learning | long-run | extract reusable patterns, propose evolution rule candidates |

### Role separation principles

1. **Implementation does not self-approve.** The implementer's summary is input for review, not a substitute.
2. **Review is read-only.** Review records findings in `review-report.md` and hands back to the worker. It never edits code.
3. **If only one session is available**, keep the role boundary by using separate turns with artifact handoffs. Do not blur implementation and review in the same turn.
4. **Model binding**: When the shell supports role-specific model selection, prefer the strongest reasoning model for planning/review and a coding-optimized model for execution. The artifact contract records the role boundary; it does not require a central model database.

## Execution Patterns

Different routes use different execution strategies for parallel workers and reviewers.

### Pattern: producer-reviewer (default, all routes)

The implementer (producer) writes code. A separate review pass (reviewer) inspects the result. Every route uses this at minimum.

```
producer → artifact → reviewer → verdict
```

### Pattern: pipeline (sequential gates)

Steps execute in order with verification gates between them. Used when steps have data or state dependencies.

```
step 1 → gate → step 2 → gate → step 3 → final gate
```

Applied by default for medium routes and all routes with ordered plan steps.

### Pattern: fan-out/fan-in (parallel workers)

Multiple independent workers execute in parallel, then a single reviewer consolidates. Used for high/epic routes when plan tasks touch different files with no shared state.

```
worker A ──┐
worker B ──┤ → reviewer → verdict
worker C ──┘
```

### When to use which pattern

| Route | Default pattern | When to upgrade |
|-------|----------------|-----------------|
| small | pipeline + producer-reviewer | Never — single worker is sufficient |
| medium | pipeline + producer-reviewer | Upgrade to fan-out when 3+ independent file groups |
| high | fan-out/fan-in + producer-reviewer | Always — separate spec and quality reviews |
| epic | fan-out/fan-in per milestone | Always — milestone-level parallel execution |

Plans for high/epic routes should explicitly name the execution pattern in the Architecture Notes section.

## Evolution rule flow

ForgeFlow turns repeated patterns and mistakes into Markdown rules without restoring the old Python runtime:

1. `long-run` records evidence-backed candidates in `eval-record.md` and `.forgeflow/evolution/proposed/*.md` using `templates/evolution-rule.md`.
2. `review` validates candidate evidence, false-positive guard, scope, enforcement mode, and rollback/retirement path.
3. Approved project rules move to `.forgeflow/evolution/active/` and are loaded automatically by future `clarify`, `plan`, and `execute` stages.
4. Global rules live under `~/.forgeflow/evolution/active/*.md`, but they are advisory only and cannot hard block a project task.
5. Retired rules move to `.forgeflow/evolution/retired/` with a retirement reason.

## Strict response constraints

When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.

When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.

## Rules

1. Start with clarify unless the user provides a complete brief.
2. Pick the smallest route that honestly covers the risk.
3. Do not skip plan for medium or high work.
4. Do not merge spec-review and quality-review.
5. Do not treat the implementer's own summary as approval.
6. Keep state in artifacts/files, not just chat history.
7. Each plan step implements only its own scope. Do not implement future steps early.
8. The review stage is read-only verification. Do not use Write or Edit during review. Record required fixes in `review-report.md` findings and hand back to the worker.
9. Project active evolution rules are required constraints when their trigger and application stage match. Global evolution rules are advisory only.

## Operator prompts

Small task:

```text
Use ForgeFlow. Clarify this request, choose the route, execute the smallest safe change, then state what evidence justifies quality-review and finalize.
```

Medium task:

```text
Use ForgeFlow. Clarify first, select the route, write a concrete plan with expected artifacts and verification, then execute only after the plan is clear.
```

Large/high-risk task:

```text
Use ForgeFlow. Treat this as large/high-risk. Clarify, plan, execute, run spec-review and quality-review separately, and call out residual risk before finalize.
```

Epic/massive scale task:

```text
Use ForgeFlow. Treat this as an epic. Clarify, breakdown milestones, then for each milestone: plan, execute, and review. Track progress in roadmap.md.
```
