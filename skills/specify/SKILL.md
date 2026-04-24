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

## Artifact path rule

Artifact names in this skill are workflow contracts. Do not write files inside the plugin installation directory or `skills/<skill>/` directory. If the user asks you to create files, write them in the current project workspace or an explicit task directory. If no writable task directory is clear, return the artifact content in the response instead of guessing a path.

## Procedure

1. Read the brief and identify missing decisions.
2. Ask forced-choice questions only when a decision changes implementation shape.
3. Derive requirements downward: goal -> context -> decisions -> requirements -> sub-requirements.
4. Keep requirements behavioral, not implementation-flavored.
5. Hand off to `/plan`.
