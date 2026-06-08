---
name: forgeflow
description: Artifact-first delivery workflow for multi-stage implementation or refactor work. Use for /forgeflow, /forgeflow:<stage>, "ForgeFlow", staged workflow, artifact-backed delivery, or 구현/리팩토링/체계적/단계별/검증 when the user wants clarify → plan → execute → review → ship with Markdown artifacts and gates. Not for quick fixes, single-file edits, or simple lookups.
version: 1.12.1
intent: Route user requests through staged ForgeFlow workflow (clarify → plan → execute → review → ship)
inputs: User request text, /forgeflow command, stage invocation, ~/.forgeflow/projects/<project-slug>/defaults.md
outputs: Routed execution to appropriate stage skill, task workspace bootstrap
author: gimso2x
validate_prompt: |
  Must route to correct stage skill based on user input.
  Must read <storage-root>/defaults.md when present for auto/isolation settings.
  Must resolve template root before reading any template.
  Must not invent artifact structure when templates are missing.
  Must follow route model (small/medium/high/epic) for stage sequencing.
  Must route work through explicit ForgeFlow stages and artifact-backed gates.
  Must preserve stage boundaries, verification evidence, and independent review semantics.
  Must not treat ForgeFlow as a chat-only ritual when task artifacts are required.
dependencies:
  - skills/_shared/discipline.md
  - skills/_shared/automation.md
  - skills/_shared/context-resume.md
  - docs/adapter-config.md
  - docs/advisory-guidelines.md
  - templates/brief.md
  - templates/plan.md
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
- Claude: expect structured reports, but prefer bullet/list artifacts over Markdown tables unless a compact matrix is clearly easier to scan.
- Cursor: use slash names without `:` (`/clarify`, not `/forgeflow:clarify`); resolve templates per Template resolution below

Adapter-specific CLI flags and timeout guides: `docs/adapter-config.md`.

## Slash-style entrypoints

| Stage | Claude / Codex / Gemini | Cursor |
|-------|-------------------------|--------|
| Overview | `/forgeflow` | `/forgeflow` |
| Clarify | `/forgeflow:clarify` | `/clarify` |
| Plan | `/forgeflow:ff-plan` | `/ff-plan` |
| Execute | `/forgeflow:execute` | `/execute` |
| Review | `/forgeflow:ff-review` (pipeline: after execute; standalone: with URL/repo/diff/files input) | `/ff-review` (same) |
| Ship | `/forgeflow:ship` | `/ship` |
| Config | `/forgeflow:ff-config` | `/ff-config` |
| Loop | `/forgeflow:ff-loop <task>` | `/ff-loop <task>` |
| Init (full) | Select `full init` inside `/forgeflow:ff-config` | Select `full init` inside `/ff-config` |
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
5. Always write task artifacts under the resolved `<task-dir>` (`~/.forgeflow/projects/<project-slug>/tasks/<task-id>/`), never under a plugin install or cache directory.

## Script resolution (all adapters)

Skills reference scripts like `scripts/forgeflow_fact_store.py`. Resolve the script root before executing any script:

1. If `<workspace>/scripts/forgeflow_fact_store.py` exists (developing ForgeFlow itself), use `<workspace>/scripts/`.
2. Otherwise search for the ForgeFlow plugin `scripts/` directory (first match wins):
   - `~/.cursor/plugins/local/forgeflow/scripts/`
   - Any `~/.cursor/plugins/**/forgeflow/scripts/`
   - Any `~/.claude/plugins/cache/forgeflow/**/scripts/`
   - Any path under `.codex/plugins` that ends with `forgeflow/scripts/`
3. When a script root is found, run `python3 <script_root>/forgeflow_fact_store.py` using the resolved absolute path.
4. If no script root is found, skip the script-dependent feature and record a bounded assumption in the artifact. Do not fail the pipeline.

Scripts included in ForgeFlow:
- `forgeflow_fact_store.py` — Memory Bank fact store (L4)
- `forgeflow_evolution_promote.py` — SOFT→HARD rule promotion (L5)
- `forgeflow_hook_check.sh` — Hard rule verification for hooks (L5)
- `telemetry_collect.py` / `telemetry_aggregate.py` — Telemetry collection

## Init intelligence

When `/forgeflow:clarify` or full init creates drafts, it should ground the brief in the current repository rather than a generic task template:

