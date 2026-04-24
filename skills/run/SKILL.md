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

## Artifact path rule

Artifact names in this skill are workflow contracts. Do not write files inside the plugin installation directory or `skills/<skill>/` directory. If the user asks you to create files, write them in the current project workspace or an explicit task directory. If no writable task directory is clear, return the artifact content in the response instead of guessing a path.

## Procedure

1. Confirm route and current stage.
2. Execute only tasks that belong to the plan/scope.
3. Run focused verification after each meaningful change.
4. Update evidence/decision notes.
5. Stop if requirements become ambiguous; return to `/clarify` or `/specify`.

Worker self-report is not approval. `/review` still has to happen.
