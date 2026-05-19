---
name: execute
description: Execute a ForgeFlow plan with verification and runtime evidence. Use when the user types /forgeflow:execute or asks to implement after clarify/plan.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must execute only scoped plan tasks and respect contracts or verify_plan obligations when present.
  Must not treat worker self-report as final approval; review remains required.
---

# Execute

Use this skill to execute the selected ForgeFlow route.

## Input

- `plan.json` or a clear small-route brief
- `requirements.md` if available
- `brief.json` or equivalent brief
- Target repository

## Output Artifacts

- Code changes
- `run-state.json` or equivalent stage/gate state
- `decision-log.json` with key implementation decisions
- `implementation-notes.md` — real-time log of design decisions, spec deviations, tradeoffs, and open questions (see below)
- Updated `plan-ledger.json` for medium/high routes
- Verification output summary

### implementation-notes.md

Maintain this file **throughout execution**, not as a post-hoc summary. Append entries as decisions arise. Use this structure:

```markdown
# Implementation Notes: <task-id>

## Design Decisions
- [DECISION] <what was decided> — <why> (when: <timestamp or step-id>)

## Spec Deviations
- [DEVIATION] <what differs from plan/spec> — <reason> (when: <step-id>)

## Tradeoffs
- [TRADEOFF] <chosen approach> over <alternative> — <why> (when: <step-id>)

## Open Questions
- [QUESTION] <unresolved item needing user confirmation> (status: open/resolved)
```

Guidelines:
- Every entry must state **why** — not just what changed.
- Record a deviation even if you consider it minor; review will judge severity.
- Open questions that block execution should be escalated immediately via `decision-log.json` stuck detection.
- This artifact is reviewed during `/forgeflow:review` and ships with the task evidence.

## Exit Condition

- Planned tasks are implemented
- Verification commands have been run
- Failures are fixed or explicitly recorded
- Runtime evidence exists for review
- `run-state.json` has been written to the active task directory **before** the exit summary

### Route-aware exit requirements

The execute stage MUST produce `run-state.json` conforming to `schemas/run-state.schema.json`. The exit prompt and next-step guidance depend on the active route:

- **small** route: After implementation, run at least one smoke check (build, lint, or type check — whichever is fastest). Write `run-state.json` with `status: "completed"`, then prompt the user:
  ```
  구현 완료. 검증 통과. /forgeflow:review로 리뷰를 진행하시겠습니까? (y/n)
  ```
- **medium** route: Write `run-state.json` after each step completes. After final step, prompt:
  ```
  모든 계획 단계 실행 완료. /forgeflow:review를 진행해야 합니다. (y/n)
  ```
- **high** route: Write `run-state.json` after each step completes. After final step, the next stage is **mandatory** — do NOT ask whether to review:
  ```
  high route 실행 완료. 독립 review가 필수입니다. /forgeflow:review --type spec 으로 Spec Review를 시작합니다.
  ```
  Then immediately invoke `/forgeflow:review --type spec`. /forgeflow:review를 자동으로 시작합니다.
- **epic** route: Write `run-state.json` after each step of the current milestone completes. After the final step of the current milestone:
  ```
  마일스톤 실행 완료. 독립 review가 필수입니다. /forgeflow:review --type spec 으로 Spec Review를 시작합니다.
  ```
  Then immediately invoke `/forgeflow:review --type spec`.

Do not end the execute stage without writing `run-state.json`. An execute pass that leaves no state artifact is incomplete.

## File write and output discipline

Default to **artifact-first mode**. Run should update `run-state.json` before and after code changes, and keep execution evidence in the active task directory unless the user explicitly asks for a dry run, exact-output response, or no-write simulation.

Step state must be incremental, not a final recap. Each plan step must move through `in_progress` before `completed`, and the agent must update `run-state.json` immediately when starting and finishing each step. Example: `step-1: pending → in_progress → completed`, then `step-2: pending → in_progress → completed`. Do not batch-mark all steps as `completed` only at the end. If a step cannot finish, mark it `blocked` or `failed` with evidence instead of leaving the last known state ambiguous.

**TDD (Test-Driven Development) Cycle**:
For every implementation step:
1. **Red**: Write a failing test that covers the objective. Run it and confirm failure.
2. **Green**: Write the minimal code to pass the test.
3. **Refactor**: Improve the code while keeping tests green.

**Hypothesis-Driven Debugging**:
If a bug or failure occurs during implementation/verification:
1. Document the reproduction steps and observed issue in `decision-log.json`.
2. List causal hypotheses.
3. Test each hypothesis.
4. Apply the fix only after the root cause is verified. Avoid "trial and error" coding.

