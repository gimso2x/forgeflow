---
name: forgeflow
description: Artifact-first delivery workflow for AI coding agents. Use when a user types /forgeflow, /forgeflow:<stage>, or asks to implement, refactor, debug, review, or ship code through clarify, route selection, artifacts, gates, and independent review.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must route work through explicit ForgeFlow stages and artifact-backed gates.
  Must preserve stage boundaries, verification evidence, and independent review semantics.
  Must not treat ForgeFlow as a chat-only ritual when task artifacts are required.
---

# ForgeFlow

ForgeFlow turns agent work into explicit stages with artifacts, gates, and independent review.

## Slash-style entrypoints

Claude Code may expose native slash commands. Codex exposes plugin skills, so these same strings are prompt triggers that dispatch to the matching ForgeFlow skill:

- `/forgeflow` -> this overview workflow skill
- `/forgeflow:init ...` -> `init`
- `/forgeflow:clarify ...` -> `clarify`
- `/forgeflow:specify` -> `specify`
- `/forgeflow:plan` -> `plan`
- `/forgeflow:run` -> `run`
- `/forgeflow:review` -> `review`
- `/forgeflow:ship` -> `ship`
- `/forgeflow:finish` -> `finish`

Do not require `CODEX.md` before plugin use. `CODEX.md` and project presets are optional project-local hardening surfaces.

## Input

- User request or issue
- Target repository/path
- Constraints, acceptance criteria, and risk notes if available
- Existing artifacts if the task is already in progress

## Output Artifacts

At minimum, produce or update the artifacts appropriate for the selected route:

- `brief.json` or equivalent brief: clarified objective, constraints, risk, route
- `run-state.json`: current stage and completed gates
- `plan-ledger.json` for medium/large routes: planned steps, task status, gate evidence
- `review-report.json`: independent review result; worker self-report is not enough
- final summary: changed files, verification evidence, residual risks

## Exit Condition

The task is complete only when:

- route is explicitly selected: `small`, `medium`, or `large_high_risk`
- required stages for that route are complete
- review gates are satisfied by evidence, not by vibes
- verification commands have passed or failures are explicitly documented
- final response names artifacts/evidence used for finalize

## Route model

```text
small: clarify -> execute -> quality-review -> finalize
medium: clarify -> plan -> execute -> quality-review -> finalize
large_high_risk: clarify -> plan -> execute -> spec-review -> quality-review -> finalize -> long-run
```

## File write and output discipline

Default to **artifact-first mode**. ForgeFlow is not a chat-only ritual. Unless the user explicitly asks for a dry run, exact-output response, or no-write simulation, create/update the canonical task artifacts under the active task directory.

Canonical writable location:

- explicit task directory provided by the user, or
- repo-local `.forgeflow/tasks/<task-id>/` resolved by `/forgeflow:init` or the orchestrator runtime.

If the task directory does not exist yet, bootstrap it first with `/forgeflow:init` or `python3 scripts/run_orchestrator.py init ...` before clarify/plan/run/review/ship. Do not skip straight to source edits when the artifact workspace is missing.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When a user names artifacts such as `brief.json`, `plan.json`, or `review-report.json` without a path, assume the active task directory, not chat-only fallback. Do not guess a repo-root artifact path outside `.forgeflow/tasks/<task-id>/`.

If writing is allowed, write only under the current project workspace or the active task directory. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.


## Strict response constraints

When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.

Bad: adding verdicts, JSON artifacts, rationale sections, or extra warnings after the requested list.
Good: if asked for exactly two checks, return exactly two checks.

When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.

## Rules

1. Start with clarify unless the user provides a complete brief.
2. Pick the smallest route that honestly covers the risk.
3. Do not skip plan for medium or large/high-risk work.
4. Do not merge `spec-review` and `quality-review`.
5. Do not treat the implementer's own summary as approval.
6. Keep state in artifacts/files, not just chat history.
7. If using ForgeFlow's local runtime, remember default `execute` is stub; real provider CLI execution requires `--real` and `execution_mode: real` in the payload.

## Operator prompts

Small task:

```text
Use ForgeFlow. Clarify this request, choose the route, execute the smallest safe change, then state what evidence justifies quality-review and finalize.
```

Medium task:

```text
Use ForgeFlow. Clarify first, select the route, write a concrete plan with expected artifacts and verification, then execute only after the plan is clear.
```

Large/high-risk task:

```text
Use ForgeFlow. Treat this as large/high-risk. Clarify, plan, execute, run spec-review and quality-review separately, and call out residual risk before finalize.
```
