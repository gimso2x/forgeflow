---
name: ff-plan
description: Create an executable ForgeFlow plan with exact tasks, files, acceptance criteria, and verification steps. Includes epic decomposition for epic route. Use when the user types /ff-plan or /forgeflow:ff-plan. Also use when the user says 'make a plan', 'break this down', 'decompose tasks', 'plan this out', plan 만들어, tasks 나눠, or 분해 for implementation work. Not for general scheduling, meeting agendas, or non-implementation planning.
version: 0.6.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must default to artifact-first behavior and produce `plan.md` in the active task directory unless the user explicitly requests dry-run or no-write output.
  Must run check-plan guard before exiting the stage.
  Must keep contracts, fulfills, journeys, and verify_plan consistent when present.
  Must include contract-first traceability for medium/high/epic or brownfield work.
  Must support refactor mode with requirement traceability when brief indicates refactoring.
  For epic route, must produce `roadmap.md` conforming to `templates/roadmap.md` format with measurable success criteria per milestone and integration verification as final node.
dependencies:
  - skills/_shared/isolation.md
  - skills/_shared/discipline.md
  - skills/_shared/automation.md
  - skills/_shared/context-resume.md
  - skills/_shared/verification-gates.md
  - skills/_shared/role-critic.md
---

# Plan

Use this skill to turn a ForgeFlow brief or requirements document into an executable task plan.

## Reference inventory

- [references/epic-decomposition.md](references/epic-decomposition.md) — epic roadmap decomposition, milestone DAG, and integration verification guidance.

## Input

- `brief.md` from `/forgeflow:clarify`
- Codebase context
- Shared project context from `<storage-root>/project-draft.md` when present
- Route selected by `/forgeflow:clarify`

## Output Artifacts

Write `plan.md` to the active task directory using `templates/plan.md` as the structure. The plan must capture:

- Route
- Dependencies (what must exist before execution starts)
- Tasks with: objective, exact files, dependencies on other tasks, expected output, verification, fulfills (which acceptance criteria)
- Reviewer-facing Design Intent: problem framing, chosen approach, alternatives considered, intentional exclusions, and review focus
- Task-specific Review Criteria: applicable conventions, relevant decisions/ADRs, acceptance traces, risk checks, and out-of-scope checks
- Verification Plan with typed targets and gates
- Contracts (interfaces, invariants) when applicable
- Journeys (end-to-end flow verification) when applicable
- Parallelism notes (which tasks can run concurrently)

Also create empty scaffolds for the execute stage to fill:
- `implementation-notes.md` (from `templates/implementation-notes.md`) — decisions, deviations, evidence
- `ledger.md` (from `templates/ledger.md`, schema: ledger/v1) — unified plan items + execution tracking
- `run-state.json` (create with `python3 <forgeflow-checkout>/scripts/forgeflow_storage.py --project-dir <repo-root> --task-id <task-id> --write-run-state` if missing) — `repo_root`, `project_name`, `project_slug`, `storage_root`, `task_id`

Additionally, produce:
- `ledger.md` (from `templates/ledger.md`, schema: ledger/v1) — standardized task ledger with plan items, execution tracking, and decisions.

For **epic** route, also produce:
- `roadmap.md` (from `templates/roadmap.md`) — milestone definitions, dependency DAG, statuses

### Artifact Field Contract

**plan.md** (produced by ff-plan):
- **Required**: route, Goal, Requirements, Implementation Steps, Verification
- **Recommended**: Architecture Notes, Contracts, Journeys

## Medium route sub-band depth

Read **Route Sub-band** from `brief.md` (clarify records `medium-light` or `medium-full` from raw_score; route label stays `medium`).

- **medium-light** (`10-16.9`):
  - Task decomposition and Verification Plan are required.
  - Contracts and Journeys are **optional** unless brownfield extension/refactor or cross-module interfaces are in scope.
  - Default execution pattern: pipeline + producer-reviewer.
  - Parallelism notes only when 2+ independent file groups exist.
- **medium-full** (`17-24.9`):
  - Apply **contract-first traceability** (below) — Contracts and Verification Plan with typed targets are required.
  - Add Journeys when 2+ plan tasks compose an end-to-end flow.
  - Consider fan-out/fan-in in Architecture Notes when 3+ independent file groups exist.

## Dependency minimization for tool/script tasks

