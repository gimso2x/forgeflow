---
name: clarify
description: Turn a vague or underspecified request into a scoped ForgeFlow brief and route decision. Bootstraps task workspace if missing. Use when the user types /clarify or /forgeflow:clarify, or first for new implementation/refactor requests when the user says 어떻게 접근, 모르겠어, 정리해줘, or shows uncertainty about how to approach a feature. Not for questions about existing brief.md content, documentation lookups, or when the user already provided a complete brief.
version: 0.6.0
intent: Convert vague or underspecified requests into scoped ForgeFlow brief and route decision
inputs: User request text, /clarify or /forgeflow:clarify command, project context
outputs: brief.md with route selection, scope boundary, acceptance criteria, task workspace bootstrap
author: gimso2x
validate_prompt: |
  Must produce brief.md with route selection, scope boundary, and acceptance criteria.
  Must bootstrap task workspace (<task-dir>/) and run-state.json if missing.
  Must run check-clarify guard before exiting the stage (Procedure step 17).
  Must include WHERE grounding for non-trivial work.
  Must detect tech stack and auto-detect verification gates.
  Must not skip scope boundary definition or route rationale.
  Must not skip workspace bootstrap for any route including small.
  Must preserve exact-output and dry-run constraints when requested.
dependencies:
  - templates/brief.md (resolve: `<storage-root>/templates/brief.md` first, then plugin cache)
  - skills/_shared/discipline.md
  - skills/_shared/isolation.md
  - skills/_shared/context-resume.md
---

# Clarify

Use this skill to convert a raw request into a ForgeFlow context brief (`brief.md`) and route decision.

> **Terminology**: `<task-dir>` = resolved task directory: `~/.forgeflow/projects/<project-slug>/tasks/<task-id>/`. `<storage-root>` = `~/.forgeflow/projects/<project-slug>/`.

## Reference inventory

- [references/scope-grounding.md](references/scope-grounding.md) — WHERE grounding, discovery depth, and scope boundary rules for non-trivial requests.

## Input

- Raw user request
- Target repository/path if known
- Constraints, acceptance criteria, risk notes if provided
- Existing codebase context if available
- Shared project context from `<storage-root>/project-draft.md` if present
- Resolved task identity for `run-state.json`: `repo_root`, `project_name`, `project_slug`, `storage_root`, `task_id`
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

Check that `<task-dir>` does not already exist. If it does, append a numeric suffix.

## Branch name generation

For worktree isolation (medium/high/epic), generate a human-readable branch name following the project's commit convention `[브랜치명]`:

```
<type>/<YYYYMM>-<korean-description>
```

- `type`: feature, fix, refactor, docs, or task
- `YYYYMM`: current year-month
- `korean-description`: 2-4 word Korean summary of the objective, hyphen-separated

Examples:
- `feature/202605-네이버지도-기초`
- `fix/202605-면적-슬라이더-정합`
- `refactor/202605-인증-훅-분리`

The branch name is used as the git branch name and commit message prefix. It must be stored in `brief.md` Task Isolation section as `branch`.

The task ID remains as the internal identifier for the resolved `tasks/` directory and `<storage-root>/worktrees/` directories — it does NOT become the branch name.

Plugin-cache/extension-cache safety rule: never create task artifacts under a path containing `.claude/plugins/cache`, `.codex/plugins`, `.cursor/plugins`, `~/.cursor/plugins/local`, or any plugin marketplace/cache/extension directory. If the working directory resolves to a plugin install/cache/extension directory and the user did not provide `--task-dir`, stop and ask for an explicit `--task-dir` instead of writing there.

## Output Artifacts

Write `brief.md` to the active task directory using the `brief.md` template as the structure. Resolve the template path: first check `<storage-root>/templates/brief.md`, then fall back to the plugin cache `templates/brief.md` (see main `forgeflow` skill template resolution). If neither exists, generate the structure from the fields listed below. The brief must capture:

