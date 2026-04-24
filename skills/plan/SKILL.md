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

## Procedure

1. Read the brief/requirements fully.
2. Inspect the repo for existing conventions.
3. Decompose into small tasks with acceptance criteria.
4. Mark dependency order and parallel safety.
5. Identify risky tasks and required review evidence.
6. Hand off to `/run`.

Do not code during planning unless the user explicitly asks for a tiny small-route direct execution.

## Output mode examples

If asked:

```text
/plan For route small, list exactly two plan steps. Do not write files.
```

Return exactly the requested steps in the response. Do **not** create `plan.json`.

If asked:

```text
/plan Write plan.json under work/my-task
```

Then and only then write `work/my-task/plan.json`.