When a plan task involves creating a new CLI tool, script, or external service adapter, evaluate whether the full SDK is necessary before adding a dependency. If the required scope is narrow (e.g., simple HTTP calls, JSON-RPC, file I/O) and the runtime built-in API (`fetch`, `readline`, `fs`) can cover it, prefer zero-dependency implementation. Record the decision in the task notes. If future expansion is anticipated, note "SDK 도입 검토" as a follow-up rather than pre-adding the dependency.

## Plan-mode adaptation guardrails

Treat Claude Code's plan-mode behavior as a UX pattern, not an implementation dependency:

1. **Explore before planning**: inspect the brief, active artifacts, relevant source files, templates, and verification conventions before decomposing tasks. Ask the user only for blocker decisions that repo inspection cannot answer.
2. **Artifact-first plan**: write `plan.md` and supporting ledgers as the source of truth. Do not leave the executable plan only in chat.
3. **Approval boundary**: planning stops at the `plan -> execute` boundary unless `--auto` is active. Non-auto plans must end with the closed execute-stage question.
4. **No implementation in plan**: do not edit product/source files while planning, except when the user explicitly asks for a tiny small-route direct execution.
5. **Safe reference policy**: external examples may inspire general interaction patterns, but non-public, leaked, or unofficial source must not be fetched, quoted, copied, or treated as normative. Record this as a constraint when a user provides such a reference.
6. **Readiness check**: before exit, verify Goal, Requirements, Implementation Steps, Verification, scope boundary, dependencies, fulfills, and approval boundary are explicit enough for `/forgeflow:execute` to run without guessing.

## Review intent and criteria

Every plan must include reviewer-facing **Design Intent** and **Review Criteria** sections. These sections make `/forgeflow:ff-review` less generic and prevent reviewers from inventing unapproved scope.

1. Populate **Design Intent** from the brief objective, plan architecture notes, selected approach, rejected alternatives, and explicit non-goals.
2. Populate **Review Criteria** from `brief.md` acceptance criteria, `docs/coding-convention.md` when present, active evolution rules, relevant ADR/architecture docs, and task-specific risk checks.
3. Populate **Simplicity Check** with the minimal solution, rejected abstraction/flexibility, and why this is enough now. Keep speculative extensibility as follow-up, not task scope.
3. If repo policy files such as `docs/adr.yaml`, `docs/adr.md`, `docs/code-convention.yaml`, `docs/coding-convention.md`, or `<storage-root>/evolution/active/*` exist, use only the task-relevant entries and cite repo-relative paths. Do not paste long policy bodies into `plan.md`.
4. For small route, keep both sections compact: 1-3 bullets each is enough.
5. For medium/high/epic, include enough criteria for reviewers to trace findings back to a named acceptance criterion, convention, ADR, active rule, or risk check.
6. Record intentional exclusions explicitly so review findings can distinguish true defects from out-of-scope improvements.
7. For each task, name the surgical scope: why the listed files are necessary and why adjacent refactor is excluded unless explicitly planned.

## Contract-first traceability for medium/high/epic or brownfield work

For non-trivial work, plan the cross-module contract before task decomposition. Apply the **Architecture Glossary** to identify **deepening opportunities** — refactors that turn shallow modules into deep ones:

- **Depth**: Module's interface should be simpler than its implementation. Prefer deep modules (simple API, complex internals) over shallow ones (interface as complex as implementation).
- **Seam**: Identify points where behavior can be changed without modifying existing code (interfaces, dependency injection, strategy patterns). These are natural task boundaries.
- **Locality**: Keep related code together. If a change requires touching many files, consider refactoring for better locality first.

1. Identify interfaces, invariants, data shapes, and compatibility constraints that parallel workers must not break.
2. If any contract exists, write it into the Contracts section of plan.md and/or a sibling `contracts.md` artifact.
3. Add fulfills links on tasks when requirements or sub-requirements are known.
4. Add Verification Plan entries for each fulfilled requirement/sub-requirement and each journey.
5. Add Journeys for multi-step user or system flows that require end-to-end verification.
6. Preserve the clarify-stage non-goals and bounded assumptions in the plan when they affect execution boundaries.

Small documentation-only tasks may omit these sections. If present, they must be internally consistent.

## Auto-detectable verification gates

→ Shared gate definitions: `_shared/verification-gates.md`.

