---
name: forgeflow
description: Artifact-first delivery workflow for AI coding agents. Routes work through clarify → plan → execute → review → ship stages with Markdown artifacts, verification gates, and independent review. Use when the user types /forgeflow, /forgeflow:<stage>, or asks to implement, refactor, debug, review, or ship code through a structured workflow.
version: 0.3.0
author: gimso2x
intent: "Route implementation, refactor, debug, review, and ship work through explicit artifact-backed stages."
inputs:
  - user_request: string
  - target_repository: path
  - existing_artifacts: markdown
outputs:
  - brief.md: artifact
  - plan.md: artifact
  - implementation-notes.md: artifact
  - review-report.md: artifact
  - ship-summary.md: artifact
dependencies:
  - skills/_shared/discipline.md
  - docs/adapter-config.md
  - docs/advisory-guidelines.md
  - templates/brief.md
  - templates/plan.md
validate_prompt: |
  Must route work through explicit ForgeFlow stages and artifact-backed gates.
  Must preserve stage boundaries, verification evidence, and independent review semantics.
  Must not treat ForgeFlow as a chat-only ritual when task artifacts are required.
---

# ForgeFlow

ForgeFlow turns agent work into explicit stages with Markdown artifacts, gates, and independent review.
It enforces **Deep Architecture Discipline** (Depth, Seam, Locality, Deletion test) and a **Grilling loop**.
Use Socratic interviewing with recommended answers to ensure rigorous design and maintainable code.

## Adapter detection

Skills may need adapter-specific behavior. Use the canonical detection table in `docs/adapter-config.md` (env var → adapter directory signals). Do not duplicate adapter flags or timeout tables here — link to `docs/adapter-config.md` instead.

Adapter-specific usage examples:

- Codex output normalization: strip raw diff before artifact parsing (see `docs/adapter-config.md` → Output normalization)
- Gemini: leverage 1M+ token context for project-wide "WHERE grounding" and consistency checks. Enforce `import type` for `verbatimModuleSyntax` compliance.
- Claude: expect structured table-format reports
- Cursor: use slash names without `:` (`/clarify`, not `/forgeflow:clarify`); resolve templates per Template resolution below

Adapter-specific CLI flags and timeout guides: `docs/adapter-config.md`.

## Slash-style entrypoints

| Stage | Claude / Codex / Gemini | Cursor |
|-------|-------------------------|--------|
| Overview | `/forgeflow` | `/forgeflow` |
| Clarify | `/forgeflow:clarify` | `/clarify` |
| Plan | `/forgeflow:plan` | `/plan` |
| Execute | `/forgeflow:execute` | `/execute` |
| Review | `/forgeflow:review` | `/review` |
| Ship | `/forgeflow:ship` | `/ship` |
| Long-run | `/forgeflow:long-run` | `/long-run` |
| Benchmark | `/forgeflow:benchmark` | `/benchmark` |

Cursor skill names cannot contain `:`. Use the Cursor column when invoking skills in Cursor; other adapters keep the `/forgeflow:*` form.

## Template resolution (all adapters)

Skills reference paths like `templates/brief.md`. Resolve the template root before reading or copying any template:

1. If `<workspace>/templates/<file>.md` exists, use that path.
2. Otherwise search for the ForgeFlow plugin `templates/` directory (first match wins):
   - `~/.cursor/plugins/local/forgeflow/templates/`
   - Any `~/.cursor/plugins/**/forgeflow/templates/`
   - Any `~/.claude/plugins/cache/forgeflow/**/templates/`
   - Any path under `.codex/plugins` that ends with `forgeflow/templates/`
3. When a template root is found, read `templates/<file>.md` relative to that root using the resolved absolute path.
4. If no template root is found, stop and tell the user to install ForgeFlow locally or add `templates/` to the workspace. Do not invent artifact structure.
5. Always write task artifacts under `<workspace>/.forgeflow/tasks/<task-id>/`, never under a plugin install or cache directory.

## Input

- User request or issue
- Target repository/path
- Constraints, acceptance criteria, and risk notes if available
- Existing artifacts if the task is already in progress

## Route model

- `small`
  - Stages: clarify -> execute -> review -> ship
  - When: 1-2 files, low risk, easy rollback
- `medium`
  - Stages: clarify -> plan -> execute -> review -> ship
  - When: several coordinated files, shared state, moderate test surface
- `high`
  - Stages: clarify -> plan -> execute -> review (spec) -> review (quality) -> ship -> long-run
  - When: auth/security, data migration, infra, irreversible changes
