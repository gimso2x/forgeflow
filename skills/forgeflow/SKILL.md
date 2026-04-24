---
name: forgeflow
description: Artifact-first delivery workflow for AI coding agents. Use when a user asks to implement, refactor, debug, review, or ship code and the work should go through clarify, route selection, artifacts, gates, and independent review.
version: 0.1.0
author: gimso2x
---

# ForgeFlow

ForgeFlow turns agent work into explicit stages with artifacts, gates, and independent review.

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

## Artifact path rule

Artifact names in this skill are workflow contracts. Do not write files inside the plugin installation directory or `skills/<skill>/` directory. If the user asks you to create files, write them in the current project workspace or an explicit task directory. If no writable task directory is clear, return the artifact content in the response instead of guessing a path.

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