When constructing the Verification Plan, prefer automated gates over manual review wherever the verification can be expressed as a machine-checkable assertion. Use manual review only for qualitative judgments that cannot be automated.

### Available automated gates

| Gate | Description | Applicable when |
|------|-------------|-----------------|
| `screen_count_check` | Verify row counts match expected numbers | Documents with screen/page catalogs |
| `cross_document_consistency_check` | Verify terminology/version consistency across files | Multi-document deliverables |
| `document_validation` | Lint, build, test on document-only workspace | Any documentation task |
| `contract_check` | Verify step output against stated contracts | Tasks with contracts.md |
| `version_consistency_check` | Verify version strings match across artifacts | Tasks referencing package versions |
| `total_preservation_check` | Verify aggregate values (effort, count) unchanged | Tasks with summary totals |
| `scope_boundary_check` | Verify no unintended files changed via git diff | All tasks |

### Gate selection rules

1. **Documentation-only tasks**: Use at least `scope_boundary_check` + `version_consistency_check` or `total_preservation_check` alongside manual review. Do not use manual review as the sole gate.
2. **Code tasks**: Use `contract_check` for every step. Add `screen_count_check` or `cross_document_consistency_check` when the task affects UI catalogs or cross-file references.
3. **Mixed tasks**: Apply documentation gates to documentation steps and code gates (`build`, `lint`, `test`, `type_check`) to code steps.

## Evolution rule application

Before decomposing tasks, read the brief's `Applied Evolution Rules` section and, if command/file inspection is allowed, re-check active rule directories:

- Project active: `<storage-root>/evolution/active/*.md` (resolved via `forgeflow_storage.py`)
- Global advisory: `~/.forgeflow/evolution/active/*.md`

Apply rules this way:

1. Project active rules whose trigger matches the task become plan constraints, verification gates, or explicit non-goals.
2. Global advisory rules may shape the plan but cannot block execution by themselves.
3. If a project active rule changes task ordering, file scope, or verification, record that under `Applied Evolution Rules` in plan.md.
4. If no active rules apply, record `none` instead of silently skipping this section.

## Context resume and refresh safety

→ `_shared/context-resume.md`.

- **high/epic**: `plan.md` MUST include **Reader Summary** within the first ~30 lines.
- **Minimum read set (new)**: `brief.md` Objective, Scope, Acceptance Criteria, Applied Evolution Rules.
- **Minimum read set (resume)**: `checkpoint.md` → brief summary → plan Reader Summary + Tasks + Verification Plan sections.
- **Long plans**: keep section anchors (`## 작업 목록 (Tasks)`, `## 검증 계획 (Verification Plan)`) so execute/review can target tasks without full re-read. Large brownfield tasks may exceed ~300 lines — design for section-targeted resume, not full-document replay.
- **Stage exit**: write `plan.md`, scaffolds (`implementation-notes.md`, `ledger.md`, `run-state.json` if missing), update `checkpoint.md`. Safe to refresh context after checkpoint update.
- Do not refresh context mid-decomposition before minimum plan gate is satisfied.

## Minimum plan gate

Before crossing `plan -> execute`, the plan must make these sections explicit:

- Goal
- Requirements
- Implementation Steps
- Verification

State assumptions and success criteria before proposing tasks. If an assumption changes the implementation path, record it as a bounded assumption or return to `/forgeflow:clarify`; do not hide it inside a task title.

**Testing Principle** (route-aware, → `skills/execute/references/testing-discipline.md`):
- **small**: No test steps in plan. Lint/build verification only.
- **medium**: Do NOT create a dedicated "write failing tests" task. Integrate test writing into the implementation step (test-after). Example: "X를 구현하고 테스트 작성" instead of separate T1=test, T2=impl. **테스트 파일을 plan task의 Files 목록에 반드시 포함한다** (예: `src/features/map/components/map-marker-layer.test.tsx`). 이렇게 하면 execute 단계에서 테스트 파일 추가 시 scope boundary alert가 발생하지 않는다.
- **high/epic**: TDD applies — plan test-first steps for logic/contract changes. Style/config steps use test-after.
"Write failing test" should be its own objective **only** for high/epic logic steps.

## Refactor mode

Use refactor mode inside this existing plan flow when the requested work is primarily a behavior-preserving structural change across an existing public surface, a migration-sensitive internal reorganization, test-sensitive decomposition work, or removal/replacement of implementation machinery while preserving user-visible behavior.

