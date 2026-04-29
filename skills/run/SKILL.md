---
name: run
description: Execute a ForgeFlow plan with verification and runtime evidence. Use for implementation after clarify/plan.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must execute only scoped plan tasks and respect contracts or verify_plan obligations when present.
  Must not treat worker self-report as final approval; review remains required.
---

# Run

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
- Updated `plan-ledger.json` for medium/large routes
- Verification output summary

## Exit Condition

- Planned tasks are implemented
- Verification commands have been run
- Failures are fixed or explicitly recorded
- Runtime evidence exists for review
- Next step is `/forgeflow:review`

## File write and output discipline

Default to **artifact-first mode**. Run should update `run-state.json` before and after code changes, and keep execution evidence in the active task directory unless the user explicitly asks for a dry run, exact-output response, or no-write simulation.

Canonical writable location:

- explicit task directory provided by the user, or
- repo-local `.forgeflow/tasks/<task-id>/` created via `/forgeflow:init` or `python3 scripts/run_orchestrator.py init ...`.

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

## Procedure

1. Confirm route and current stage.
2. Read `contracts` metadata and sibling `contracts.md` before editing when present.
3. Execute only tasks that belong to the plan/scope.
4. Treat `fulfills`, `journeys`, and `verify_plan` as verification obligations, not decoration.
5. Run focused verification after each meaningful change.
6. Update evidence/decision notes.
7. Record artifact updates before claiming progress: if implementation started, `run-state.json` should say so before you brag in chat.
8. Stop if requirements become ambiguous; return to `/forgeflow:clarify` or `/forgeflow:specify`.

Contract-aware execution rules:

- Do not change an interface or invariant named in `contracts` unless the plan explicitly authorizes it.
- For each step with `fulfills`, record evidence against those requirement/sub-requirement IDs.
- For each journey in `journeys`, preserve end-to-end verification until `/forgeflow:review`; a passed unit test alone is not enough for a journey gate.
- If `verify_plan` exists and a target cannot be verified, mark the task blocked instead of pretending it is done.

Worker self-report is not approval. `/forgeflow:review` still has to happen.

## UX guardrails

- Treat the latest executable brief/plan as sufficient authority only after the user has approved entering `/forgeflow:run`.
- If `/forgeflow:run` was reached without explicit user approval after the previous stage-boundary question, stop immediately and ask for approval instead of editing files. Do not infer approval from the agent's own prior question.
- 이미 승인된 run scope 안에서는 반복적으로 계획을 다시 허락받지 않는다.
- Do not pause just to reconfirm the same plan before editing files.
- Only bounce back to `/forgeflow:clarify` or `/forgeflow:specify` when scope genuinely changed or a blocker invalidates the current brief/plan.
- When the user asks to fix review findings, treat that as approval to enter a fix loop for the current review scope: read the latest `review-report.json`, fix only current `open_blockers`/major findings, re-run focused verification, and update `review-report.json` before claiming the fix loop is complete. The updated `open_blockers` must reflect the remaining current blockers, not stale blockers from the previous review.
- Bad: `승인된 계획대로 실행하겠습니다.`만 말하고 대기.
- Good: 바로 수정/검증을 시작하고 evidence를 남긴다.