- Objective (one-sentence goal)
- WHERE/context grounding for non-trivial work
- Common Project Context sources read from `<storage-root>/project-draft.md` when present
- In Scope / Out of Scope boundary
- Scope boundary (files_planned, files_limit by route threshold, boundary_status: within|at_limit|exceeds)
- Constraints
- Acceptance Criteria
- Risk Level
- Assumptions (including bounded assumptions for non-blocking unknowns)
- Open Questions (blocker vs non-blocking)
- Specialists (required, skipped, skip rationale)
- Specialist profile (primary, secondary, rationale — review verification perspective, separate from route)
- Verification Gates (auto-detected from tech stack)
- Environment Notes (git status, dependency check, tech stack detected)
- Route selection and rationale
- Route Sub-band (`medium-light` | `medium-full` | `n/a`) when route is medium
- **Goal Contract** (required — review PASS/FAIL contract): 성공 기준 (Success Criteria), 필수 증거 (Evidence Required), 인정된 리스크 (Accepted Risks), 명시적 제외 (Explicit Exclusions)

## Exit Condition

- The request has a clear goal and scope boundary
- True blocker questions are answered; non-blocking unknowns are recorded as bounded assumptions
- A route is selected and justified
- Next skill is named:
  - `small` -> `/forgeflow:execute` or direct execute path
  - `medium` -> `/forgeflow:ff-plan`
  - `high` -> `/forgeflow:ff-plan` with spec/quality review kept separate
  - `epic` -> `/forgeflow:ff-plan` (plan includes epic decomposition)

## Constraints

## File write and output discipline

→ Core rules: `_shared/discipline.md`.

Follow the user language rules there: write user-facing replies and artifact prose in the user's primary language, while preserving canonical English labels, commands, paths, artifact filenames, and enum values.

Write `brief.md` under `<task-dir>`. If the task directory is missing, create it first. Also create `<task-dir>/run-state.json` with resolved project/storage identity if it is missing. **Required** deterministic bootstrap — always use this, never invent paths manually:

```bash
python3 <forgeflow-checkout>/scripts/forgeflow_storage.py --project-dir <repo-root> --task-id <task-id> --write-run-state
```

**Project-local .forgeflow creation is forbidden.** Never write artifacts under `<repo>/.forgeflow/`. All task artifacts, telemetry, evolution rules, and worktrees must live under the global storage root `~/.forgeflow/projects/<project-slug>/`. The only exception is worktree compatibility symlinks under `<storage-root>/worktrees/<task-id>/.forgeflow/` (see `_shared/isolation.md`). If you catch yourself constructing a path containing `<repo>/.forgeflow`, stop and use `forgeflow_storage.py` to resolve the correct global path instead.

Do not return a pseudo-brief in chat only when the workflow expects artifacts.

## Strict response constraints

→ Core rules: `_shared/discipline.md`.

When the user requests an exact output (label only, list only, dry run), return exactly that — nothing extra.

- Label-only route: output exactly `small`, `medium`, `high`, or `epic` and stop.
- Exact-count questions: start directly with `1.` — no preamble.
- List questions: list them inline. Do not call interactive tools unless the user asks.

## Context resume and refresh safety

→ `_shared/context-resume.md`.

- **Minimum read set (new task)**: user request + repo context as needed for scope.
- **Minimum read set (resume)**: `checkpoint.md` → `brief.md` in-progress sections only.
- **Stage exit**: update `checkpoint.md` with Current Stage, Next Action, Minimum Read Set. Safe to refresh context after brief + checkpoint are written.
- Do not refresh context mid-interview before `brief.md` is complete.

## Evolution preflight

→ Full protocol: `_shared/evolution-preflight.md`.

Unless the prompt is exact-output, label-only, dry-run, or says not to inspect files, check evolution rules before route selection:

1. Load project active rules from `<storage-root>/evolution/active/*.md` if the directory exists (resolved via `forgeflow_storage.py`). Do **not** create this directory if it does not exist. Read-only check.
2. Load global advisory rules from `~/.forgeflow/evolution/active/*.md` if available.
3. Match rules by their `Trigger` and `Application Stage` fields.
4. Record matching rules in the brief's `Applied Evolution Rules` section.
5. Project active rules are required constraints for this repository. Global rules are advisory only: they may guide clarify/plan, but they must not block or force hard enforcement.
6. If a project active rule conflicts with the user request, surface it as a blocker question with a recommended resolution.

## Fact Recall (Memory Bank L4)

