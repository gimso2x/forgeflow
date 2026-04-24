---
name: plan
description: Create an executable ForgeFlow plan with exact tasks, files, acceptance criteria, and verification steps.
version: 0.1.0
author: gimso2x
---

# Plan

Use this skill to turn a ForgeFlow brief or requirements document into an executable task plan.

## Input

- `brief.json` or equivalent brief
- `requirements.md` if available
- Codebase context
- Route selected by `/clarify`

## Output Artifacts

- `plan.json` or equivalent plan containing:
  - task IDs
  - exact files to change
  - dependencies
  - acceptance criteria
  - verification commands
  - risk notes
- `plan-ledger.json` starter shape for medium/large routes when useful

## Exit Condition

- Every task has exact file paths or a justified discovery step
- Every task has verification
- Dependencies form a DAG
- Medium/large routes have enough detail for `/run` without guessing
- No placeholder tasks remain

## Artifact path rule

Artifact names in this skill are workflow contracts. Do not write files inside the plugin installation directory or `skills/<skill>/` directory. If the user asks you to create files, write them in the current project workspace or an explicit task directory. If no writable task directory is clear, return the artifact content in the response instead of guessing a path.

## Procedure

1. Read the brief/requirements fully.
2. Inspect the repo for existing conventions.
3. Decompose into small tasks with acceptance criteria.
4. Mark dependency order and parallel safety.
5. Identify risky tasks and required review evidence.
6. Hand off to `/run`.

Do not code during planning unless the user explicitly asks for a tiny small-route direct execution.