Refactor mode is a planning branch, not a separate stage or command.

When refactor mode applies, the plan must include:

- preserved public behavior statement, or a decision explaining why the refactor is internal-only
- explicit non-goals
- migration boundary
- rollback, escape hatch, or explicit not-applicable note for contained internal refactors
- tiny always-green implementation steps
- regression verification strategy focused on public behavior over implementation-detail tests
- note on whether existing tests cover the affected public behavior

**Deepening strategy**: Apply the **Deletion test** to any module suspected of being shallow. Propose candidates that concentrate complexity rather than just moving it. Aim for high **leverage** (behavior behind a small interface) and **locality** (concentrated knowledge).

Representation rules:

- preserved behavior maps to Requirements, task objectives, fulfills, and Verification Plan
- non-goals live in a plan section named "Non-goals"
- migration boundaries live in a plan section named "Migration boundary", or in Contracts
- rollback or escape hatch lives in each task's notes
- regression verification lives in each task's Verification field and the top-level Verification Plan
- existing test coverage lives in a plan section named "Existing coverage"

### Requirement traceability

For non-trivial work, carry the requirement map through the executable plan instead of leaving it as prose:

- Assign stable requirement IDs (`R1`, `R2`, or `R1.1`) before decomposing implementation steps.
- Each non-trivial step must include fulfills with requirement or sub-requirement IDs when requirements are known.
- Every fulfills target must have a matching Verification Plan entry.
- Every acceptance criterion from the brief must map to at least one requirement ID, step, or verify target; otherwise record it as intentionally out of scope.
- Use `sub_req` for requirement-level targets and `step` only when the verification target is the step itself.
- If a step intentionally has no requirement reference, say why in the plan; do not silently create orphan work.
- If a verification target is not executable, record the limitation and a fallback manual/evidence gate before execution starts.

Do not proceed to `/forgeflow:execute` if one of those is missing for non-trivial work.

### Stage Completion Gate

Before exiting plan, verify artifacts with the guard check script:

```bash
python3 <forgeflow-checkout>/scripts/forgeflow_guard_check.py check-plan --task-dir <task-dir>
```

- **PASS** -> stage complete, proceed to execute or present the plan to the user.
- **BLOCK** -> update `plan.md`/route artifacts, then re-run. Do not exit plan with BLOCK results.
- Label-only / dry-run mode is the only exception because no artifacts are written by design.

## Exit Condition

- Every task has exact file paths or a justified discovery step
- Every task has verification
- Dependencies form a DAG
- Medium/high/epic routes have enough detail for `/forgeflow:execute` without guessing
- The minimum plan gate covers Goal, Requirements, Implementation Steps, and Verification
- Refactor-specific checks are present only when refactor mode applies
- Contract metadata is present for cross-module work, or explicitly unnecessary
- Fulfills, journeys, and Verification Plan links are consistent when present
- No placeholder tasks remain
- For epic route: `roadmap.md` is written following `templates/roadmap.md` format with valid dependency DAG and integration verification milestone
- **Next Steps recorded**: plan.md `Next Steps → execute` section is filled with tasks, verification plan, and known gaps from Self-Critique

## Constraints

## File write and output discipline

→ Core rules: `_shared/discipline.md`.

Follow the user language rules there: write user-facing replies and artifact prose in the user's primary language, while preserving canonical English labels, commands, paths, artifact filenames, and enum values.

Write `plan.md` under `<task-dir>`. If the task directory is missing, bootstrap it first. Do not downgrade planning into a chat transcript when the workflow expects artifacts.

## Strict response constraints

→ `_shared/discipline.md`.

## Automation / non-interactive approval mode

→ `_shared/automation.md`.

## Procedure

### Phase 0: Epic Decomposition (epic route only)

For `epic` route without existing `roadmap.md`: run problem framing, five-angle pressure test, synthesis, and write `roadmap.md`. Skip if `roadmap.md` exists; use `--milestone M2` to plan a specific milestone.

→ Full procedure, pressure test, synthesis heuristics, anti-patterns: [`references/epic-decomposition.md`](references/epic-decomposition.md)

### Phase 1: Load and map