**Progress and timestamp discipline:**

Every time `run-state.json` is written, the `progress` object MUST be recalculated from the current step statuses:
- `percentage`: `(completed_steps / total_steps) * 100`, rounded to 1 decimal
- `completed_steps`: count of steps with status `"completed"`
- `total_steps`: total number of steps in the plan
- `next_actionable`: list of step IDs that are `"pending"` and whose dependencies are all `"completed"`

All `started_at` and `completed_at` timestamps MUST be real ISO 8601 values (e.g. `2026-05-04T02:35:00.000Z`), **not** placeholder zeros like `2026-05-04T00:00:00.000Z`. Use `new Date().toISOString()` or equivalent when recording timestamps.

Canonical writable location:

- explicit task directory provided by the user, or
- repo-local `.forgeflow/tasks/<task-id>/` created via `/forgeflow-init` or `python3 scripts/run_orchestrator.py init ...`.

If the task directory is missing, bootstrap or recover it first. Do not jump straight into `src/...` edits while the workflow state lives nowhere.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `run-state.json` or `decision-log.json` are mentioned without an explicit path, write them to the active task directory, not the repository root and not chat-only fallback.

If writing is allowed, write only under the current project workspace or the active task directory. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.


## Strict response constraints

When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.

Bad: adding verdicts, JSON artifacts, rationale sections, or extra warnings after the requested list.
Good: if asked for exactly two checks, return exactly two checks.

When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.

For exact-count list prompts, output numbered lines only. Do not output a dry-run completion sentence, heading, preamble, fenced block, artifact JSON, or verdict. A fenced code block is a format violation for exact-count list prompts.

Example exact-count response must be plain text lines, not a fenced block:

1. Confirm the planned README badge change is limited to the badge markdown.
2. Verify the resulting badge text and link target by manual inspection.

No heading. No preamble. No code fence. No third line. Start directly with `1.`.


## Automation / non-interactive approval mode

If the user explicitly includes `--yes`, `--auto-approve`, `--non-interactive`, or says to continue through ForgeFlow stages without further approval, treat that as approval for the current bounded ForgeFlow sequence. Do not pause at the normal stage-boundary y/n prompt; proceed to the next requested ForgeFlow stage after writing the required artifact for the current stage. This only applies inside the stated task scope and never overrides a blocker, failed verification, missing required artifact, or unsafe/destructive action.

## Procedure

1. Confirm route and current stage. Read `brief.json` to determine route.
2. Initialize `run-state.json` in the active task directory if it does not exist. Set `current_stage: "execute"`, `status: "in_progress"`.
3. Read `contracts` metadata and sibling `contracts.md` before editing when present.
   - **Environment safety net**: If `brief.json` lacks `environment_preflight`, run: `git rev-parse --is-inside-work-tree 2>/dev/null; ls node_modules .venv vendor 2>/dev/null | head -3`. If dependencies are missing and a package manager is detected, stop and ask: "종속성이 설치되지 않았습니다. 설치를 먼저 진행하시겠습니까?" Do NOT attempt installation yourself. If no git and route is medium/high, warn that ship cannot commit/PR, then continue.
3b. **Git worktree isolation**:
    - If `brief.json` has `"use_worktree": true`, the Python runtime creates a git worktree via `git worktree add --detach` and records it in `run-state.json.worktree.path`.
    - The worktree is a real git worktree (not a Claude Code `EnterWorktree`). The agent must work in the worktree directory using the **absolute path** from `run-state.json.worktree.path`.
    - **File operations**: Use the worktree path as the base directory for all edits. Example: if `run-state.json.worktree.path` is `/tmp/ff-worktree-abc123`, edit files at `/tmp/ff-worktree-abc123/src/foo.ts` instead of `./src/foo.ts`.
    - **Git commands**: Run git commands with `cwd` set to the worktree path, not the original repo.
    - **Verification**: Run lint/build/test from the worktree directory.
    - **Agent delegation**: When spawning sub-agents for parallel steps, pass the worktree path as the working directory in the prompt.
    - If `use_worktree` is `false` or missing, execute in the current working tree.
    - After execute completes, the runtime's `merge_worker_worktree()` applies the diff back via patch. The agent should NOT attempt manual merge — only the runtime handles merge.
