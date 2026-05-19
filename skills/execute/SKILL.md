---
name: execute
description: Execute a ForgeFlow plan with verification and runtime evidence. Use when the user types /forgeflow:execute or asks to implement after clarify/plan.
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must execute only scoped plan tasks and respect contracts or verify_plan obligations when present.
  Must not treat worker self-report as final approval; review remains required.
---

# Execute

Use this skill to execute the selected ForgeFlow route.

## Input

- `plan.md` or a clear small-route brief
- `brief.md` from `/forgeflow:clarify`
- `requirements.md` if available
- Target repository

## Output Artifacts

- Code changes matching the plan
- `implementation-notes.md` — real-time log maintained throughout execution (template: `templates/implementation-notes.md`)
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

The exit prompt and next-step guidance depend on the active route:

- **small** route: After implementation, run at least one smoke check (build, lint, or type check — whichever is fastest). Update `implementation-notes.md` with `Status: completed`, then prompt the user:
  ```
  구현 완료. 검증 통과. /forgeflow:review로 리뷰를 진행하시겠습니까? (y/n)
  ```
- **medium** route: Update progress after each step completes. After final step, prompt:
  ```
  모든 계획 단계 실행 완료. /forgeflow:review를 진행해야 합니다. (y/n)
  ```
- **high** route: Update progress after each step completes. After final step, the next stage is **mandatory** — do NOT ask whether to review:
  ```
  high route 실행 완료. 독립 review가 필수입니다. /forgeflow:review --type spec 으로 Spec Review를 시작합니다.
  ```
  Then immediately invoke `/forgeflow:review --type spec`.
- **epic** route: Update progress after each step of the current milestone completes. After the final step of the current milestone:
  ```
  마일스톤 실행 완료. 독립 review가 필수입니다. /forgeflow:review --type spec 으로 Spec Review를 시작합니다.
  ```
  Then immediately invoke `/forgeflow:review --type spec`.

Do not end the execute stage without updating `implementation-notes.md`. An execute pass that leaves no state artifact is incomplete.

## File write and output discipline

Default to **artifact-first mode**. Keep execution evidence in `.forgeflow/tasks/<task-id>/implementation-notes.md` and update it before and after code changes unless the user explicitly asks for a dry run, exact-output response, or no-write simulation.

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

Canonical writable location:

- `.forgeflow/tasks/<task-id>/`

If the task directory is missing, bootstrap or recover it first. Do not jump straight into source edits while the workflow state lives nowhere.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

Write only under the current project workspace or the active task directory. Never write inside `skills/<skill>/`.

## Strict response constraints

When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.

When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.

For exact-count list prompts, output numbered lines only. No heading, preamble, fenced block, summary, or extra lines.

## Automation / non-interactive approval mode

If the user explicitly includes `--yes`, `--auto-approve`, `--non-interactive`, or says to continue through ForgeFlow stages without further approval, treat that as approval for the current bounded ForgeFlow sequence. Do not pause at the normal stage-boundary y/n prompt; proceed to the next requested ForgeFlow stage after writing the required artifact for the current stage. This only applies inside the stated task scope and never overrides a blocker, failed verification, missing required artifact, or unsafe/destructive action.

## Procedure

1. Confirm route and current stage. Read `brief.md` to determine route.
2. Initialize `implementation-notes.md` in the active task directory if it does not exist (use `templates/implementation-notes.md`). Set `Current Stage: execute`, `Status: in_progress`.
3. Read Contracts section from `plan.md` before editing when present.
   - **Environment safety net**: If `brief.md` lacks environment notes, run: `git rev-parse --is-inside-work-tree 2>/dev/null; ls node_modules .venv vendor 2>/dev/null | head -3`. If dependencies are missing and a package manager is detected, stop and ask: "종속성이 설치되지 않았습니다. 설치를 먼저 진행하시겠습니까?" Do NOT attempt installation yourself. If no git and route is medium/high, warn that ship cannot commit/PR, then continue.
