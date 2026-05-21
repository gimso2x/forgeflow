---
name: clarify
description: Turn a vague request into a scoped ForgeFlow brief and route decision. Bootstraps task workspace if missing. Use when the user types /clarify or /forgeflow:clarify, or first for new implementation/refactor/debug requests unless the user already provided a complete brief.
version: 0.4.0
author: gimso2x
intent: "Analyze the user request, repository context, route, specialists, and verification gates, then write a scoped brief."
inputs:
  - user_request: string
  - target_repository: path
  - constraints: markdown
  - task_id: string (optional; auto-generated if omitted)
outputs:
  - brief.md: artifact
dependencies:
  - templates/brief.md
  - skills/_shared/discipline.md
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must return a clear route or brief artifact only when the prompt asks for it.
  Must default to artifact-first behavior and write `brief.md` to the active task directory unless the user explicitly requests dry-run or no-write output.
  Must include WHERE/risk grounding for non-trivial work when artifact writing is allowed.
  Must create `.forgeflow/tasks/<task-id>/` if it does not already exist.
  Must not overwrite existing task artifacts.
---

# Clarify

Use this skill to convert a raw request into a ForgeFlow context brief (`brief.md`) and route decision.

## Input

- Raw user request
- Target repository/path if known
- Constraints, acceptance criteria, risk notes if provided
- Existing codebase context if available
- `--task-id`: stable task identifier (optional; auto-generated if omitted)

## Task ID generation

When `--task-id` is not provided and no active task directory exists, generate one using this pattern:

```
<type>-<short-slug>-<3-char-hash>
```

- `type`: feature, fix, refactor, docs, or task
- `short-slug`: 2-4 word kebab-case slug derived from the objective
- `3-char-hash`: first 3 characters of a timestamp-based hex string

Example: `feature-auth-redir-a3f`

Check that `.forgeflow/tasks/<task-id>/` does not already exist. If it does, append a numeric suffix.

Plugin-cache/extension-cache safety rule: never create task artifacts under a path containing `.claude/plugins/cache`, `.codex/plugins`, `.cursor/plugins`, `~/.cursor/plugins/local`, `.gemini/extensions`, `~/.gemini/extensions`, or any plugin marketplace/cache/extension directory. If the working directory resolves to a plugin install/cache/extension directory and the user did not provide `--task-dir`, stop and ask for an explicit `--task-dir` instead of writing there.

## Output Artifacts

Write `brief.md` to the active task directory using `templates/brief.md` as the structure. The brief must capture:

- Objective (one-sentence goal)
- WHERE/context grounding for non-trivial work
- In Scope / Out of Scope boundary
- Constraints
- Acceptance Criteria
- Risk Level
- Assumptions (including bounded assumptions for non-blocking unknowns)
- Open Questions (blocker vs non-blocking)
- Specialists (required, skipped, skip rationale)
- Verification Gates (auto-detected from tech stack)
- Environment Notes (git status, dependency check, tech stack detected)
- Route selection and rationale
- Route Sub-band (`medium-light` | `medium-full` | `n/a`) when route is medium

## Exit Condition

- The request has a clear goal and scope boundary
- True blocker questions are answered; non-blocking unknowns are recorded as bounded assumptions
- A route is selected and justified
- Next skill is named:
  - `small` -> `/forgeflow:execute` or direct execute path
  - `medium` -> `/forgeflow:plan`
  - `high` -> `/forgeflow:plan` with spec/quality review kept separate
  - `epic` -> `/forgeflow:plan` (plan includes epic decomposition)

## Constraints

## File write and output discipline

→ Core rules: `_shared/discipline.md`.

Follow the user language rules there: write user-facing replies and artifact prose in the user's primary language, while preserving canonical English labels, commands, paths, artifact filenames, and enum values.

Write `brief.md` under `.forgeflow/tasks/<task-id>/`. If the task directory is missing, create it first. Do not return a pseudo-brief in chat only when the workflow expects artifacts.

## Strict response constraints

→ Core rules: `_shared/discipline.md`.

When the user requests an exact output (label only, list only, dry run), return exactly that — nothing extra.

- Label-only route: output exactly `small`, `medium`, `high`, or `epic` and stop.
- Exact-count questions: start directly with `1.` — no preamble.
- List questions: list them inline. Do not call interactive tools unless the user asks.

## Context resume and compact safety

→ `_shared/context-resume.md`.