1. Read the brief/requirements fully. Apply Evolution rule application before task decomposition. Map Context Brief fields to plan sections:

   | Brief Field | Plan Mapping |
   |-------------|-------------|
   | Objective | Plan task IDs + step objectives |
   | Scope (In/Out) | Work scope section |
   | Technical Context | Architecture + tech stack + file structure basis |
   | Constraints | Reflected during task decomposition |
   | Applied Evolution Rules | Plan constraints, verification gates, or advisory notes |
   | Acceptance Criteria | Self-review checklist |
   | Open Questions | Recorded as bounded assumptions |

2. Inspect the repo for existing conventions, test patterns, and file structure.

   - If `<storage-root>/project-draft.md` exists in the target project root, treat it as section-scoped shared context produced by `/forgeflow:ff-config init --mode=full`. Read only task-relevant sections such as `Reusable Project Context`, `Documentation Pointers`, `Context Usage Rules`, and `Verification Conventions`. Use those pointers to reduce repeated discovery, but keep `brief.md` and `plan.md` as the task-specific source of truth.
   - When adding resume guidance to `checkpoint.md`, include only the relevant `<storage-root>/project-draft.md` section names or source document paths, not the full common context content. Plans must not depend on copied project-draft prose when a repo-relative source document or code path can be referenced instead.

3. **File Structure Mapping**: Before writing tasks, determine exactly which files will be created or modified:
   - Each file should have one clear responsibility
   - Files that change together should live together
   - Follow existing codebase patterns — don't unilaterally restructure
   - File structure informs task decomposition: each task should produce a self-contained change

### Phase 2: Task decomposition

4. Decompose into small tasks following these heuristics:

   **Parallelism and Dependencies** — design for maximum parallel execution. Tasks require sequential ordering only when:
   - They modify the same file (prevents file conflicts)
   - One task's output is referenced by another (interface dependency)
   - They modify shared state (DB schema, config files)

   Mark each task's dependency status explicitly:
   - `(none)` = parallelizable
   - List of task names = runs after those tasks

   **Worker-Validator Structure** — each task should be executable by an independent worker (subagent) and verifiable by a separate validator:
   - Worker: executes steps exactly as written, no judgments beyond the plan
   - Validator: checks test pass/fail, code quality, spec compliance

   **Execution Pattern Selection** — for high/epic routes, explicitly choose and record the execution pattern in Architecture Notes:
   - **pipeline + producer-reviewer** (default): sequential steps with gates between them. Use when steps have data or state dependencies.
   - **fan-out/fan-in + producer-reviewer**: parallel workers, single reviewer. Use when 3+ tasks touch independent file groups with no shared state.
   - Medium routes default to pipeline. High/epic routes should consider fan-out/fan-in when the plan has 3+ independent parallel tasks.

   **Task Granularity** — each step is one action (2-5 minutes of work):
   - **high/epic TDD steps**: "Write the failing test" — one step; "Write the minimal code to pass" — one step
   - **medium test-after steps**: "Implement X and write tests" — one step (no separate test-first step)
   - "Commit" — one step

5. For every step, write expected output and verification. Never leave a step that assumes "the worker will figure it out."

6. Apply contract-first traceability (see above) for medium/high/epic or brownfield work.

7. For `high/epic` work, pressure-test milestone boundaries from five angles before execution:
   - feasibility risks
   - architecture/interface boundaries
   - dependency ordering
   - regression and recovery risks
   - verification strategy

### Phase 3: Self-review and Self-Critique

8. **Self-review** before presenting to the user:
   - Every requirement from the brief maps to at least one step
   - Every step has fulfills, expected output, verification, and rollback note
   - Dependencies form a valid DAG (no cycles, no orphans)
   - No placeholder tasks remain
   - Verification Plan covers every fulfills target

9. Identify risky tasks and required review evidence.