After evolution preflight, search the ForgeFlow Memory Bank for facts relevant to the current request:

1. Run `python3 scripts/forgeflow_fact_store.py search --query "<objective keywords>"` to find relevant facts.
2. If facts are found, record them in the brief's `Applied Memory Facts` section with their IDs and content.
3. Facts inform WHERE grounding, constraints, assumptions, and verification gates — they are context, not commands.
4. If no facts are found, record a bounded assumption: "Memory Bank에 관련 팩트 없음" and continue normally.
5. Prefer high-confidence facts over low-confidence ones when they conflict.

Fact types and their clarify usage:
- `decision`: Past architectural choices that may constrain the current task.
- `constraint`: Known limitations or requirements from prior work.
- `pattern`: Reusable approaches that succeeded before.
- `bug_fix`: Past failure modes to watch for.
- `preference`: User-stated preferences from earlier sessions.
- `discovery`: Found behaviors or properties of the codebase.

This is how ForgeFlow learns from prior work: long-run proposes rules, review validates them, active rules are loaded automatically by future clarify/plan/execute stages.

## WHERE grounding

Before routing non-trivial work, calibrate WHERE dimensions (project_type, situation, ambition, risk_modifiers) in the brief. Apply risk escalation and situation-specific rules.

→ Full calibration rules, risk escalation, and situation patterns: [`references/scope-grounding.md`](references/scope-grounding.md)

## Scope Boundary Definition

Generate `scope_files` list and compare against route thresholds. Record `boundary_status` in brief.md.

→ Route thresholds and boundary alert rules: [`references/scope-grounding.md`](references/scope-grounding.md)

## Procedure

### Phase 1: Bootstrap (steps 1-2)

1. **Bootstrap task workspace if missing** (all routes — never skip): If no active task directory exists (no `<task-dir>` found), generate a task ID (see Task ID generation above) or use `--task-id` if provided, and create `<task-dir>`. Do not overwrite if `brief.md` already exists — report that it was kept as-is.
   ```bash
   python3 <forgeflow-checkout>/scripts/forgeflow_storage.py --project-dir <repo-root> --task-id <task-id> --write-run-state
   ```
   If this fails, **do not proceed** to step 2. Resolve the error first.

### Phase 2: Analysis & Grounding (steps 2-6)

2. Inspect relevant repo context before inventing scope.
   - Run the Evolution preflight first when allowed, then map matched rules into brief.md.
   - **Common project context preflight**: If `<storage-root>/project-draft.md` exists in the target project root, treat it as section-scoped shared context produced by `/forgeflow:ff-config init --mode=full`. Read only the sections relevant to the request: `Reusable Project Context`, `Documentation Pointers`, `Context Usage Rules`, and verification/test framework fields. Reflect useful planning, architecture, WBS, cross-module contract, and verification pointers in `brief.md` under WHERE, Constraints, Assumptions, Verification Gates, and Environment Preflight. Do not copy the whole draft into task artifacts, and do not treat it as task-specific source of truth. If it does not exist, do not block; record a bounded assumption that common project context was unavailable and continue normal repo inspection.
   - Map Instructions, Tools, Environment, State, and Feedback into brief fields. Use Environment Notes, tech stack, Open Questions, and Verification Gates for missing context instead of creating a separate harness artifact.
   - If an Environment or Tools gap prevents execution, add it to Open Questions as a blocker and ask before routing to plan or execute.
   - **Exploration batching**: When exploring the codebase, batch multiple read/search operations into a single turn to minimize latency where the adapter allows parallel tool calls.
   - Surface confusion instead of guessing. If the request has competing interpretations that materially change scope, say so in the brief.
   - For brownfield refactors or extensions, specifically identify **architectural friction**: where are modules **shallow** (interface as complex as implementation), where is **locality** missing, and where are **pass-throughs** bloating the path? Use `<storage-root>/project-draft.md` architecture and contract pointers as hints, but verify task-critical facts against source documents or code.
   - Do not silently pick one interpretation when the ambiguity affects user-visible behavior, data, security, or files to edit. Record material ambiguity in `brief.md` under `Assumptions and Interpretation`: `Selected interpretation`, `Assumptions`, `Open ambiguity`, and `Why safe to proceed`.
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

