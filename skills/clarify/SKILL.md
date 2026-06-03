---
name: clarify
description: Turn a vague request into a scoped ForgeFlow brief and route decision. Bootstraps task workspace if missing. Use when the user types /clarify or /forgeflow:clarify, or first for new implementation/refactor/debug requests unless the user already provided a complete brief.
version: 0.6.0
author: gimso2x
intent: Convert a raw user request into a scoped brief with route selection and acceptance criteria.
inputs: Raw user request, target repository/path, constraints, existing codebase context.
outputs: brief.md with objective, scope boundary, route, acceptance criteria, and verification gates.
validate_prompt: |
  Must produce brief.md with route selection, scope boundary, and acceptance criteria.
  Must bootstrap task workspace (<task-dir>/) and run-state.json if missing.
  Must include WHERE grounding for non-trivial work.
  Must detect tech stack and auto-detect verification gates.
  Must not skip scope boundary definition or route rationale.
  Must preserve exact-output and dry-run constraints when requested.
dependencies:
  - templates/brief.md (resolve: `.forgeflow/templates/brief.md` first, then plugin cache)
  - skills/_shared/discipline.md
  - skills/_shared/isolation.md
  - skills/_shared/context-resume.md
  Must default to artifact-first behavior and write `brief.md` to the active task directory unless the user explicitly requests dry-run or no-write output.
  Must include WHERE/risk grounding for non-trivial work when artifact writing is allowed.
  Must create `<task-dir>` if it does not already exist.
  Must not overwrite existing task artifacts.
---

# Clarify

Use this skill to convert a raw request into a ForgeFlow context brief (`brief.md`) and route decision.

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

The task ID remains as the internal identifier for resolved `tasks/` directory and `.forgeflow/worktrees/` directories — it does NOT become the branch name.

Plugin-cache/extension-cache safety rule: never create task artifacts under a path containing `.claude/plugins/cache`, `.codex/plugins`, `.cursor/plugins`, `~/.cursor/plugins/local`, `.gemini/extensions`, `~/.gemini/extensions`, or any plugin marketplace/cache/extension directory. If the working directory resolves to a plugin install/cache/extension directory and the user did not provide `--task-dir`, stop and ask for an explicit `--task-dir` instead of writing there.

## Output Artifacts

Write `brief.md` to the active task directory using the `brief.md` template as the structure. Resolve the template path: first check `.forgeflow/templates/brief.md` in the workspace, then fall back to the plugin cache `templates/brief.md` (see main `forgeflow` skill template resolution). If neither exists, generate the structure from the fields listed below. The brief must capture:

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

Write `brief.md` under `<task-dir>`. If the task directory is missing, create it first. Also create `<task-dir>/run-state.json` with resolved project/storage identity if it is missing. Preferred deterministic bootstrap:

```bash
python3 <forgeflow-checkout>/scripts/forgeflow_storage.py --project-dir <repo-root> --task-id <task-id> --write-run-state
```

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

Unless the prompt is exact-output, label-only, dry-run, or says not to inspect files, check evolution rules before route selection:

1. Load project active rules from `.forgeflow/evolution/active/*.md` if the directory exists.
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

## Scope Boundary Definition

clarify 단계에서 scope boundary를 명시적으로 정의하여 scope creep을 방지합니다.

### scope_files 목록 생성

clarify에서는 예상 수정 파일 목록(`scope_files`)을 명시적으로 생성합니다:

1. 요구사항 분석 후 직접적으로 수정이 필요한 파일 나열
2. 각 파일의 수정 이유를 In Scope 항목과 매핑
3. scope_files 수를 route 임계값과 비교하여 `boundary_status` 산정
4. **medium/high/epic route**: scope_files에 예상 테스트 파일도 포함한다. 프로젝트의 테스트 파일 명명 규칙(`*.test.*`, `*.spec.*`, `test_*` 등)을 감지하여, 수정 대상 소스 파일에 대응하는 테스트 파일 경로를 scope_files에 추가한다. 이는 execute 단계의 test-after 검증에서 scope boundary alert를 방지한다.

### Route 임계값과 boundary alert

| Route | files_limit | boundary_status 기준 |
|-------|-------------|---------------------|
| small | 3 | files_planned ≤ 3 → within, = 3 → at_limit, > 3 → exceeds |
| medium | 8 | files_planned ≤ 8 → within, = 8 → at_limit, > 8 → exceeds |
| high | 20 | files_planned ≤ 20 → within, = 20 → at_limit, > 20 → exceeds |
| epic | unlimited | boundary_status 항상 within |

- `boundary_status = exceeds` 시 brief.md에 경고 기록 및 "scope split 권장" advisory 발행
- `boundary_status = at_limit` 시 주의 표시 (경고는 아님)
- scope_boundary 정보를 brief.md YAML frontmatter에 기록

## Procedure

1. **Bootstrap task workspace if missing**: If no active task directory exists (no `<task-dir>` found), generate a task ID (see Task ID generation above) or use `--task-id` if provided, and create `<task-dir>`. Do not overwrite if `brief.md` already exists — report that it was kept as-is.