10. **Self-Critique Loop** (inspired by gajae-code's ralplan pattern):

    After plan.md draft is complete, run an internal **Critic** pass (`skills/_shared/role-critic.md`). Fill the `## Self-Critique` section in `plan.md` (see `templates/plan.md` for the exact field structure) with a **receipt-only verdict**:

    1. **Coverage**: Does this plan satisfy every acceptance criterion and Goal Contract success criteria from brief.md?
    2. **Dependency correctness**: Are there missing dependencies, ordering errors, or file-conflict risks not flagged?
    3. **Verifiability**: Does every verification step produce observable evidence (command output, test results, diff)?
    4. **Risk gaps**: Are there accepted risks from brief.md that the plan does not mitigate or acknowledge?

    **Receipt-only Verdict structure** (fill in `### Self-Critique Verdict`):
    - **Status**: `APPROVE` (all clear) | `ITERATE` (fixable issues) | `REJECT` (fundamental problems)
    - **Findings**: one line per finding, tagged `[HIGH]` or `[LOW]`
    - **Required Changes**: numbered list (only when ITERATE/REJECT)

    When Status is `APPROVE`, skip `### Detailed Findings` entirely — no prose needed.
    When Status is `ITERATE` or `REJECT`, expand findings with evidence in `### Detailed Findings`.

    **Field mapping to `templates/plan.md` Self-Critique section:**
    - Question 1 → `Coverage PASS?`
    - Question 2 → `Dependency PASS?`
    - Question 3 → `Verifiability PASS?`
    - Question 4 → `Risk gaps PASS?`

    **Rules:**
    - If any answer is "no" or "uncertain", revise the plan and re-run Critic (max 3 iterations).
    - Critic PASS condition: all four answers are affirmative with no hedging → Status = APPROVE.
    - Record the final Critic verdict (PASS/revision count) in `Critic verdict` and `Revision count` fields so review stage can see it.
    - If Critic does not pass after 3 iterations, flag the remaining concern in `Open Concerns` field and proceed — do not block planning indefinitely.
    - **Review consumption**: ff-review reads the Self-Critique section. If `Critic verdict` is not `PASS` and no `Open Concerns` are listed, review must flag it as a planning defect.

11. Propose `/forgeflow:execute` as the next stage and stop for explicit user approval.

Do not code during planning unless the user explicitly asks for a tiny small-route direct execution.

### Anti-patterns

| Anti-Pattern | Why It Fails |
|---|---|
| Marking tasks that modify the same file as parallel | File conflicts, unmergeable changes |
| Listing tasks without dependencies | Execution order tangles, interface mismatches |
| Steps that assume "the worker will figure it out" | Worker's arbitrary interpretation -> spec drift |
| Approving a plan with placeholders | Blocked at execution stage, must return to planning |
| Skipping self-review | Missing spec coverage, type mismatches, dependency errors go undetected |
| Writing tasks before mapping files | Task boundaries don't match file boundaries |

## UX guardrails

- Planning owns plan creation; do not ask the user to make the plan.
- Do not ask for re-approval when the plan is executable; the agent owns decomposition.
- Do stop before crossing the `plan -> execute` stage boundary, because execution is a separate stage.
- **If `--auto` is active** (see `_shared/automation.md`): skip the prompt and invoke `forgeflow:execute` through the adapter-native skill mechanism. Call `Skill(skill: "forgeflow:execute", args: "--task-id <task-id>")` when a Skill tool exists; in Codex App/CLI contexts without that tool, write the checkpoint and continue by following `skills/execute/SKILL.md`. Do NOT just print the skill name or ask "(y/n)".
- **Otherwise**, end with: `계획은 여기까지 확정됐습니다. 다음 스텝으로 /forgeflow:execute을 진행하시겠습니까? (y/n)`
- Do not invoke `/forgeflow:execute` in the same assistant turn after asking the closed next-stage question (unless `--auto` is active). The next assistant turn may proceed only after an explicit user approval such as `y`, `yes`, `진행`, or `실행`.

## Output mode examples

If asked:

```text
/forgeflow:ff-plan For route small, list exactly two plan steps. Do not write files.
```

Return exactly the requested steps in the response. Do not create `plan.md` for this dry-run variant.

If asked:

```text
/forgeflow:ff-plan Write plan.md under resolved task directory (`~/.forgeflow/projects/<project-slug>/tasks/<task-id>` by default)
```

Then and only then write `<task-dir>/plan.md`.

## Telemetry

On completion of this stage, record a telemetry event to `<telemetry-dir>/<task-id>.md`:
- **event**: `stage_complete` on success, `stage_fail` on error/failure
- **stage**: plan
- **outcome**: `success` | `partial` | `failed`
- **failure_type**: on failure, categorize as `scope_mismatch` | `validation_error` | `adapter_error` | `timeout` | `unknown`

On abnormal conditions, also record:
- **event**: `boundary_alert` or `stage_fail` as appropriate

Follow `skills/_shared/discipline.md` Telemetry Event Recording for format details.