4. **Scope Topology Lock (Round 0)** — before deep requirement questions, enumerate the change scope as 1–6 top-level components:
   1. List every module, subsystem, or file group the request will likely touch as top-level components.
   2. Present the topology to the user for one-shot confirmation: "변경 범위 위상: [C1, C2, …]. 이 범위가 맞습니까?"
   3. Only after user confirmation (or user correction), proceed to deep Socratic questions.
   4. If during later questioning a new component is discovered, pause and re-confirm the topology before continuing.
   5. Record the confirmed topology in `brief.md` → Scope Topology section.

5. Apply Socratic clarification (the "grilling loop") before route selection:
   - Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.
   - For each question asked, provide your recommended answer to reduce user cognitive load.
   - If a question can be answered by exploring the codebase, explore the codebase instead of asking.
   - Name the hidden assumptions the request appears to rely on.
   - Separate true blocker questions from non-blocking unknowns.
   - State explicit non-goals and scope boundaries before planning.
   - Do not let ambiguity disappear into prose. It must be visible in the brief artifact or response artifact.

6. **Ambiguity scoring gate** — after Socratic clarification, quantitatively score clarity across 4 dimensions before proceeding:

   Score each dimension 1–10 (10 = fully clear):

   | Dimension | What to evaluate |
   |-----------|-----------------|
   | **Objective clarity** | Is the goal unambiguous and testable? |
   | **Scope clarity** | Are boundaries (in/out) explicit with no grey zones? |
   | **Constraint clarity** | Are technical, platform, and dependency constraints known? |
   | **Acceptance clarity** | Can a third party verify completion without domain context? |

   Compute: `ambiguity_score = average(max(10 - dim_score) / 10)` across all 4 dimensions.

   - `ambiguity_score ≤ 0.3` → proceed. Brief is clear enough for execution.
   - `0.3 < ambiguity_score ≤ 0.5` → ask 1–2 targeted blocker questions, then re-score (max 3 rounds).
   - `ambiguity_score > 0.5` → identify the weakest 2 dimensions and ask focused blocker questions. Re-score (max 3 rounds).
   - After 3 rounds without reaching ≤ 0.3: record the weakest dimensions as bounded assumptions in brief.md, note the residual ambiguity, and proceed. Do not block indefinitely.

   Record in `brief.md` YAML frontmatter:
   ```yaml
   ambiguity:
     objective: <!-- 1-10 -->
     scope: <!-- 1-10 -->
     constraints: <!-- 1-10 -->
     acceptance: <!-- 1-10 -->
     score: <!-- computed 0.0-1.0 -->
     rounds: <!-- N -->
     status: pass | bounded_assumption
   ```

### Phase 3: Scoring & Routing (steps 7-11)

7. Score complexity using the documented weighted model:
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

8. Apply alias hints only within the scoring context. The table below maps user wording to `suggested_next_skill` — Keyword hints are advisory and must not auto-invoke any skill. Route selection (`small`/`medium`/`high`/`epic`) remains explicit and independent of alias hints. Do not auto-invoke skills from keyword detection alone.

   | User wording | Hint |
   |--------------|------|
   | "리뷰해줘", "review this", "audit" | Prefer `/forgeflow:ff-review` when artifacts or a diff already exist; otherwise clarify first. |
   | "계획 세워", "plan this", "break down" | Prefer `/forgeflow:ff-plan` after brief is complete. |
   | "버그", "fix", "debug", "깨짐" | Prefer execute then review; escalate route when risk keywords appear. |
   | "릴리즈", "ship", "배포" | Prefer `/forgeflow:ship` only after review evidence exists. |
   | "대규모", "milestone", "epic" | Consider `epic` and `/forgeflow:ff-plan` with epic decomposition; do not force it without scope evidence. |

