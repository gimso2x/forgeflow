---
name: execute
description: Execute a ForgeFlow plan with verification and runtime evidence. Includes opt-in subagent per-task loop for high/epic routes. Use when the user types /execute or /forgeflow:execute, or asks to implement after clarify/plan.
version: 0.4.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must execute only scoped plan tasks and respect contracts or verify_plan obligations when present.
  Must not treat worker self-report as final approval; review remains required.
  Must use `skills/execute/references/` prompts for subagent dispatch and write the same execute artifacts.
  Must not dispatch parallel implementer subagents for steps that touch the same file.
---

# Execute

Use this skill to execute the selected ForgeFlow route.

## Input

- `plan.md` or a clear small-route brief
- `brief.md` from `/forgeflow:clarify`
- Target repository

## Output Artifacts

- Code changes matching the plan
- `implementation-notes.md` — real-time log maintained throughout execution (template: `templates/implementation-notes.md`)
- `run-ledger.md` — execution truth tracking per-task status (template: `templates/run-ledger.md`)
- `checkpoint.md` — tactical resume pointer updated at stage entry/exit (template: `templates/checkpoint.md`)
- Verification output summary

### implementation-notes.md

Maintain this file **throughout execution**, not as a post-hoc summary. Append entries as decisions arise. Use the structure from `templates/implementation-notes.md`:

- **Current Stage**: execute
- **Status**: in_progress | completed | blocked
- **Decisions**: what was decided, why, when
- **Deviations from Plan**: what differs from plan/spec, reason
- **Progress**: checkpoint tracking per task
- **Files Changed**: path and description of change
- **Evidence**: gate results, test outputs, verification outcomes
- **Blocked By**: blockers or "none"

Guidelines:
- Every entry must state **why** — not just what changed.
- Record a deviation even if you consider it minor; review will judge severity.
- This artifact is reviewed during `/forgeflow:review` and ships with the task evidence.

## Exit Condition

- Planned tasks are implemented
- Verification commands have been run
- Failures are fixed or explicitly recorded
- Runtime evidence exists for review
- `implementation-notes.md` has been updated with final status **before** the exit summary

### Route-aware exit requirements

The exit prompt and next-step guidance depend on the active route.

**If `--auto` is active** (see `_shared/automation.md`): skip the route-specific prompt below and invoke the appropriate `/forgeflow:review` directly.

**Otherwise**, prompt the user:

- **small** route: After implementation, run at least one smoke check (build, lint, or type check — whichever is fastest). Update `implementation-notes.md` with `Status: completed`, then prompt the user:
  ```
  구현 완료. 검증 통과. /forgeflow:review로 리뷰를 진행하시겠습니까? (y/n)
  ```
- **medium** route: Update progress after each step completes. After final step, prompt:
  ```
  모든 계획 단계 실행 완료. /forgeflow:review를 진행해야 합니다. (y/n)
  ```
- **high** route: Update progress after each step completes. After final step, review is mandatory — output this prompt and wait for user confirmation:
  ```
  high route 실행 완료. 독립 review가 필수입니다. /forgeflow:review --type spec 을 진행하시겠습니까? (y/n)
  ```
- **epic** route: Update progress after each step of the current milestone completes. After the final step of the current milestone:
  ```
  마일스톤 실행 완료. 독립 review가 필수입니다. /forgeflow:review --type spec 을 진행하시겠습니까? (y/n)
  ```

Do not end the execute stage without updating `implementation-notes.md`. An execute pass that leaves no state artifact is incomplete.

## Constraints

- **Coding convention**: follow `docs/coding-convention.md` for all code output. File size limits (300 lines), naming (kebab-case files, PascalCase components, camelCase functions), import style (`import type`, `@/` paths), and formatting rules are mandatory.

## Evolution rule enforcement

Before editing files, load active evolution rules when file inspection is allowed:

- Project active rules: `.forgeflow/evolution/active/*.md`
- Global advisory rules: `~/.forgeflow/evolution/active/*.md`

Apply them this way:

1. Project active rules whose `Trigger` and `Application Stage` match the task are required execution constraints.
2. Global advisory rules may guide execution, but they must not block or force hard enforcement.
3. Record applied rules and any ignored advisory rules in `implementation-notes.md` under Decisions or Evidence.
4. If a project active rule would be violated, stop before editing and mark the step `blocked` with the rule id and expected behavior.
5. If the plan omitted an applicable active rule, treat it as a plan deviation and record why before continuing.

## File write and output discipline

→ Core rules: `_shared/discipline.md`.

Follow the user language rules there: write user-facing replies and artifact prose in the user's primary language, while preserving canonical English labels, commands, paths, artifact filenames, and enum values.

Keep execution evidence in `.forgeflow/tasks/<task-id>/implementation-notes.md` and update it before and after code changes.

Step state must be incremental, not a final recap. Each plan step must move through progress tracking: `pending -> in_progress -> completed`. Do not batch-mark all steps as `completed` only at the end. If a step cannot finish, mark it `blocked` with evidence instead of leaving the last known state ambiguous.

**TDD (Test-Driven Development) Cycle**:
For every implementation step:
1. **Red**: Write a failing test that covers the objective. Run it and confirm failure.
2. **Green**: Write the minimal code to pass the test.
3. **Refactor**: Improve the code while keeping tests green.

**Hypothesis-Driven Debugging**:
If a bug or failure occurs during implementation/verification:
1. Document the reproduction steps and observed issue in implementation-notes.md.
2. List causal hypotheses.
3. Test each hypothesis.
4. Apply the fix only after the root cause is verified. Avoid "trial and error" coding.

**Progress and timestamp discipline:**

All timestamps in implementation-notes.md must be real ISO 8601 values, not placeholders.

If the task directory is missing, bootstrap or recover it first. Do not jump straight into source edits while the workflow state lives nowhere.

## Strict response constraints

→ `_shared/discipline.md`.

## Automation / non-interactive approval mode

→ `_shared/automation.md`.

## Real external execution safety

ForgeFlow v1.x does not ship the old Python `exec-stage --real` runtime. If a live adapter or `--real` path is reintroduced, stub/dry-run must remain the default. Before any actual Claude/Codex/Gemini CLI call, API call, billing event, or shared-system mutation, the executor must print a visible stderr warning and require an explicit `[y/N]` confirmation unless the user already approved that exact live action in the current scope.

Minimum warning contract:

```text
[WARNING] --real: 실제 외부 CLI/API 호출이 실행됩니다. 계속하시겠습니까? [y/N]
```

`--auto-approve` and `--non-interactive` do not bypass this safety contract for new live external execution paths.

## Procedure

0. **Isolation check** (→ `_shared/isolation.md`):
   - Detect environment: `test -f .git` → worktree, `test -d .git` → main repo.
   - If in a worktree: verify `.forgeflow` symlink is valid and task artifacts are accessible.
   - If in main repo and `brief.md` has `isolation: worktree`: warn the user — execute should run inside the worktree (`cd .forgeflow/worktrees/<task-id>`). Stop and ask whether to proceed in main (risky for parallel work) or switch to worktree.
   - If `isolation: none` or small route: proceed normally in current directory.

1. Confirm route and current stage. Read `brief.md` to determine route.
2. Run Evolution rule enforcement before editing files.
3. Initialize `implementation-notes.md` in the active task directory if it does not exist (use `templates/implementation-notes.md`). Set `Current Stage: execute`, `Status: in_progress`.
4. Initialize `run-ledger.md` from `templates/run-ledger.md` if it does not exist. Set all task statuses from `plan.md` as `pending`.
5. Write `checkpoint.md` from `templates/checkpoint.md` with `Current Stage: execute`, `Active Task: first pending task`, `Next Action: begin first plan step`.
6. Read Contracts section from `plan.md` before editing when present.
   - **Environment safety net**: If `brief.md` lacks environment notes, run: `git rev-parse --is-inside-work-tree 2>/dev/null; ls node_modules .venv vendor 2>/dev/null | head -3`. If dependencies are missing and a package manager is detected:
     - **Under `--auto`**: install automatically using the detected package manager. Record the install command in `implementation-notes.md` Evidence. Do not stop or ask the user.
     - **Otherwise**: stop and ask: "종속성이 설치되지 않았습니다. 설치를 먼저 진행하시겠습니까?" Do NOT attempt installation yourself.
     - If no git and route is medium/high, warn that ship cannot commit/PR, then continue.