4. For each task in the plan:
   - **TDD Red**: Write/update tests to fail.
   - **Execute Implementation**: Implement minimal code to pass. Prefer the smallest implementation that satisfies the acceptance criteria.
   - **Context budget**: Do not re-read a file already in context unless it was edited since. Before reading a file, ask: “Do I need the full content, or just a specific section?” If the latter, read only the relevant lines using offset/limit. Batch multiple file inspections into parallel tool calls where possible.
   - **Implementation Notes**: When a decision is made that was not in the plan, when the implementation deviates from the spec, when a tradeoff is chosen, or when an open question arises — **append an entry to `implementation-notes.md` immediately**. Do not batch these until the end.
   - **TDD Refactor**: Clean up implementation.
   - **Architectural Depth**: Ensure implementation follows the plan’s architectural intent (Depth, Leverage, Locality) and avoids creating new shallow modules (see `docs/refactor-planning-decision.md`).
   - If blocked, apply **Hypothesis-Driven Debugging**.
   - Nothing speculative: no drive-by abstractions, unrelated cleanup, hidden migrations, or “while I’m here” rewrites unless the approved plan names them.
5. Apply adapter-aware execution: use the chosen backend for implementation mechanics, but keep ForgeFlow artifacts, gates, and evidence paths backend-neutral. If the backend cannot produce required evidence, record that limitation in `decision-log.json` and block or downgrade the affected verification gate instead of silently proceeding.
6. Treat `fulfills`, `journeys`, and `verify_plan` as verification obligations, not decoration.
7. Run focused verification after each meaningful change.
8. Update `run-state.json` immediately when starting and finishing each step. Step state must be incremental: `step-1: pending → in_progress → completed`, then `step-2: pending → in_progress → completed`. Do not batch-mark all steps as `completed` only at the end. If a step cannot finish, mark it `blocked` or `failed` with evidence.
   - **Contract checkpoint**: Before marking any plan task complete, verify: "Does this code violate a stated contract from contracts.md or DECISIONS.md?" Record in evidence as `contract_check:PASS <task>` or `contract_check:FAIL <task> reason="..."`.
9. After all steps complete, set `run-state.status = "completed"` and `run-state.completed_gates` to include all passed gates.
10. Stop if requirements become ambiguous; return to `/forgeflow:clarify`.
11. Deliver the route-aware exit prompt (see Exit Condition above). **완료 보고를 반드시 사용자에게 출력**:
    1. 완료 요약 (1-2문장, 한국어)
    2. 검증 결과: lint/build/test 각각 pass/fail + 숫자
    3. 변경 파일 목록
    4. 주의사항 (있는 경우): contract_check 실패, environment warning, 미해결 decisions
    Do NOT auto-proceed to the next stage. 반드시 사용자가 다음 단계를 실행하도록 대기.

Contract-aware execution rules:

- Do not change an interface or invariant named in `contracts` unless the plan explicitly authorizes it.
- For each step with `fulfills`, record evidence against those requirement/sub-requirement IDs.
- For each journey in `journeys`, preserve end-to-end verification until `/forgeflow:review`; a passed unit test alone is not enough for a journey gate.
- If `verify_plan` exists and a target cannot be verified, mark the task blocked instead of pretending it is done.

Worker self-report is not approval. `/forgeflow:review` still has to happen.

## Agent delegation for specialist work

When `brief.json` includes `required_specialists` and the task scope justifies delegation, use the Agent tool to spawn specialist sub-agents for independent plan steps. This prevents context exhaustion and enables parallel execution.

### When to delegate

Delegate to a sub-agent when ALL of these conditions are met:
1. `brief.required_specialists` lists a relevant specialist (e.g., `frontend-execute`, `backend-execute`)
2. The plan step has no unresolved dependencies on other in-progress steps
3. The step involves isolated file changes that won't conflict with parallel work
4. The main context is getting large enough that delegating preserves quality

Do NOT delegate when:
- The step modifies shared files that other steps also touch
- The step is step-1 (environment setup) or the final verification step
- The plan has `parallel_safe: false` and path conflicts exist
- The task is `small` route (overhead exceeds benefit)

### How to delegate

Use the Agent tool with `subagent_type: "general-purpose"` and provide the specialist's domain instructions from the corresponding agent definition file under `adapters/targets/<adapter>/agents/forgeflow-<specialist>-worker.md`:

```
Agent({
  description: "Frontend specialist: implement <step objective>",
  prompt: "You are a ForgeFlow frontend worker. Task: <step objective>.
           Working directory: <worktree-path from run-state.json.worktree.path>
           Files to change: <exact paths relative to worktree>. Acceptance criteria: <from plan step>.
           Write run-state evidence as contract_check:PASS <step-id>.
           Do not modify files outside the listed scope.
           Run verification from the worktree directory."
})
```

### Agent result handling

After the agent returns:
1. Verify the claimed changes exist (`git diff --stat`)
2. Run verification commands to confirm the agent's evidence
3. Update `run-state.json` with the verified result — agent self-report alone is not evidence
4. Record the delegation in `decision-log.json` with `category: "agent-delegation"`