- `epic`
  - Stages: clarify -> plan (with epic decomposition) -> execute -> review (spec) -> review (quality) -> ship -> long-run
  - When: massive scope, hierarchical milestones, multi-week effort

Complexity thresholds (rough guide, not rigid):

The route score keeps the v0.x weighted model as a documentation contract after the Python runtime removal:

```text
raw_score = file_count*1.0 + estimated_lines*0.1 + requirement_count*2.0 + dependency_count*1.5 + risk_keywords*3.0
```

| Score | Route |
|-------|-------|
| `< 10` | small |
| `10-16.9` | medium-light: few files, scoped changes |
| `17-24.9` | medium-full: cross-module or service-level changes |
| `25-49.9` | high |
| `>= 50` | epic |

- `17.0` is the `mid_threshold` that separates medium-light from medium-full.
- If a project wants different thresholds, update this file, `skills/clarify/SKILL.md`, and README together.
- Budget and session sizing guidance is advisory, not a runtime quota; see `docs/advisory-guidelines.md`.

## Output Artifacts

All artifacts are Markdown files written to `.forgeflow/tasks/<task-id>/`:

- `brief.md` — clarified objective, constraints, risk, route (template: `templates/brief.md`)
- `plan.md` — task decomposition with steps, verification, contracts (template: `templates/plan.md`)
- `implementation-notes.md` — real-time execution log (template: `templates/implementation-notes.md`)
- `run-ledger.md` — execution truth per plan task (template: `templates/run-ledger.md`)
- `checkpoint.md` — tactical resume pointer (template: `templates/checkpoint.md`); **read first on stage resume** after context compaction
- `review-report.md` — independent review result (template: `templates/review-report.md`; high/epic uses spec then quality passes on this file)
- `roadmap.md` for epic route: milestone DAG and statuses (template: `templates/roadmap.md`)
- `ship-summary.md` — final handoff summary (template: `templates/ship-summary.md`)
- `eval-record.md` — reusable learnings for high/epic routes (template: `templates/eval-record.md`)
- Evolution rule candidates and active rules live under `.forgeflow/evolution/` using `templates/evolution-rule.md` — not as a standalone task artifact unless copying a snapshot for reference

## Status analysis before routing

Before choosing the next stage for an existing task, inspect the active task directory.

1. Read `checkpoint.md` first when present (`Minimum Read Set`, `Next Action`, `Blockers`).
2. Read `run-ledger.md` for task status truth; `implementation-notes.md` Reader Summary for narrative.
3. Check `review-report.md` Verdict and Open Blockers when review has run.

→ Compact/resume rules: `_shared/context-resume.md`

## File write and output discipline

→ Core rules: `_shared/discipline.md`.

When artifacts are mentioned without an explicit path, assume `.forgeflow/tasks/<task-id>/`, not chat-only fallback.

## Role Boundaries

ForgeFlow separates responsibilities across stages. The implementing session must not approve its own work.

### Canonical responsibilities

| Role | Stages | Responsibility |
|------|--------|----------------|
| planning | clarify, plan | scope, decompose, write/update artifacts, define file boundaries (plan includes epic decomposition) |
| implementation | execute | edit code only inside assigned scope, run validation, update evidence |
| review | review | inspect artifacts independently, separate reported from observed evidence |
| learning | long-run | extract reusable patterns, propose evolution rule candidates |

### Role separation principles

1. **Implementation does not self-approve.** The implementer's summary is input for review, not a substitute.
2. **Review is read-only.** Review records findings in `review-report.md` and hands back to the worker. It never edits code.
3. **If only one session is available**, keep the role boundary by using separate turns with artifact handoffs. Do not blur implementation and review in the same turn.
4. **Model binding**: When the shell supports role-specific model selection, use capability-appropriate models (heuristic, not enforced):
   - **Planning / review / spec micro-review** — strongest reasoning available
   - **Integration or multi-file execute** — standard coding model
   - **Mechanical plan steps** (1–2 files, complete spec) — fast/cheap model acceptable
   The artifact contract records the role boundary; it does not require a central model database.

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

Multiple independent workers execute in parallel, then a single reviewer consolidates.
Use this for high/epic routes when plan tasks touch different files with no shared state.

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

### Review depth by route

| Route | During execute (`/forgeflow:execute`) | After execute (`/forgeflow:review`) |
|-------|--------------------------------------|-------------------------------------|
| small | Self-check + step verification; no micro-reviewer subagents | Single **quality** pass on `review-report.md` |
| medium | Step verification + contract checkpoint per plan step | Single **quality** pass |
| high | Per-step **spec micro-check** (controller or `references/spec-reviewer-prompt.md`); optional quality micro-check after spec passes | **Spec** pass then **quality** pass (sequential, same `review-report.md`) |
| epic | Same as high, per milestone plan step | Same as high, per milestone completion |

