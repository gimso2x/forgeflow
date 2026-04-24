---
name: run
description: Execute a ForgeFlow plan with verification and runtime evidence. Use for implementation after clarify/plan.
version: 0.1.0
author: gimso2x
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
- Next step is `/review`

## File write and output discipline

Default to **response-only mode**. Do not call Write/Edit or create artifact files unless the user explicitly asks you to write files or provides a clear writable task directory.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `brief.json`, `plan.json`, or `review-report.json` are mentioned without an explicit writable path, return their content in the chat response as fenced text or concise structured bullets. Do not guess a path in the repository root.

If writing is allowed, write only under the current project workspace or the explicit task directory named by the user. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.


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
7. Stop if requirements become ambiguous; return to `/clarify` or `/specify`.

Contract-aware execution rules:

- Do not change an interface or invariant named in `contracts` unless the plan explicitly authorizes it.
- For each step with `fulfills`, record evidence against those requirement/sub-requirement IDs.
- For each journey in `journeys`, preserve end-to-end verification until `/review`; a passed unit test alone is not enough for a journey gate.
- If `verify_plan` exists and a target cannot be verified, mark the task blocked instead of pretending it is done.

Worker self-report is not approval. `/review` still has to happen.