- Infer project type from durable markers such as `package.json`, framework config files, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml`, app/router directories, and test/build scripts.
- Record the inferred shape as user-facing categories: user-facing app, API/service, dev tool/library, or infrastructure.
- Detect task domains and change type from the objective (frontend, backend, data, auth, infra, testing, security; feature, bugfix, refactor, migration, security, testing).
- Reflect domain/project hints in `brief.md` WHERE, constraints, acceptance criteria, and verification gates without inventing files or framework facts not seen in the repo.

## Input

- User request or issue
- Target repository/path
- Constraints, acceptance criteria, and risk notes if available
- Existing artifacts if the task is already in progress

## Route model

- `small`
  - Stages: clarify -> execute -> ship (3-stage, review skipped)
  - When: 1-2 files, low risk, easy rollback
  - **Review skip condition**: execute stage must end with a self-verify pass against brief.md Goal Contract evidence criteria. If self-verify fails or Goal Contract evidence is ambiguous, fall back to full 4-stage (clarify -> execute -> review -> ship) and warn the user.
  - **User advisory**: after ship, recommend manual review for any concern.
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

All artifacts are Markdown files written to `<task-dir>`:

- `brief.md` — clarified objective, constraints, risk, route (template: `templates/brief.md`)
- `plan.md` — task decomposition with steps, verification, contracts (template: `templates/plan.md`)
- `implementation-notes.md` — real-time execution log (template: `templates/implementation-notes.md`)
- `ledger.md` — unified plan items + execution tracking (template: `templates/ledger.md`, schema: ledger/v1)
- `checkpoint.md` — tactical resume pointer (template: `templates/checkpoint.md`); **read first on stage resume** after context refresh
- `review-report.md` — independent review result (template: `templates/review-report.md`; high/epic uses spec then quality passes on this file)
- `roadmap.md` for epic route: milestone DAG and statuses (template: `templates/roadmap.md`)
- `ship-summary.md` — final handoff summary (template: `templates/ship-summary.md`)
- `eval-record.md` — reusable learnings for high/epic routes (template: `templates/eval-record.md`)
- Evolution rule candidates and active rules live under the **global storage root** `<storage-root>/evolution/` using `templates/evolution-rule.md` — not as a standalone task artifact unless copying a snapshot for reference. Project-scope active rules live under `<storage-root>/evolution/active/` (resolved via `forgeflow_storage.py`), not under `<repo>/.forgeflow/evolution/`.

## Status analysis before routing

Before choosing the next stage for an existing task, inspect the active task directory.

1. Read `checkpoint.md` first when present (`Minimum Read Set`, `Next Action`, `Blockers`).
2. Read `ledger.md` for task status truth; `implementation-notes.md` Reader Summary for narrative.
3. Check `review-report.md` Verdict and Open Blockers when review has run.

→ Context refresh/resume rules: `_shared/context-resume.md`

## File write and output discipline

→ Core rules: `_shared/discipline.md`.

When artifacts are mentioned without an explicit path, assume `<task-dir>`, not chat-only fallback.

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
4. **Model binding**: When the shell supports role-specific model selection, use capability-appropriate models. ForgeFlow declares model **tiers** by stage — adapters translate tiers to concrete models based on available providers.

   **Stage Model Tiers (declarative):**

   | Stage | Tier | Rationale |
   |---|---|---|
   | clarify | reasoning | Ambiguity resolution needs strong inference |
   | ff-plan | reasoning | Plan quality directly affects all downstream stages |
   | execute | coding | Implementation benefits from coding-optimized models |
   | ff-review | reasoning | Independent verification needs strong reasoning, not coding speed |
   | ship | fast | Mechanical commit/tag/changelog — no reasoning needed |

   - `reasoning` = strongest reasoning model available (e.g. Claude Opus, o3)
   - `coding` = coding-optimized model (e.g. Claude Sonnet, GPT-4.1)
   - `fast` = cheapest/fastest acceptable model (e.g. Haiku, Mini)

   Adapters should respect tier hints when model selection is available, but **must not** block or fail if a tier cannot be satisfied — fall back to the default model silently.
   The artifact contract records the role boundary; it does not require a central model database.

   **Auto-escalation rules** (applied by ff-loop and stage skills):

   | Condition | Action |
   |-----------|--------|
   | 2+ consecutive retry failures at same tier | Escalate one tier up (fast → coding → reasoning) |
   | 2+ consecutive stage successes at escalated tier | Downgrade back to original tier |
   | Tier ceiling reached (reasoning) | No further escalation; record in implementation-notes.md |

   Record tier changes in `implementation-notes.md` → Decisions:
   ```
   [tier-escalation] stage=<name> tier=<from>→<to> reason=<2 consecutive failures> retry=<N>
   ```

   This prevents retry loops at an insufficient tier while avoiding unnecessary cost when a lower tier succeeds.

## Execution Patterns

Different routes use different execution strategies: producer-reviewer (default), pipeline (sequential gates), fan-out/fan-in (parallel workers for high/epic). Review depth scales by route.

→ Pattern details, worktree isolation, fan-in gates, route pattern selection, and review depth table: [`references/execution-patterns.md`](references/execution-patterns.md)

## Evolution rule flow

ForgeFlow turns repeated patterns and mistakes into Markdown rules during the **ship** stage, which runs in all routes (small, medium, high, epic):

- `observe`
  - Trigger: ship reviews task artifacts and identifies reusable patterns with concrete evidence
  - Artifact/location: `implementation-notes.md`, `review-report.md`, `eval-record.md` (if high/epic)
- `extract` (ship)
  - Trigger: reusable pattern found with evidence, not covered by existing active rules
  - Artifact/location: evolution rule written directly to `active/`:
    - `Scope: global-advisory` → `~/.forgeflow/evolution/active/<rule-name>.md` (default)
    - `Scope: project` → `<storage-root>/evolution/active/<rule-name>.md` (project-specific only, resolved via `forgeflow_storage.py`)
  - No separate propose→validate cycle needed — review already validated the work
- `active`
  - Trigger: rule file exists in an `active/` directory
  - Loaded by future `clarify`, `plan`, and `execute` when trigger/stage match
- `retired`
  - Trigger: rule becomes harmful, obsolete, or too noisy
  - Artifact/location: `.forgeflow/evolution/retired/` (project) or `~/.forgeflow/evolution/retired/` (global) with reason
  - Next state: not loaded

Global rule candidates may be recorded by long-run. Ship materializes proposed global rule artifacts in `~/.forgeflow/evolution/`, supports review in place, and activates approved rules. They are advisory only and cannot hard block a project task.

## Adapter performance guide

Adapter execution time varies significantly. Timeout guides and per-adapter ceilings are in `docs/adapter-config.md` (including Cursor). When orchestrating or benchmarking multi-adapter workflows, use those values.

If an adapter exceeds the safety ceiling, terminate the process and record the timeout in `implementation-notes.md` as a blocker. Do not silently wait indefinitely.

## Procedure

1. Detect the adapter environment (see `docs/adapter-config.md`).
2. **Read project defaults**: if `<storage-root>/defaults.md` exists in the project root, parse it for default settings. Supported fields: `auto` (bool), `isolation` (bool). See `docs/adapter-config.md` → Project Defaults.
3. **Handle `/forgeflow:ff-config`** (or `/ff-config` in Cursor): interactive project defaults manager (`--mode=full` for architecture draft generation via `templates/project-draft.md`).
   1. Read `<storage-root>/defaults.md` if it exists. Show current settings. When missing, use hardcoded defaults: `auto: false`, `isolation: true`.
   2. Present available options with current values:
      ```
      ForgeFlow 설정

      1. auto (자동 체이닝)       — 현재: 꺼짐   (기본값: 꺼짐)
      2. isolation (worktree 격리) — 현재: 켜짐   (기본값: 켜짐)
      3. init (기본 scaffolding) — <storage-root>/defaults.md 생성
      4. full init (프로젝트 컨텍스트 draft) — <storage-root>/project-draft.md 생성/갱신
      5. prune (고아 워크트리 정리) — 현재: N개
      6. 종료

      번호를 선택하세요:
      ```
   3. On selection 1 or 2, toggle the value (off→on, on→off). Create or update `<storage-root>/defaults.md`. Confirm the change.
   4. On selection 3, run the basic init flow from `skills/ff-config/SKILL.md` Mode C.
   5. On selection 4, run the full project context init flow from `skills/ff-config/SKILL.md` Mode B to detect project context and generate `<storage-root>/project-draft.md` from `templates/project-draft.md`.
   6. On selection 5, run the prune flow from `skills/ff-config/SKILL.md` Mode D.
   7. Supported fields: `auto` (`true`/`false`), `isolation` (`true`/`false`). Additional fields may be added in future versions.
   8. Do **not** commit `<storage-root>/defaults.md` or `<storage-root>/project-draft.md` to git automatically — let the user decide.
4. If the user provides a slash command (other than ff-config), route to the matching stage skill.
5. If the user provides a free-form request, run `/forgeflow:clarify` to produce a brief with route selection.
6. After clarify, follow the route's stage sequence (see Route model above).
7. Each stage skill handles its own procedure, artifacts, and gates.
8. Auto-chain priority: `--auto` CLI flag > `brief.md` `auto: true` > `<storage-root>/defaults.md` `auto: true` > default (`false`). When auto-chain is active, stage skills proceed without `(y/n)` prompts. See `_shared/automation.md` for chain sequence, **Strict auto-chain mode** checklist, and auto-break conditions.
9. **Full loop mode**: use `/forgeflow:ff-loop` for the complete lifecycle loop — auto-chain plus retry, re-execution on review changes, route promotion, and re-plan on scope drift in a single invocation. See `skills/ff-loop/SKILL.md`.

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

Route-specific prompt templates for invoking ForgeFlow.

→ Small, medium, high, and epic operator prompts: [`references/execution-patterns.md`](references/execution-patterns.md#operator-prompts)