### Parallel delegation

For steps with no mutual dependencies (check `plan.json` → `steps[].dependencies`):
- Spawn multiple agents in a single message with parallel Agent tool calls
- Each agent must receive its exact file scope to prevent conflicts
- After ALL agents return, run cross-document consistency checks
- Mark steps completed only after verification, not when agents report done

## Execute Intelligence (v0.2)

When the orchestrator enters the `execute` stage, it automatically injects three intelligence layers into `decision-log.json` and `run-state.json`:

1. **Execute Context** (`execute-intelligence` actor): reads `plan-ledger.json` and generates a structured prompt showing the current task, its dependencies, files to edit, required gates, and attempt count. Check `decision-log.json` entries with `category: "execute-context"` for the formatted prompt.

2. **Progress Tracking** (`progress-tracker` actor): calculates per-task and overall completion percentage, identifies next-actionable tasks (pending tasks whose `depends_on` are all done), and writes the `progress` object to `run-state.json`. If anomalies are detected (excessive attempts, stage retries, too many concurrent tasks), warnings appear as `category: "anomaly-warning"` entries.

3. **Stuck Detection** (`stuck-detector` actor): monitors four signals:
   - `attempt_threshold`: task attempted 4+ times → critical
   - `test_regression`: test failures increased 50%+ from external signals → critical
   - `file_edit_loop`: same file edited 5+ times across tasks → warning
   - `stage_retry_threshold`: execute stage retried 4+ times → critical

   When a critical signal fires, the orchestrator sets `run-state.status = "blocked"` and logs an `escalation` entry. The agent should then pause, reconsider the approach, or ask the user for guidance instead of continuing to retry.

### How to use these as an agent

- At the start of each execute turn, inspect `run-state.json` first for current status, progress, blockers, and next actionable steps. If status is stale/unknown, use `python3 scripts/forgeflow_monitor.py --tasks .forgeflow/tasks --recent 10` for read-only workspace triage before editing.
- Then read `decision-log.json` for the latest `execute-context` entry — it tells you exactly what to work on.
- Check `run-state.json` → `progress` for overall status and `next_actionable` tasks.
- If `run-state.status` is `"blocked"` with stuck signals, do NOT continue editing. Report the stuck condition and suggest alternatives.
- To provide external test regression signals, call `detect_stuck(task_dir, external_signals={"test_failures_before": N, "test_failures_after": M})`.

## UX guardrails

- Treat the latest executable brief/plan as sufficient authority only after the user has approved entering `/forgeflow:execute`.
- If `/forgeflow:execute` was reached without explicit user approval after the previous stage-boundary question, stop immediately and ask for approval instead of editing files. Do not infer approval from the agent's own prior question.
- 이미 승인된 run scope 안에서는 반복적으로 계획을 다시 허락받지 않는다.
- Do not pause just to reconfirm the same plan before editing files.
- Only bounce back to `/forgeflow:clarify` when scope genuinely changed or a blocker invalidates the current brief/plan.
- When the user asks to fix review findings, treat that as approval to enter a fix loop for the current review scope: read the latest `review-report.json`, fix only current `open_blockers`/major findings, re-run focused verification, and update `review-report.json` before claiming the fix loop is complete. The updated `open_blockers` must reflect the remaining current blockers, not stale blockers from the previous review.
- Bad: `승인된 계획대로 실행하겠습니다.`만 말하고 대기.
- Good: 바로 수정/검증을 시작하고 evidence를 남긴다.

## Bounded verification fix loop

When a lint/build/test/typecheck command fails after an implementation change, do not stop at the first failure. Record each failed command, exit code, and concise failure summary in `run-state.json.evidence_refs` using a compact string such as `verification:FAIL attempt=1 command="npm run lint" exit=1 reason="react-hooks/set-state-in-effect"`, increment `run-state.retries.execute`, apply the smallest scoped fix, then rerun the focused verification. Repeat for at most 3 attempts. Mark work complete only after the latest required verification passes and add a final `verification:PASS ...` evidence ref; if failures remain, set `run-state.status` to `blocked` and keep the latest failure evidence.

Classify the failure layer before applying the fix. Use one of Instructions, Tools, Environment, State, Feedback, or Implementation, and include `layer=<name>` in the `verification:FAIL` evidence when useful. The loop is observe → classify layer → smallest scoped fix → rerun the same or narrower verification gate → record `verification:PASS`; Environment or Tools failures that require installation, permissions, destructive cleanup, or external service access must stop for user approval instead of being silently worked around.