7. For each task in the plan:
   - **TDD Red**: Write/update tests to fail.
   - **Execute Implementation**: Implement minimal code to pass. Prefer the smallest implementation that satisfies the acceptance criteria.
   - **Context budget**: → `_shared/context-resume.md`. Execute addendum:
     - **Resume minimum read set**: `checkpoint.md` → `run-ledger.md` active task + Gate Results → `implementation-notes.md` Reader Summary + Evidence Index → active `plan.md` task section only.
     - Do not re-read a file already in context unless edited since. Before reading, ask: full content, Reader Summary, or specific section? Batch parallel tool calls where possible.
     - After each task completes, append compact evidence index line to `implementation-notes.md` Evidence (e.g. `evidence_index: task=T3 gates=build:PASS,lint:PASS`).
   - **Implementation Notes**: When a decision is made that was not in the plan, when the implementation deviates from the spec, when a tradeoff is chosen, or when an open question arises — **append an entry to `implementation-notes.md` immediately**. Do not batch these until the end.
   - **TDD Refactor**: Clean up implementation.
   - **Run Ledger**: When starting a task, set its status to `running` and **Assignee** to `worker` (or `specialist` if delegated). When completing, set to `done` with evidence refs. When blocked, set to `blocked` with blocker description. Update incrementally, not in batch. See **Run ledger assignee discipline** below.
   - **Per-task micro-gates (high/epic only)**: Before marking a step `done`, run the micro-gate checklist in **Per-task micro-gates** below. Optional spec/quality micro-reviewer subagents use `references/spec-reviewer-prompt.md` and `references/quality-reviewer-prompt.md`.
   - **Checkpoint**: Update `checkpoint.md` after each task completes: set `Active Task` to the next task, update `Latest Artifacts` table. Ensures resume capability after context compaction or clear.
     - **Step-boundary /clear (mandatory)**: Once checkpoint, run-ledger, and evidence are all updated on disk for a completed step, you MUST `/clear` before starting the next task. Do not carry prior task context into the next step — all state is already persisted to disk artifacts. Resume reads checkpoint → ledger → notes → plan active task (→ `_shared/context-resume.md`). This applies to all routes (small/medium/high/epic) and regardless of `--auto` mode. **No exceptions**: the resume cost is fixed (~1-2K tokens to re-read checkpoint → ledger → notes), while skipping `/clear` accumulates stale context from every prior task.
   - **Role awareness**: You are the implementation role. You edit code and update artifacts, but you do not approve your own work. Review is a separate stage with a separate role boundary. Do not merge implementation and review in the same turn.
   - **Architectural Depth**: Ensure implementation follows the plan's architectural intent (Depth, Leverage, Locality) and avoids creating new shallow modules.
   - If blocked, apply **Hypothesis-Driven Debugging**.
   - Nothing speculative: no drive-by abstractions, unrelated cleanup, hidden migrations, or "while I'm here" rewrites unless the approved plan names them.
8. Apply adapter-aware execution: keep ForgeFlow artifacts, gates, and evidence paths backend-neutral. If the backend cannot produce required evidence, record that limitation in implementation-notes.md and block or downgrade the affected verification gate instead of silently proceeding.
9. Treat fulfills, journeys, and verify_plan as verification obligations, not decoration.
10. Run focused verification after each meaningful change. **Standard verification suite** (run all that apply, minimum 1):
    - `build`: Project build command (`pnpm build`, `npm run build`, `cargo build`, etc.)
    - `lint`: Project lint command (`pnpm lint`, `npm run lint`, `ruff check`, etc.)
    - `type_check`: TypeScript type check (`tsc --noEmit`) or equivalent
    - `test`: Project test command (`pnpm test`, `npm test`, `pytest`, etc.)
    Record results in `implementation-notes.md` Evidence as `verification:PASS/FAIL gate=<name> command="<cmd>"`.
    Small routes require at least 1 gate. Medium+ require at least 2 gates including build.