Execute micro-gates do not replace stage review. Worker self-report and micro-review are input; stage review records them in `review-report.md` → **Execute Micro-Gates** and re-verifies with observed evidence (see `templates/review-report.md`).

Subagent dispatch templates: `skills/execute/references/` (`implementer-prompt.md`, `spec-reviewer-prompt.md`, `quality-reviewer-prompt.md`).

Plans for high/epic routes should explicitly name the execution pattern in the Architecture Notes section.

## Evolution rule flow

ForgeFlow turns repeated patterns and mistakes into Markdown rules during the **ship** stage, which runs in all routes (small, medium, high, epic):

- `observe`
  - Trigger: ship reviews task artifacts and identifies reusable patterns with concrete evidence
  - Artifact/location: `implementation-notes.md`, `review-report.md`, `eval-record.md` (if high/epic)
- `extract` (ship)
  - Trigger: reusable pattern found with evidence, not covered by existing active rules
  - Artifact/location: evolution rule written directly to `active/`:
    - `Scope: global-advisory` → `~/.forgeflow/evolution/active/<rule-name>.md` (default)
    - `Scope: project` → `.forgeflow/evolution/active/<rule-name>.md` (project-specific only)
  - No separate propose→validate cycle needed — review already validated the work
- `active`
  - Trigger: rule file exists in an `active/` directory
  - Loaded by future `clarify`, `plan`, and `execute` when trigger/stage match
- `retired`
  - Trigger: rule becomes harmful, obsolete, or too noisy
  - Artifact/location: `.forgeflow/evolution/retired/` (project) or `~/.forgeflow/evolution/retired/` (global) with reason
  - Next state: not loaded

Global rules are generated directly in `~/.forgeflow/evolution/` from long-run, reviewed in place, and activated by ship. They are advisory only and cannot hard block a project task.

## Adapter performance guide

Adapter execution time varies significantly. Timeout guides and per-adapter ceilings are in `docs/adapter-config.md` (including Cursor). When orchestrating or benchmarking multi-adapter workflows, use those values.

If an adapter exceeds the safety ceiling, terminate the process and record the timeout in `implementation-notes.md` as a blocker. Do not silently wait indefinitely.

## Procedure

1. Detect the adapter environment (see `docs/adapter-config.md`).
2. If the user provides a slash command, route to the matching stage skill.
3. If the user provides a free-form request, run `/forgeflow:clarify` to produce a brief with route selection.
4. After clarify, follow the route's stage sequence (see Route model above).
5. Each stage skill handles its own procedure, artifacts, and gates.
6. If `--auto` flag is present, stage skills auto-chain to the next stage without `(y/n)` prompts. See `_shared/automation.md` for chain sequence and auto-break conditions.

## Exit Condition

- The routed stage skill completes and reports its own exit condition.
- For free-form requests, the workflow ends when `/forgeflow:ship` completes or the user explicitly stops.

## Strict response constraints

→ `_shared/discipline.md`.

## Constraints

The rules below are hard boundaries. Violating any of them undermines the ForgeFlow contract.

## Rules

1. Start with clarify unless the user provides a complete brief.
2. Pick the smallest route that honestly covers the risk.
3. Do not skip plan for medium or high work.
4. Do not merge spec and quality review passes into one turn for high/epic work.
5. Do not treat the implementer's own summary as approval.
6. Keep state in artifacts/files, not just chat history.
7. Each plan step implements only its own scope. Do not implement future steps early.
8. The review stage is read-only verification.
   Do not use Write or Edit during review.
   Record required fixes in `review-report.md` findings and hand back to the worker.
9. Project active evolution rules are required constraints when their trigger and application stage match.
   Global evolution rules are advisory only.

## Operator prompts

Small task:

```text
Use ForgeFlow. Clarify this request, choose the route, execute the smallest safe change,
then state what evidence justifies review and finalize.
```

Medium task:

```text
Use ForgeFlow. Clarify first, select the route, write a concrete plan with expected artifacts and verification,
then execute only after the plan is clear.
```

Large/high route task:

```text
Use ForgeFlow. Treat this as high route. Clarify, plan, execute,
run spec and quality review passes separately on review-report.md, and call out residual risk before finalize.
```

Epic/massive scale task:

```text
Use ForgeFlow. Treat this as an epic. Clarify, plan with epic decomposition,
then for each milestone: plan, execute, and review. Track progress in roadmap.md.
```