- **Minimum read set (new task)**: user request + repo context as needed for scope.
- **Minimum read set (resume)**: `checkpoint.md` → `brief.md` in-progress sections only.
- **Stage exit**: update `checkpoint.md` with Current Stage, Next Action, Minimum Read Set. Safe to `/compact` after brief + checkpoint are written.
- Do not compact mid-interview before `brief.md` is complete.

## Evolution preflight

Unless the prompt is exact-output, label-only, dry-run, or says not to inspect files, check evolution rules before route selection:

1. Load project active rules from `.forgeflow/evolution/active/*.md` if the directory exists.
2. Load global advisory rules from `~/.forgeflow/evolution/active/*.md` if available.
3. Match rules by their `Trigger` and `Application Stage` fields.
4. Record matching rules in the brief's `Applied Evolution Rules` section.
5. Project active rules are required constraints for this repository. Global rules are advisory only: they may guide clarify/plan, but they must not block or force hard enforcement.
6. If a project active rule conflicts with the user request, surface it as a blocker question with a recommended resolution.

This is how ForgeFlow learns from prior work: long-run proposes rules, review validates them, active rules are loaded automatically by future clarify/plan/execute stages.

## WHERE grounding

Before routing anything non-trivial, calibrate WHERE so intake is neither too heavy for toys nor too light for dangerous work.

Capture these dimensions in the brief when the user has not already provided them:

- **project_type**: user-facing app, API/service, dev tool/library, or infrastructure
- **situation**: greenfield, brownfield extension, brownfield refactor, or hybrid
- **ambition**: toy/experiment, feature/MVP, or product
- **risk_modifiers**: sensitive data, external exposure, irreversible ops, high scale

Risk escalation rules:

- Sensitive data -> security and data requirements must be deep.
- External exposure -> security and access requirements must be deep.
- Irreversible ops -> risk and compatibility requirements must be deep.
- High scale -> infrastructure and architecture requirements must be deep.

Situation rules:

- Greenfield: ask enough to define behavior and core architecture, but do not invent enterprise ceremony.
- Brownfield extension: inspect existing code and docs before asking factual questions; ask about decisions and tradeoffs, not facts the repo can answer.
- Brownfield refactor: compatibility, callers, migration path, and rollback are first-class requirements.
- Hybrid: separate new-module behavior from integration constraints.

For exact-count, dry-run, or response-only prompts, do not force the WHERE interview. Obey the requested output exactly.

## Procedure

1. **Bootstrap task workspace if missing**: If no active task directory exists (no `.forgeflow/tasks/<task-id>/` found), generate a task ID (see Task ID generation above) or use `--task-id` if provided, and create `.forgeflow/tasks/<task-id>/`. Do not overwrite if `brief.md` already exists — report that it was kept as-is.

2. Inspect relevant repo context before inventing scope.
   - Run the Evolution preflight first when allowed, then map matched rules into brief.md.
   - Map Instructions, Tools, Environment, State, and Feedback into brief fields. Use Environment Notes, tech stack, Open Questions, and Verification Gates for missing context instead of creating a separate harness artifact.
   - If an Environment or Tools gap prevents execution, add it to Open Questions as a blocker and ask before routing to plan or execute.
   - **Gemini optimization**: Leverage Gemini's ability to run parallel tool calls. When exploring the codebase, batch multiple `ls`, `grep`, or `cat` operations into a single turn to minimize latency.
   - Surface confusion instead of guessing. If the request has competing interpretations that materially change scope, say so in the brief.
   - For brownfield refactors or extensions, specifically identify **architectural friction**: where are modules **shallow** (interface as complex as implementation), where is **locality** missing, and where are **pass-throughs** bloating the path?
   - Do not silently pick one interpretation when the ambiguity affects user-visible behavior, data, security, or files to edit.
   - **Environment preflight**: Run these checks and record results in the Environment Notes section of brief.md:
     - `git rev-parse --show-toplevel 2>/dev/null` -> confirm the correct git root matches the target project directory. If mismatched, note the warning.
     - `git rev-parse --is-inside-work-tree 2>/dev/null` -> if not a git repo, note the warning.
     - Check for lockfile + dependency directory mismatch (e.g., `pnpm-lock.yaml` exists but no `node_modules`): add to Open Questions: "종속성이 설치되지 않았습니다. execute 전에 설치를 진행하시겠습니까?"
     - If neither lockfile nor dependency directory exists: new project, skip silently.
   - **Tech stack detection**: Auto-detect the framework/build tool from project files and record in brief.md. Check for:
     - `package.json` -> read dependencies for framework signals (next, react, vue, svelte, nuxt)
     - `pyproject.toml` or `requirements.txt` -> Python (FastAPI/Django/Flask)
     - `Cargo.toml` -> Rust
     - `go.mod` -> Go
     - If detected tech stack contradicts the user's request, add to Open Questions as a blocker.

