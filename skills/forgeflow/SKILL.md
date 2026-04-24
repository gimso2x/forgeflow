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

## File write and output discipline

Default to **response-only mode**. Do not call Write/Edit or create artifact files unless the user explicitly asks you to write files or provides a clear writable task directory.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `brief.json`, `plan.json`, or `review-report.json` are mentioned without an explicit writable path, return their content in the chat response as fenced text or concise structured bullets. Do not guess a path in the repository root.

If writing is allowed, write only under the current project workspace or the explicit task directory named by the user. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.

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