9. Select specialist based on task nature (separate from route):
   Route determines scope size (small/medium/high/epic). Specialist determines the review verification perspective.

   **Specialist selection criteria** (pick primary and optionally secondary):
   - 인증/권한/비밀번호/입력검증 → `security`
   - UI/문구/접근성/사용자흐름 → `ux`
   - 성능/메모리/지연/대규모데이터 → `perf`
   - 로직/에러처리/엣지케이스 → `correctness`
   - 구조/네이밍/중복/복잡도/가독성/함수길이 → `maintainability`
   - 명확한 해당 없음 → `none`

   Write the specialist field to `brief.md` YAML frontmatter:
   ```yaml
   specialist:
     primary: none | security | ux | perf | correctness | maintainability
     secondary: none | security | ux | perf | correctness | maintainability
     rationale: "<why this specialist is needed>"
   ```

   - Primary specialist is the dominant review lens. Secondary adds a supplementary perspective.
   - When the task touches multiple domains equally, assign the higher-risk domain as primary.
   - `none` means no specialized review lens; standard quality review applies.
   - Record rationale as a one-line explanation of why the specialist was chosen.

10. Set verification gates in the brief:
   - `small`: at least one of `build`, `lint`, or `type_check` — whichever is available and fastest.
   - `medium`: at least `lint` and `type_check`, plus `test` if tests exist for changed files.
   - `high`: full verification suite — `build`, `lint`, `type_check`, and `test`.
   - `epic`: full verification suite, plus milestone-level integration tests.

11. State the route and why, unless an exact-output/label-only instruction applies.

### Phase 4: Output & Verification (steps 12-17)

12. **Read project defaults** before producing the brief. Read `<storage-root>/defaults.md` if it exists. Propagate settings to `brief.md` frontmatter:
    - `auto: true` → set `brief.md` frontmatter `auto` to `true`. This ensures `--auto` chaining activates for all subsequent stages.
    - `auto: false` or missing → set `brief.md` frontmatter `auto` to `false`.
    - `isolation: true` → used for worktree isolation decision (step 16). Already handled.
    - If `<storage-root>/defaults.md` does not exist, set `auto: false`, `isolation: false`.
    - **Do not skip this step.** If `defaults.md` says `auto: true` but the brief has `auto: false`, the chain will break at the y/n prompt.

13. **Goal Contract collection** — before writing brief.md, fill the 4 Goal Contract fields in the brief template:
    - **성공 기준 (Success Criteria)**: Extract from the user's stated goal + your scope analysis. Must be objectively measurable (e.g. "all tests pass", "command X exits 0", "file Y contains Z"). NOT aspirational — every criterion must be checkable by a third party without domain context.
    - **필수 증거 (Evidence Required)**: For each success criterion, name the observable artifact or command output that proves it. Map 1:1 with success criteria. If you cannot name evidence for a criterion, the criterion is too vague — refine it.
    - **인정된 리스크 (Accepted Risks)**: Risks you and the user acknowledge and explicitly accept. Review must NOT re-litigate these. If the user has not named any, record "none stated" — do not fabricate risks.
    - **명시적 제외 (Explicit Exclusions)**: Things this task will NOT do. Draw from Out of Scope + any user-stated boundaries. This is the hard scope fence review checks against.
    - **Collection trigger**: Fill during Socratic clarification (step 5) and scope boundary definition. If the user provided a complete brief with acceptance criteria, derive Goal Contract directly from those. If the request is too vague for concrete success criteria, the Goal Contract gaps become blocker questions — do NOT ship a brief with empty success criteria.
    - **Review consumption**: ff-review reads these 4 fields as the PASS/FAIL contract for the task. If Goal Contract is empty or aspirational, review must flag it as a planning defect, not an implementation defect.

14. Produce `brief.md` using the `brief.md` template as the structure (resolve path: `<storage-root>/templates/brief.md` first, then plugin cache), unless an exact-output/label-only instruction applies.

15. If the request is actionable, record remaining non-blocking unknowns as bounded assumptions and make the next stage obvious without asking the user to do your planning work, unless an exact-output/label-only instruction applies.