2. Establish WHERE grounding unless the prompt is an exact-output dry run.

3. Ask up to 5 clarifying questions when they materially improve requirements. Ask 0 if the request is already actionable, and do not pad the list with nice-to-have trivia.
   - Good questions resolve product behavior, user/audience, success criteria, data/source of truth, rollout/risk constraints, or explicit out-of-scope boundaries.
   - Bad questions ask for implementation chores the agent should infer from repo inspection, preferences that do not change the plan, or confirmations that can be recorded as bounded assumptions.

4. Apply Socratic clarification (the "grilling loop") before route selection:
   - Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.
   - For each question asked, provide your recommended answer to reduce user cognitive load.
   - If a question can be answered by exploring the codebase, explore the codebase instead of asking.
   - Name the hidden assumptions the request appears to rely on.
   - Separate true blocker questions from non-blocking unknowns.
   - State explicit non-goals and scope boundaries before planning.
   - Assign an ambiguity score from `0.0` to `1.0`; above `0.2`, either ask blocker questions or record why execution can proceed safely with bounded assumptions.
   - Do not let ambiguity disappear into prose. It must be visible in the brief artifact or response artifact.

5. Score complexity using the documented weighted model:
   ```text
   raw_score = file_count*1.0 + estimated_lines*0.1 + requirement_count*2.0 + dependency_count*1.5 + risk_keywords*3.0
   ```
   - `< 10`: `small` — one localized change, usually 1-2 files, low ambiguity, no cross-cutting behavior.
   - `10-16.9`: `medium-light` — several coordinated files/components, scoped state/layout/navigation, moderate test/update surface, but no security/data migration/infra rollback risk.
   - `17-24.9`: `medium-full` — cross-module or service-level changes that still avoid high-risk auth/security/data/infra boundaries.
   - `25-49.9`: `high` — auth/security, data migration, payments, production infra, irreversible data changes, broad architecture migration, or many contracts/journeys requiring separate spec and quality review.
   - `>= 50`: `epic` — massive scope, hierarchical milestone breakdown, multi-week effort.

   **Scoring Calibration**:
   - `file_count`: Count of existing files to modify + new files to create.
   - `estimated_lines`: Total net change in lines (additions + modifications).
   - `requirement_count`: Number of distinct items in the Acceptance Criteria list.
   - `dependency_count`: Number of external libraries or internal modules impacted.
   - `risk_keywords`: Presence of keywords like `auth`, `payment`, `migration`, `security`, `infra`, `delete`.

   **WHERE Route Calibration**: After computing `raw_score`, apply WHERE-based adjustments before selecting the final route. These prevent over-routing simple tasks in toy/experiment projects or under-routing complex tasks in production systems.

   - `ambition = toy/experiment` AND no risk modifiers checked → downgrade one tier (e.g. `medium-light` → `small`, `high` → `medium`), but never downgrade below `small`.
   - `ambition = product` AND any risk modifier checked → upgrade one tier (e.g. `medium-full` → `high`), but never upgrade above `epic`.
   - `situation = greenfield` AND `ambition = toy/experiment` → maximum route is `medium`; if `raw_score >= 25`, keep at `medium` and note the cap in route rationale.
   - Record the calibration in the brief's Route Rationale section (e.g. "raw_score 17 → medium-light, but WHERE calibration (ambition=toy, no risk modifiers) downgrades to small").

   Return route label `medium` for both `medium-light` and `medium-full`; record the sub-band in route rationale. The `17.0` mid threshold exists to decide how deep the plan/review detail should be inside the medium route, not to create a separate slash route.

6. Apply alias hints only within the scoring context. The table below maps user wording to `suggested_next_skill` — Keyword hints are advisory and must not auto-invoke any skill. Route selection (`small`/`medium`/`high`/`epic`) remains explicit and independent of alias hints. Do not auto-invoke skills from keyword detection alone.

   | User wording | Hint |
   |--------------|------|
   | "리뷰해줘", "review this", "audit" | Prefer `/forgeflow:review` when artifacts or a diff already exist; otherwise clarify first. |
   | "계획 세워", "plan this", "break down" | Prefer `/forgeflow:plan` after brief is complete. |
   | "버그", "fix", "debug", "깨짐" | Prefer execute then review; escalate route when risk keywords appear. |
   | "릴리즈", "ship", "배포" | Prefer `/forgeflow:ship` only after review evidence exists. |
   | "대규모", "milestone", "epic" | Consider `epic` and `/forgeflow:plan` with epic decomposition; do not force it without scope evidence. |