4. For each task in the plan:
   - **TDD Red**: Write/update tests to fail.
   - **Execute Implementation**: Implement minimal code to pass. Prefer the smallest implementation that satisfies the acceptance criteria.
   - **Context budget**: Do not re-read a file already in context unless it was edited since. Before reading a file, ask: "Do I need the full content, or just a specific section?" If the latter, read only the relevant lines. Batch multiple file inspections into parallel tool calls where possible.
   - **Implementation Notes**: When a decision is made that was not in the plan, when the implementation deviates from the spec, when a tradeoff is chosen, or when an open question arises — **append an entry to `implementation-notes.md` immediately**. Do not batch these until the end.
   - **TDD Refactor**: Clean up implementation.
   - **Architectural Depth**: Ensure implementation follows the plan's architectural intent (Depth, Leverage, Locality) and avoids creating new shallow modules.
   - If blocked, apply **Hypothesis-Driven Debugging**.
   - Nothing speculative: no drive-by abstractions, unrelated cleanup, hidden migrations, or "while I'm here" rewrites unless the approved plan names them.
5. Apply adapter-aware execution: keep ForgeFlow artifacts, gates, and evidence paths backend-neutral. If the backend cannot produce required evidence, record that limitation in implementation-notes.md and block or downgrade the affected verification gate instead of silently proceeding.
6. Treat fulfills, journeys, and verify_plan as verification obligations, not decoration.
7. Run focused verification after each meaningful change.
8. Update `implementation-notes.md` immediately when starting and finishing each step. Step state must be incremental: `pending -> in_progress -> completed`. Do not batch-mark all steps as `completed` only at the end. If a step cannot finish, mark it `blocked` with evidence.
   - **Contract checkpoint**: Before marking any plan task complete, verify: "Does this code violate a stated contract?" Record in evidence as `contract_check:PASS <task>` or `contract_check:FAIL <task> reason="..."`.
9. After all steps complete, update implementation-notes.md to `Status: completed` with all passed gates in Evidence.
10. Stop if requirements become ambiguous; return to `/forgeflow:clarify`.
11. Deliver the route-aware exit prompt (see Exit Condition above). **완료 보고를 반드시 사용자에게 출력**:
    1. 완료 요약 (1-2문장, 한국어)
    2. 검증 결과: lint/build/test 각각 pass/fail + 숫자
    3. 변경 파일 목록
    4. 주의사항 (있는 경우): contract_check 실패, environment warning, 미해결 decisions
    Do NOT auto-proceed to the next stage. 반드시 사용자가 다음 단계를 실행하도록 대기.

Contract-aware execution rules:

- Do not change an interface or invariant named in contracts unless the plan explicitly authorizes it.
- For each step with fulfills, record evidence against those requirement/sub-requirement IDs.
- For each journey in the plan, preserve end-to-end verification until `/forgeflow:review`; a passed unit test alone is not enough for a journey gate.
- If verify_plan exists and a target cannot be verified, mark the task blocked instead of pretending it is done.

Worker self-report is not approval. `/forgeflow:review` still has to happen.

## Agent delegation for specialist work

When `brief.md` includes required specialists and the task scope justifies delegation, use the Agent tool to spawn specialist sub-agents for independent plan steps. This prevents context exhaustion and enables parallel execution.

### When to delegate

Delegate to a sub-agent when ALL of these conditions are met:
1. Brief lists a relevant specialist (e.g., `frontend-execute`, `backend-execute`)
2. The plan step has no unresolved dependencies on other in-progress steps
3. The step involves isolated file changes that won't conflict with parallel work
4. The main context is getting large enough that delegating preserves quality

Do NOT delegate when:
- The step modifies shared files that other steps also touch
- The step is step-1 (environment setup) or the final verification step
- The task is `small` route (overhead exceeds benefit)

### How to delegate

Use the Agent tool with a clear specialist prompt:

```text
Agent({
  description: "Frontend specialist: implement <step objective>",
  prompt: "You are a ForgeFlow frontend worker. Task: <step objective>.
           Working directory: <path>
           Files to change: <exact paths>. Acceptance criteria: <from plan step>.
           Do not modify files outside the listed scope.
           Run verification from the working directory."
})
```

### Agent result handling

After the agent returns:
1. Verify the claimed changes exist (`git diff --stat`)
2. Run verification commands to confirm the agent's evidence
3. Update implementation-notes.md with the verified result — agent self-report alone is not evidence

### Parallel delegation

For steps with no mutual dependencies (check plan.md dependencies):
- Spawn multiple agents in a single message with parallel Agent tool calls
- Each agent must receive its exact file scope to prevent conflicts
- After ALL agents return, run cross-document consistency checks
- Mark steps completed only after verification, not when agents report done

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
