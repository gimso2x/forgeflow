---
name: specify
description: Derive testable requirements from a ForgeFlow brief before planning. Use when scope needs formal requirements before execution.
version: 0.1.0
author: gimso2x
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

## Exit Condition

- Every requirement traces to a decision or brief constraint
- Every sub-requirement is testable or manually verifiable
- No implementation tasks are created here
- `/plan` can consume the requirements without guessing

## File write and output discipline

Default to **response-only mode**. Do not call Write/Edit or create artifact files unless the user explicitly asks you to write files or provides a clear writable task directory.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `brief.json`, `plan.json`, or `review-report.json` are mentioned without an explicit writable path, return their content in the chat response as fenced text or concise structured bullets. Do not guess a path in the repository root.

If writing is allowed, write only under the current project workspace or the explicit task directory named by the user. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.

## Procedure

1. Read the brief and identify missing decisions.
2. Ask forced-choice questions only when a decision changes implementation shape.
3. Derive requirements downward: goal -> context -> decisions -> requirements -> sub-requirements.
4. Keep requirements behavioral, not implementation-flavored.
5. Hand off to `/plan`.