7. Select specialists based on task nature:
   - Auth/Encryption/External Input -> `security-review`
   - UI/Accessibility/User Flow -> `ux-review`
   - Response time/Memory/Large data -> `perf-review`
   - Frontend focused -> `frontend-execute`
   - Backend/API/DB -> `backend-execute`
   - Infra/Deployment/IaC -> `infra-execute`
   - List skipped specialists and provide a skip rationale.

8. Set verification gates in the brief:
   - `small`: at least one of `build`, `lint`, or `type_check` — whichever is available and fastest.
   - `medium`: at least `lint` and `type_check`, plus `test` if tests exist for changed files.
   - `high`: full verification suite — `build`, `lint`, `type_check`, and `test`.
   - `epic`: full verification suite, plus milestone-level integration tests.

9. State the route and why, unless an exact-output/label-only instruction applies.

10. Produce `brief.md` using `templates/brief.md` as the structure, unless an exact-output/label-only instruction applies.

11. If the request is actionable, record remaining non-blocking unknowns as bounded assumptions and make the next stage obvious without asking the user to do your planning work, unless an exact-output/label-only instruction applies.

Do not implement here. Clarify is the intake gate, not the coding phase.

## Contract-first traceability for medium/high/epic or brownfield work

For non-trivial work, identify cross-module contracts before route selection:

1. Identify interfaces, invariants, data shapes, and compatibility constraints that parallel workers must not break.
2. If any contract exists, note it in the brief's Constraints section.
3. Record `fulfills` targets for traceability.
4. Identify journeys (multi-step user or system flows that require end-to-end verification).
5. Preserve non-goals and bounded assumptions when they affect execution boundaries.

Small documentation-only tasks may omit these.

## Auto-detectable verification gates

When constructing verification gates, prefer automated gates over manual review wherever possible.

| Gate | Description | Applicable when |
|------|-------------|-----------------|
| `scope_boundary_check` | Verify no unintended files changed via git diff | All tasks |
| `contract_check` | Verify step output against stated contracts | Tasks with cross-module contracts |
| `version_consistency_check` | Verify version strings match across artifacts | Tasks referencing package versions |
| `build` | Build passes | Code tasks |
| `lint` | Linter passes | Code tasks |
| `type_check` | Type checker passes | Typed code tasks |
| `test` | Test suite passes | Code tasks with tests |

## UX guardrails

The goal is to gather just enough information to route correctly — not to run an interrogation. The user came to build something, not to fill out forms.

- Inspect the repo before saying the scope is unclear. Most factual questions can be answered by reading code.
- Don't manufacture open questions to prolong intake. Non-blocking unknowns go into the brief as bounded assumptions.
- Don't ask the user to write the plan for you. That's your job.
- If the request is already actionable, skip directly to route selection and brief output.
- Stop at the stage boundary. Do not proceed to plan/execute without user confirmation.

**Blocker handling**: If brief.md has unresolved blockers, present each one to the user with your recommended answer. Wait for their response. Update the brief. Only then close the stage.

When all blockers are resolved:

**If `--auto` is active** (see `_shared/automation.md`): skip the prompt and invoke the next stage skill directly.
- `small` → `/forgeflow:execute`
- `medium` or `high` → `/forgeflow:plan`
- `epic` → `/forgeflow:plan`

**Otherwise**, end with a route-specific next step:
- `small`: `요구사항 충분. small route입니다. 다음 스텝으로 /forgeflow:execute을 진행하시겠습니까? (y/n)`
- `medium` or `high`: `요구사항 충분. <route> route입니다. 다음 스텝으로 /forgeflow:plan을 진행하시겠습니까? (y/n)`
- `epic`: `요구사항 충분. epic route입니다. 다음 스텝으로 /forgeflow:plan을 진행하시겠습니까? (y/n)`

## Output mode examples

For label-only requests like `/forgeflow:clarify Add a README badge. Return only the selected route label.`:
Return exactly one of `small`, `medium`, `high`, or `epic`. No explanation, no file writes.