2. Inspect relevant repo context before inventing scope.
   - Run the Evolution preflight first when allowed, then map matched rules into brief.md.
   - **Common project context preflight**: If `<storage-root>/project-draft.md` exists in the target project root, treat it as section-scoped shared context produced by `/forgeflow:ff-config init --mode=full`. Read only the sections relevant to the request: `Reusable Project Context`, `Documentation Pointers`, `Context Usage Rules`, and verification/test framework fields. Reflect useful planning, architecture, WBS, cross-module contract, and verification pointers in `brief.md` under WHERE, Constraints, Assumptions, Verification Gates, and Environment Preflight. Do not copy the whole draft into task artifacts, and do not treat it as task-specific source of truth. If it does not exist, do not block; record a bounded assumption that common project context was unavailable and continue normal repo inspection.
   - Map Instructions, Tools, Environment, State, and Feedback into brief fields. Use Environment Notes, tech stack, Open Questions, and Verification Gates for missing context instead of creating a separate harness artifact.
   - If an Environment or Tools gap prevents execution, add it to Open Questions as a blocker and ask before routing to plan or execute.
   - **Gemini optimization**: Leverage Gemini's ability to run parallel tool calls. When exploring the codebase, batch multiple `ls`, `grep`, or `cat` operations into a single turn to minimize latency.
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
   | "리뷰해줘", "review this", "audit" | Prefer `/forgeflow:ff-review` when artifacts or a diff already exist; otherwise clarify first. |
   | "계획 세워", "plan this", "break down" | Prefer `/forgeflow:ff-plan` after brief is complete. |
   | "버그", "fix", "debug", "깨짐" | Prefer execute then review; escalate route when risk keywords appear. |
   | "릴리즈", "ship", "배포" | Prefer `/forgeflow:ship` only after review evidence exists. |
   | "대규모", "milestone", "epic" | Consider `epic` and `/forgeflow:ff-plan` with epic decomposition; do not force it without scope evidence. |

7. Select specialist based on task nature (separate from route):
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

8. Set verification gates in the brief:
   - `small`: at least one of `build`, `lint`, or `type_check` — whichever is available and fastest.
   - `medium`: at least `lint` and `type_check`, plus `test` if tests exist for changed files.
   - `high`: full verification suite — `build`, `lint`, `type_check`, and `test`.
   - `epic`: full verification suite, plus milestone-level integration tests.

9. State the route and why, unless an exact-output/label-only instruction applies.

10. **Read project defaults** before producing the brief. Read `<storage-root>/defaults.md` if it exists. Propagate settings to `brief.md` frontmatter:
    - `auto: true` → set `brief.md` frontmatter `auto` to `true`. This ensures `--auto` chaining activates for all subsequent stages.
    - `auto: false` or missing → set `brief.md` frontmatter `auto` to `false`.
    - `isolation: true` → used for worktree isolation decision (step 13). Already handled.
    - If `<storage-root>/defaults.md` does not exist, set `auto: false`, `isolation: false`.
    - **Do not skip this step.** If `defaults.md` says `auto: true` but the brief has `auto: false`, the chain will break at the y/n prompt.

11. **Goal Contract collection** — before writing brief.md, fill the 4 Goal Contract fields in the brief template:
    - **성공 기준 (Success Criteria)**: Extract from the user's stated goal + your scope analysis. Must be objectively measurable (e.g. "all tests pass", "command X exits 0", "file Y contains Z"). NOT aspirational — every criterion must be checkable by a third party without domain context.
    - **필수 증거 (Evidence Required)**: For each success criterion, name the observable artifact or command output that proves it. Map 1:1 with success criteria. If you cannot name evidence for a criterion, the criterion is too vague — refine it.
    - **인정된 리스크 (Accepted Risks)**: Risks you and the user acknowledge and explicitly accept. Review must NOT re-litigate these. If the user has not named any, record "none stated" — do not fabricate risks.
    - **명시적 제외 (Explicit Exclusions)**: Things this task will NOT do. Draw from Out of Scope + any user-stated boundaries. This is the hard scope fence review checks against.
    - **Collection trigger**: Fill during Socratic clarification (step 4) and scope boundary definition. If the user provided a complete brief with acceptance criteria, derive Goal Contract directly from those. If the request is too vague for concrete success criteria, the Goal Contract gaps become blocker questions — do NOT ship a brief with empty success criteria.
    - **Review consumption**: ff-review reads these 4 fields as the PASS/FAIL contract for the task. If Goal Contract is empty or aspirational, review must flag it as a planning defect, not an implementation defect.

12. Produce `brief.md` using the `brief.md` template as the structure (resolve path: `.forgeflow/templates/brief.md` first, then plugin cache), unless an exact-output/label-only instruction applies.

13. If the request is actionable, record remaining non-blocking unknowns as bounded assumptions and make the next stage obvious without asking the user to do your planning work, unless an exact-output/label-only instruction applies.

14. **Worktree isolation** (medium/high/epic only, unless `--no-isolation` or `defaults.md` `isolation: false`):
    Follow the protocol in `_shared/isolation.md`. Summary:
    a. Generate branch name (see Branch name generation above).
    b. Check if `.forgeflow/worktrees/<task-id>/` already exists — skip if so (idempotent).
    c. Create branch: `git branch <branch-name> HEAD`
    d. Create worktree: `git worktree add .forgeflow/worktrees/<task-id> <branch-name>`
    e. Symlink: `ln -s <main-repo>/.forgeflow .forgeflow/worktrees/<task-id>/.forgeflow`
    f. Record in brief.md Task Isolation section: `isolation: worktree`, `worktree_path`, `branch`.
    g. After brief + worktree are ready, inform the user:
       ```
       worktree 생성됨: .forgeflow/worktrees/<task-id> (branch: <branch-name>)
       병렬 실행: cd .forgeflow/worktrees/<task-id> 후 /forgeflow:execute
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

**If `--auto` is active** (set via `--auto` flag, `<storage-root>/defaults.md` `auto: true`, `brief.md` `auto: true`, or user instruction — see `_shared/automation.md`): skip the prompt and **call the `Skill` tool** to invoke the next stage. Do NOT just print the skill name as text.
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