11. Update `implementation-notes.md` immediately when starting and finishing each step. Step state must be incremental: `pending -> in_progress -> completed`. Do not batch-mark all steps as `completed` only at the end. If a step cannot finish, mark it `blocked` with evidence.
   - **Contract checkpoint**: Before marking any plan task complete, verify: "Does this code violate a stated contract?" Record in evidence as `contract_check:PASS <task>` or `contract_check:FAIL <task> reason="..."`.
12. After all steps complete, update implementation-notes.md to `Status: completed` with all passed gates in Evidence.
13. Stop if requirements become ambiguous; return to `/forgeflow:clarify`.
14. Deliver the route-aware exit prompt (see Exit Condition above). Before exiting, verify the **mandatory completion checklist**:
    - ☐ Implementation plan was stated before code changes
    - ☐ All changed files are listed with descriptions
    - ☐ Each component/function role is explained in one line (fill `## 컴포넌트/함수 역할` section in implementation-notes)
    - ☐ Edge cases are enumerated (medium/high/epic routes; fill `## 엣지 케이스` section)
    - ☐ Verification commands were run and results recorded
    - ☐ Deviations from plan recorded (medium/high/epic routes)
    - ☐ Code quality metrics collected (all routes; fill `## 지표` section)
    - ☐ **File size gate**: if any changed file exceeds 300 lines (or the project's documented limit), flag it in Metrics as `oversized_file` and note the split plan. Do not silently ship oversized files.
    If any checklist item is missing, complete it before delivering the exit prompt. Do not skip items.
    **완료 보고를 반드시 사용자에게 출력**:
    1. 완료 요약 (1-2문장, 한국어)
    2. 검증 결과: lint/build/test 각각 pass/fail + 숫자
    3. 변경 파일 목록
    4. 주의사항 (있는 경우): contract_check 실패, environment warning, 미해결 decisions
    Do NOT auto-proceed to the next stage unless `--auto` is active (see `_shared/automation.md`). 반드시 사용자가 다음 단계를 실행하도록 대기.

Contract-aware execution rules:

- Do not change an interface or invariant named in contracts unless the plan explicitly authorizes it.
- For each step with fulfills, record evidence against those requirement/sub-requirement IDs.
- For each journey in the plan, preserve end-to-end verification until `/forgeflow:review`; a passed unit test alone is not enough for a journey gate.
- If verify_plan exists and a target cannot be verified, mark the task blocked instead of pretending it is done.

Worker self-report is not approval. `/forgeflow:review` still has to happen.

## Subagent Per-Task Loop (opt-in, `--subagent-per-task`)

For **high/epic** routes when the user wants every plan step to run implementer → spec micro-review → quality micro-review subagents in strict sequence, enable this mode via `/forgeflow:execute --subagent-per-task`. Default `/forgeflow:execute` remains controller-led with optional delegation.

### When to use

Use when **all** are true:

1. Route is **high** or **epic** (medium only if the user explicitly opts in and accepts overhead)
2. `plan.md` exists and the user approved entering execute
3. User invoked `/forgeflow:execute --subagent-per-task` or explicitly requested subagent-driven execution

Do **not** use for small route (overhead exceeds benefit).

### When not to use

- Steps share the same files (use sequential controller-led execution)
- Environment setup step or final integration-only step (controller runs these)
- User asked for default execute without `--subagent-per-task`

### Per-task loop (strict order)

For each plan step in dependency order:

```text
1. Controller sets run-ledger: running, Assignee worker
   → Record dispatch: "implementer-prompt.md"
2. Dispatch implementer subagent (references/implementer-prompt.md)
3. If NEEDS_CONTEXT → provide context and re-dispatch
   If BLOCKED → ledger blocked; stop or escalate to user
4. Controller verifies: git diff --stat + step verification commands
5. Dispatch spec micro-reviewer OR controller spec micro-check
   → Record dispatch: "spec-reviewer-prompt.md"
   → micro_spec:PASS|FAIL in implementation-notes
6. If spec not approved → implementer fixes → re-review spec (loop)
7. Dispatch quality micro-reviewer OR controller quality micro-check
   → Record dispatch: "quality-reviewer-prompt.md"
   → micro_quality:PASS|FAIL in implementation-notes
8. If quality not approved → implementer fixes → re-review quality (loop)
9. Mark step done in run-ledger only after steps 4–8 pass
10. Update checkpoint.md → next step
```

**Never** skip spec before quality. **Never** mark done on worker DONE alone.

### Parallelism

- **Implementer subagents:** one at a time per conflicting file set (same rule as execute delegation)
- **Fan-out:** only when plan marks steps `(none)` dependency and disjoint file scopes; still **fan-in** with per-step micro-gates before marking done
- Do not run two implementers that touch the same file concurrently

### Model hints

When the shell supports role-specific models:

- Mechanical steps (1–2 files, complete spec) → fast/cheap model
- Integration / multi-file steps → standard coding model
- Micro-reviewers → strongest available for spec; standard for quality if step is mechanical

## Per-task micro-gates

Micro-gates run **during execute** on **high** and **epic** routes. They do not replace stage-level `/forgeflow:review`.

### All routes (every plan step before `done`)

1. **Contract checkpoint** — `contract_check:PASS|FAIL` in implementation-notes Evidence
2. **Step verification** — run verification from the plan step; record `verification:PASS|FAIL`
3. **Run ledger** — status, assignee, evidence refs updated incrementally
4. **fulfills / journeys** — record evidence for IDs named in the step when present

### high / epic only (before marking step `done`)

5. **Spec micro-check (controller)** — Compare diff to step acceptance criteria using the same checklist as `templates/review-report.md` → Spec Compliance; record `micro_spec:PASS|FAIL step=<name>` (`PASS` only when micro verdict would be `approved`)
6. **Quality micro-check (optional)** — After spec micro-check passes, dispatch quality micro-reviewer or controller checklist using review-report → Quality Assessment; record `micro_quality:PASS|FAIL step=<name>`

**Optional subagent micro-review:** After controller verifies `git diff --stat` and step verification, dispatch spec then quality micro-reviewers using templates under `references/`. Order is fixed: **spec before quality**. Re-run micro-review after fixes until pass or step is `blocked`.

**small / medium:** Steps 1–4 only; no mandatory micro-reviewer subagents. Stage review handles spec/quality for medium; small uses quality-only stage review.

## Run ledger assignee discipline

`run-ledger.md` must reflect **who did the work**, not only status:

| Event | Status | Assignee |
|-------|--------|----------|
| Step started (controller) | `running` | `worker` |
| Specialist subagent dispatched | `running` | `specialist` |
| Spec micro-review pass | `running` | `spec-reviewer` |
| Quality micro-review pass | `running` | `quality-reviewer` |
| Step verified complete | `done` | last active role (`worker` or `specialist`) |
| Blocked | `blocked` | role that hit the blocker |

Record worker escalation in implementation-notes when subagents report `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED` (see **Subagent reference prompts**).

## Subagent reference prompts

Dispatch templates live beside this skill (paste full plan step text; never point subagents at `plan.md`):

| Role | File |
|------|------|
| Implementer / specialist worker | `references/implementer-prompt.md` |
| Spec micro-reviewer (high/epic) | `references/spec-reviewer-prompt.md` |
| Quality micro-reviewer (high/epic, after spec) | `references/quality-reviewer-prompt.md` |

### Completion checklist (mandatory)

Before marking execute as completed, verify ALL items:

| # | Item | Required for |
|---|------|-------------|
| 1 | Implementation plan stated before code changes | all routes |
| 2 | All changed files listed with descriptions | all routes |
| 3 | Each component/function role explained (one line each) | all routes |
| 4 | Edge cases enumerated | medium, high, epic |
| 5 | Verification commands run and results recorded | all routes |
| 6 | Deviations from plan recorded in implementation-notes.md | medium, high, epic |
| 7 | Code quality metrics collected in implementation-notes.md | all routes |
| 8 | File size gate: oversized files (>300 lines or project limit) flagged with split plan | all routes |

If any required item is missing, the execute stage is incomplete. Do not deliver the exit prompt until all items are present.

#### Completion response format

Provide checklist responses under a **`### Completion Response`** heading (not under any other heading). This delimiter ensures downstream review and benchmark tools can extract actual responses without matching echoed prompt text. Structure:

```markdown
### Completion Response

1. **Plan**: <one-paragraph summary>
2. **Changed files**: <file list with one-line descriptions>
3. **Role descriptions**: <component/function → one-line role>
4. **Edge cases**: <numbered list, medium/high/epic only>
5. **Verification**: <command + result>
6. **Deviations**: <list or "none", medium/high/epic only>
7. **Metrics**: LOC, TS errors, type assertions, debug artifacts, max component LOC
8. **File size gate**: list any files exceeding 300 lines (or project limit) with split plan, or "all within limit"
```

## Output normalization

When ForgeFlow artifacts are parsed by downstream stages (review, ship), normalize agent output to avoid noise:

- **Codex**: Strip raw git diff blocks before extracting summaries. Codex may output 100KB+ diffs; only the final summary section is relevant for artifacts.
- **All adapters**: Remove ANSI escape sequences, cache/memory logs, and progress spinners from captured command output before recording in `implementation-notes.md`.
- Extract only: file list, verification results, component descriptions, edge cases, and the completion report.

This normalization is advisory for skill prompts but mandatory when ForgeFlow orchestrates multi-adapter pipelines.

## Adapter-aware execution

Detect the current adapter (see `skills/forgeflow/SKILL.md` → Adapter detection) and apply adapter-specific adjustments:

| Adapter | Verification | Output Discipline | Rate Limit |
|---------|-------------|-------------------|------------|
| Claude | `build` preferred. Table-format reports. | Concise by default (~5KB/medium task). No special handling needed. | No known issues. |
| Codex | `lint` mandatory (Codex naturally does this). | Normalize diff-heavy output. Strip raw git diffs; keep only summaries. Output can exceed 100KB without normalization. | No known issues. |
| Gemini | `import type` enforced for TS with `verbatimModuleSyntax`. Structured markdown. | Compact output (~7KB/medium task). May introduce UI abstractions not requested. | **Rate limit (HTTP 429) under concurrent load.** Run sequentially or add 30s cooldown between tasks when executing multiple plan steps. |
| Cursor | Skill names without colons. Same adjustments as the underlying adapter (Claude by default). | Same as underlying adapter. | Same as underlying adapter. |

### Code quality metrics (all adapters)

Collect quantitative metrics after implementation for the Completion Response and review stage:

```bash
# LOC generated
find src/ \( -name "*.ts" -o -name "*.tsx" -o -name "*.css" \) -exec cat {} + | wc -l

# TypeScript type safety
npx tsc --noEmit 2>&1 | grep -c "error TS"

# Type assertions (lower is better)
grep -r "as " src/ --include="*.ts" --include="*.tsx" | wc -l

# Debug artifacts (must be 0)
grep -rE "console\.log|TODO|FIXME|debugger" src/ --include="*.ts" --include="*.tsx" | wc -l

# Component complexity (flag any component > 100L)
for f in $(find src/ -name "*.tsx" -o -name "*.ts"); do echo "$(wc -l < "$f") $f"; done
```

Record results in `implementation-notes.md` → Metrics section and in the Completion Response item 7.

## Agent delegation for specialist work

When `brief.md` includes required specialists and the task scope justifies delegation, use the Agent tool to spawn specialist sub-agents for independent plan steps. This prevents context exhaustion and enables parallel execution.

Base prompt: `references/implementer-prompt.md` (paste **full plan step text**, file allow/deny lists, task directory).

### When to delegate

Delegate to a sub-agent when ALL of these conditions are met:
1. Brief lists a relevant specialist (e.g., `frontend-execute`, `backend-execute`) **or** route is high/epic with fan-out/fan-in in plan Architecture Notes
2. The plan step has no unresolved dependencies on other in-progress steps
3. The step involves isolated file changes that won't conflict with parallel work
4. The main context is getting large enough that delegating preserves quality

Do NOT delegate when:
- The step modifies shared files that other steps also touch
- The step is step-1 (environment setup) or the final verification step
- The task is `small` route (overhead exceeds benefit)

### How to delegate

Use the Agent tool with `references/implementer-prompt.md`. Required prompt fields:

- Full plan step text (objective, files, acceptance criteria, verification)
- `Files you MAY change` / `Files you MUST NOT change`
- Task directory `.forgeflow/tasks/<task-id>/`
- Report format: `DONE` | `DONE_WITH_CONCERNS` | `NEEDS_CONTEXT` | `BLOCKED`

**Red flags (never):**
- Tell subagent to read `plan.md` instead of pasting step text
- Mark step `done` when agent reports DONE without `git diff --stat` + verification
- Skip micro-gates on high/epic after delegated work
- Dispatch parallel implementers for steps that touch the same file

### Agent result handling

After the agent returns:
1. Verify the claimed changes exist (`git diff --stat`)
2. Run verification commands to confirm the agent's evidence
3. Set run-ledger **Assignee** to `specialist` while verifying; then apply **Per-task micro-gates**
4. Update `implementation-notes.md` with verified result — agent self-report alone is not evidence

Handle worker status:
- **NEEDS_CONTEXT** — provide missing context; re-dispatch or complete as controller
- **BLOCKED** — mark ledger `blocked`; do not mark step `done`
- **DONE_WITH_CONCERNS** — record concerns; run micro-gates before `done`

### Parallel delegation

For steps with no mutual dependencies (check plan.md dependencies):
- Spawn multiple agents in a single message with parallel Agent tool calls
- Each agent must receive its exact file scope to prevent conflicts
- After ALL agents return, run cross-document consistency checks
- Mark steps completed only after verification + micro-gates (high/epic), not when agents report done

## UX guardrails

- Treat the latest executable brief/plan as sufficient authority only after the user has approved entering `/forgeflow:execute`.
- If `/forgeflow:execute` was reached without explicit user approval after the previous stage-boundary question, stop immediately and ask for approval instead of editing files.
- 이미 승인된 run scope 안에서는 반복적으로 계획을 다시 허락받지 않는다.
- Do not pause just to reconfirm the same plan before editing files.
- Only bounce back to `/forgeflow:clarify` when scope genuinely changed or a blocker invalidates the current brief/plan.
- When the user asks to fix review findings, treat that as approval to enter a fix loop for the current review scope: read the latest `review-report.md`, fix only current blockers/major findings, re-run focused verification, and update `review-report.md` before claiming the fix loop is complete.
- Bad: `승인된 계획대로 실행하겠습니다.`만 말하고 대기.
- Good: 바로 수정/검증을 시작하고 evidence를 남긴다.

## Bounded verification fix loop

When a lint/build/test/typecheck command fails after an implementation change, do not stop at the first failure. Record each failed command, exit code, and concise failure summary in implementation-notes.md under Evidence using a compact string such as `verification:FAIL attempt=1 command="npm run lint" exit=1 reason="react-hooks/set-state-in-effect"`, apply the smallest scoped fix, then rerun the focused verification. Repeat for at most 3 attempts. Mark work complete only after the latest required verification passes and add a final `verification:PASS ...` evidence ref; if failures remain, set status to `blocked` and keep the latest failure evidence.

Classify the failure layer before applying the fix. Use one of Instructions, Tools, Environment, State, Feedback, or Implementation, and include `layer=<name>` in the `verification:FAIL` evidence when useful. The loop is: observe -> classify layer -> smallest scoped fix -> rerun the same or narrower verification gate -> record `verification:PASS`; Environment or Tools failures that require installation, permissions, destructive cleanup, or external service access must stop for user approval instead of being silently worked around.