16. **Worktree isolation** (medium/high/epic only, unless `--no-isolation` or `defaults.md` `isolation: false`):
    Follow the protocol in `_shared/isolation.md`. Summary:
    a. Generate branch name (see Branch name generation above).
    b. Check if `<storage-root>/worktrees/<task-id>/` already exists — skip if so (idempotent).
    c. Create branch: `git branch <branch-name> HEAD`
    d. Create worktree: `git worktree add <storage-root>/worktrees/<task-id> <branch-name>`
    e. If compatibility paths are required, create `<storage-root>/worktrees/<task-id>/.forgeflow/` and symlink only individual global storage subdirectories (`tasks`, `telemetry`, `evolution`, `tmp-assets`). Do not symlink or create `<repo>/.forgeflow`.
    f. Record in brief.md Task Isolation section: `isolation: worktree`, `worktree_path`, `branch`.
    g. After brief + worktree are ready, inform the user:
       ```
       worktree 생성됨: <storage-root>/worktrees/<task-id> (branch: <branch-name>)
       병렬 실행: cd <storage-root>/worktrees/<task-id> 후 /forgeflow:execute
       ```
    **Small route**: skip worktree creation. Set `isolation: none` in brief.
    **`--no-isolation`**: skip regardless of route. Set `isolation: none`.

Do not implement here. Clarify is the intake gate, not the coding phase.

## Contract-first traceability for medium/high/epic or brownfield work

For non-trivial work, identify cross-module contracts before route selection:

1. Identify interfaces, invariants, data shapes, and compatibility constraints that parallel workers must not break.
2. If any contract exists, note it in the brief's Constraints section.
3. Record `fulfills` targets for traceability.
4. Identify journeys (multi-step user or system flows that require end-to-end verification).
5. Preserve non-goals and bounded assumptions when they affect execution boundaries.

Small documentation-only tasks may omit these.

17. **Stage Completion Gate** (all routes — never skip): Before exiting clarify, verify artifacts with the guard check script:
    ```bash
    python3 <forgeflow-checkout>/scripts/forgeflow_guard_check.py check-clarify --task-dir <task-dir>
    ```
    - **PASS** → stage complete, proceed to next stage or present route to user.
    - **BLOCK** → create the missing artifacts, then re-run. Do not exit the stage with BLOCK results.
    - Do not skip this verification even for `small` route or trivial requests. The only exception is label-only / dry-run mode where no artifacts are written by design.

## Auto-detectable verification gates

→ Shared gate definitions: `_shared/verification-gates.md`.

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

**If `--auto` is active** (set via `--auto` flag, `<storage-root>/defaults.md` `auto: true`, `brief.md` `auto: true`, or user instruction — see `_shared/automation.md`): skip the prompt and invoke the next stage through the adapter-native skill mechanism. Call the `Skill` tool when it exists; in Codex App/CLI contexts without that tool, write the checkpoint and continue by following the next stage SKILL.md contract. Do NOT just print the skill name as text.
- `small` → `Skill(skill: "forgeflow:execute", args: "--task-id <task-id>")`
- `medium` or `high` → `Skill(skill: "forgeflow:ff-plan", args: "--task-id <task-id>")`
- `epic` → `Skill(skill: "forgeflow:ff-plan", args: "--task-id <task-id>")`

**Otherwise**, end with a route-specific next step:
- `small`: `요구사항 충분. small route입니다. 다음 스텝으로 /forgeflow:execute을 진행하시겠습니까? (y/n)`
- `medium` or `high`: `요구사항 충분. <route> route입니다. 다음 스텝으로 /forgeflow:ff-plan을 진행하시겠습니까? (y/n)`
- `epic`: `요구사항 충분. epic route입니다. 다음 스텝으로 /forgeflow:ff-plan을 진행하시겠습니까? (y/n)`

## Output mode examples

For label-only requests like `/forgeflow:clarify Add a README badge. Return only the selected route label.`:
Return exactly one of `small`, `medium`, `high`, or `epic`. No explanation, no file writes.

## Telemetry

On completion of this stage, record a telemetry event to `<telemetry-dir>/<task-id>.md`:
- **event**: `stage_complete` on success, `stage_fail` on error/failure
- **stage**: clarify
- **outcome**: `success` | `partial` | `failed`
- **failure_type**: on failure, categorize as `scope_exceeded` | `routing_ambiguity` | `validation_error` | `timeout` | `unknown`

On abnormal conditions (unexpected errors, routing failures), also record:
- **event**: `boundary_alert` or `stage_fail` as appropriate

Follow `skills/_shared/discipline.md` Telemetry Event Recording for format details.
