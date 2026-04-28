---
name: specify
description: Derive testable requirements from a ForgeFlow brief before planning. Use when scope needs formal requirements before execution.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must derive behavioral requirements and testable sub-requirements before planning.
  Must include WHERE/risk grounding for non-trivial work when artifact writing is allowed.
---

# Specify

Use this skill when a clarified request needs explicit requirements before planning.

## Input

- `brief.json` or equivalent clarified brief
- Codebase context
- User decisions from clarification

## Output Artifacts

- `requirements.md` containing:
  - decisions and rationale
  - requirements `R1`, `R2`, ...
  - sub-requirements `R1.1`, `R1.2`, ...
  - verification method for each sub-requirement

## Minimum requirements gate

For non-trivial work, `requirements.md` must include these sections before `/forgeflow:plan` consumes it:

- `Goal`
- `Requirements`
- `Implementation Constraints`
- `Verification`

Tiny response-only or exact-output prompts may omit the full artifact, but the response still needs enough Goal, Requirements, and Verification signal for planning.

## Exit Condition

- Every requirement traces to a decision or brief constraint
- Every sub-requirement is testable or manually verifiable
- Non-trivial `requirements.md` includes `Goal`, `Requirements`, `Implementation Constraints`, and `Verification`
- No implementation tasks are created here
- `/forgeflow:plan` can consume the requirements without guessing

## File write and output discipline

Default to **artifact-first mode**. Unless the user explicitly asks for a dry run, exact-output response, or no-write simulation, create/update `requirements.md` under the active task directory so `/forgeflow:plan` can consume the requirements as a file-backed contract.

Canonical writable location:

- explicit task directory provided by the user, or
- repo-local `.forgeflow/tasks/<task-id>/` resolved by `/forgeflow:init` or the orchestrator runtime.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `brief.json`, `plan.json`, or `review-report.json` are mentioned without an explicit writable path, use the active task directory, not chat-only fallback. Do not guess a repo-root artifact path outside `.forgeflow/tasks/<task-id>/`.

If writing is allowed, write only under the current project workspace or the active task directory. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.


## Strict response constraints

When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.

Bad: adding verdicts, JSON artifacts, rationale sections, or extra warnings after the requested list.
Good: if asked for exactly two checks, return exactly two checks.

When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.

If the user asks to list questions, list them in the response. Do **not** call AskUserQuestion or any interactive question tool unless the user explicitly asks for an interactive clarification flow.

For exact-count question prompts, start directly with `1.`. Do not explain that you will generate questions, do not mention the skill/procedure, and do not add any preamble before the numbered list.

Example exact-count response must be plain text lines, not a fenced block:

1. What badge status should the README show?
2. What source of truth should update that badge?

No heading. No preamble. No code fence. No tool call. No third line.

## WHERE grounding

Before deriving requirements for anything non-trivial, calibrate WHERE so the process is neither too heavy for toys nor too light for dangerous work.

Capture these fields when the user has not already provided them:

- `project_type`: user-facing app, API/service, dev tool/library, or infrastructure
- `situation`: greenfield, brownfield extension, brownfield refactor, or hybrid
- `ambition`: toy/experiment, feature/MVP, or product
- `risk_modifiers`: sensitive data, external exposure, irreversible ops, high scale

Risk escalation rules:

| Modifier | Escalate |
|---|---|
| Sensitive data | security and data requirements must be deep |
| External exposure | security and access requirements must be deep |
| Irreversible ops | risk and compatibility requirements must be deep |
| High scale | infrastructure and architecture requirements must be deep |

Situation rules:

- Greenfield: ask enough to define behavior and core architecture, but do not invent enterprise ceremony.
- Brownfield extension: inspect existing code and docs before asking factual questions; ask about decisions and tradeoffs, not facts the repo can answer.
- Brownfield refactor: compatibility, callers, migration path, and rollback are first-class requirements.
- Hybrid: separate new-module behavior from integration constraints.

Output discipline:

- WHERE may appear as a short section in `requirements.md` when writing artifacts.
- For exact-count, dry-run, or response-only prompts, do not force the WHERE interview. Obey the requested output exactly.
- If WHERE exposes a small-but-dangerous task, record the risk explicitly instead of routing it as a casual small task.

## Procedure

1. Read the brief and identify missing decisions.
2. Establish WHERE grounding unless the prompt is an exact-output dry run.
3. For brownfield work, inspect repo facts before asking factual questions.
4. Ask forced-choice questions only when a decision changes implementation shape.
5. Derive requirements downward: goal -> WHERE/context -> decisions -> requirements -> sub-requirements.
6. Keep requirements behavioral, not implementation-flavored.
7. Hand off to `/forgeflow:plan`.
