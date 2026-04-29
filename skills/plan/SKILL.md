---
name: plan
description: Create an executable ForgeFlow plan with exact tasks, files, acceptance criteria, and verification steps.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must default to artifact-first behavior and produce schema-valid `plan.json` in the active task directory unless the user explicitly requests dry-run or no-write output.
  Must keep contracts, fulfills, journeys, and verify_plan consistent when present.
---

# Plan

Use this skill to turn a ForgeFlow brief or requirements document into an executable task plan.

## Input

- `brief.json` or equivalent brief
- `requirements.md` if available
- Codebase context
- Route selected by `/forgeflow:clarify`

## Output Artifacts

- `plan.json` or equivalent plan containing:
  - task IDs
  - exact files to change
  - dependencies
  - acceptance criteria
  - verification commands
  - risk notes
- `plan-ledger.json` starter shape for medium/large routes when useful

When writing `plan.json`, it **must** conform to `schemas/plan.schema.json` exactly:

```json
{
  "schema_version": "0.1",
  "task_id": "readme-badge-task",
  "steps": [
    {
      "id": "step-1",
      "objective": "Identify the README badge location and desired badge text.",
      "dependencies": [],
      "expected_output": "Badge location and target badge content are known.",
      "verification": "Manual inspection of README badge location and requested badge content.",
      "rollback_note": "No repository files changed during planning.",
      "fulfills": ["R1"]
    }
  ],
  "verify_plan": [
    {"target": "R1", "type": "sub_req", "gates": ["manual_review"]}
  ]
}
```

`steps[].fulfills` and top-level `verify_plan` are required even for minimal written `plan.json`. For small tasks, create a simple requirement ID such as `R1` and make every step fulfill it.

Do not add non-schema fields such as `route`, `tasks`, `files_to_change`, `acceptance_criteria`, `verification_commands`, or `route_selection_rationale` to `plan.json`.

## Contract-first traceability for medium/large or brownfield work

For non-trivial work, plan the cross-module contract before task decomposition:

1. Identify interfaces, invariants, data shapes, and compatibility constraints that parallel workers must not break.
2. If any contract exists, write it into optional `contracts` metadata and/or a sibling `contracts.md` artifact.
3. Add `fulfills` links on steps when requirements or sub-requirements are known.
4. Add `verify_plan` entries for each fulfilled requirement/sub-requirement and each journey.
5. Add `journeys` for multi-step user or system flows that require end-to-end verification.

Optional contract-aware `plan.json` fields:

```json
{
  "contracts": {
    "artifact": "contracts.md",
    "interfaces": ["StorageAPI accepts normalized records"],
    "invariants": ["Existing public CLI flags remain backward compatible"]
  },
  "journeys": [
    {"id": "J1", "description": "User completes the changed flow", "composes": ["R1.1", "R2.1"]}
  ],
  "verify_plan": [
    {"target": "R1.1", "type": "sub_req", "gates": ["test", "review"]},
    {"target": "J1", "type": "journey", "gates": ["e2e"]}
  ]
}
```

Small documentation-only tasks may omit these fields. If the fields are present, they must be internally consistent and pass sample artifact validation.

## Minimum plan gate

Before crossing `plan → run`, the plan must make these sections explicit in `plan.json`, a sibling plan note, or the response artifact:

- `Goal`
- `Requirements`
- `Implementation Steps`
- `Verification`

## Refactor mode

Use refactor mode inside this existing plan flow when the requested work is primarily a behavior-preserving structural change across an existing public surface, a migration-sensitive internal reorganization, test-sensitive decomposition work, or removal/replacement of implementation machinery while preserving user-visible behavior.

Refactor mode is a planning branch, not a new `/forgeflow:refactor-plan` command, stage, approval gate, schema lane, or separate source of truth. `schemas/plan.schema.json` remains authoritative unless a separate decision proves a schema change is needed. If a refactor-specific requirement cannot be represented by existing `plan.json` fields or a named sibling markdown section, stop and produce a schema/decision note before execution.

When refactor mode applies, the plan must include:

- preserved public behavior statement, or a decision explaining why the refactor is internal-only
- explicit non-goals
- migration boundary
- rollback, escape hatch, or explicit not-applicable note for contained internal refactors
- tiny always-green implementation steps
- regression verification strategy focused on public behavior over implementation-detail tests
- note on whether existing tests cover the affected public behavior

Representation rules:

- preserved behavior maps to `Requirements`, `steps[].objective`, `steps[].fulfills`, and `verify_plan`
- non-goals live in a sibling plan note section named `Non-goals`
- migration boundaries live in a sibling plan note section named `Migration boundary`, or in `contracts.interfaces` / `contracts.invariants` for cross-module seams
- rollback or escape hatch lives in `steps[].rollback_note`
- regression verification lives in `steps[].verification` and top-level `verify_plan`
- existing test coverage lives in a sibling plan note section named `Existing coverage`

See `docs/refactor-planning-decision.md` for the canonical representation decision.

### Requirement traceability

For non-trivial work, carry the requirement map through the executable plan instead of leaving it as prose:

- Each non-trivial step must include `fulfills` with requirement or sub-requirement IDs when requirements are known.
- Every `fulfills` target must have a matching `verify_plan` entry.
- Use `type: "sub_req"` for requirement-level targets and `type: "step"` only when the verification target is the step itself.
- If a step intentionally has no requirement reference, say why in the sibling plan note or response artifact; do not silently create orphan work.

Do not proceed to `/forgeflow:run` if one of those is missing for non-trivial work. For tiny exact-output prompts, preserve the requested format but keep the same information density in the listed steps.

## Exit Condition

- Every task has exact file paths or a justified discovery step
- Every task has verification
- Dependencies form a DAG
- Medium/large routes have enough detail for `/forgeflow:run` without guessing
- The minimum plan gate covers `Goal`, `Requirements`, `Implementation Steps`, and `Verification`
- Refactor-specific checks are present only when refactor mode applies, with preserved behavior, non-goals, migration boundary, rollback or escape hatch, regression verification, and existing coverage represented in existing plan fields or sibling markdown sections
- Contract metadata is present for cross-module work, or explicitly unnecessary
- `fulfills`, `journeys`, and `verify_plan` links are consistent when present
- No placeholder tasks remain

## File write and output discipline

Default to **artifact-first mode**. Plan should write `plan.json` under the active task directory unless the user explicitly asks for a dry run, exact-output response, or no-write simulation.

Canonical writable location:

- explicit task directory provided by the user, or
- repo-local `.forgeflow/tasks/<task-id>/` created via `/forgeflow:init` or `python3 scripts/run_orchestrator.py init ...`.

If the task directory is missing, bootstrap it first. Do not downgrade planning into a chat transcript when the workflow contract expects artifacts.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `plan.json` are mentioned without an explicit path, write them to the active task directory, not the repository root and not chat-only fallback.

If writing is allowed, write only under the current project workspace or the active task directory. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.


## Strict response constraints

When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.

Bad: adding verdicts, JSON artifacts, rationale sections, or extra warnings after the requested list.
Good: if asked for exactly two checks, return exactly two checks.

When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.

For exact-count list prompts, output numbered lines only. Do not output an empty response, heading, preamble, fenced block, summary, artifact JSON, or verdict. A fenced code block is a format violation for exact-count list prompts.

Example exact-count response must be plain text lines, not a fenced block:

1. Identify the README badge location and desired badge text.
2. Update the badge markdown and verify the rendered preview manually.

No heading. No preamble. No code fence. No third line.

## Procedure

1. Read the brief/requirements fully.
2. Inspect the repo for existing conventions.
3. Decompose into small tasks with acceptance criteria.
4. Mark dependency order and parallel safety.
5. Identify risky tasks and required review evidence.
6. For `large_high_risk` work, pressure-test milestone boundaries from five angles before execution:
   - feasibility risks
   - architecture/interface boundaries
   - dependency ordering
   - regression and recovery risks
   - verification strategy
7. Propose `/forgeflow:run` as the next stage and stop for explicit user approval.

Do not code during planning unless the user explicitly asks for a tiny small-route direct execution.

## UX guardrails

- Planning owns plan creation; do not ask the user to make the plan.
- Do not ask for 계획 내용 재승인 when the plan is executable; the agent owns decomposition.
- Do stop before crossing the `plan → run` stage boundary, because execution is a separate stage.
- End with a closed next-stage question such as `계획은 여기까지 확정됐습니다. 다음 스텝으로 `/forgeflow:run`을 진행하시겠습니까? (y/n)`.
- Do not invoke `/forgeflow:run`, the Skill tool, or any execution tool in the same assistant turn after asking the closed next-stage question. The next assistant turn may proceed only after an explicit user approval such as `y`, `yes`, `진행`, or `실행`.
- Bad: `계획 확정. run 직행.`
- Bad: `내가 계획을 세워?`
- Good: `아니요. 계획은 내가 세운다. 아래처럼 진행.`

## Output mode examples

If asked:

```text
/forgeflow:plan For route small, list exactly two plan steps. Do not write files.
```

Return exactly the requested steps in the response. Do **not** create `plan.json` for this dry-run variant.

If asked:

```text
/forgeflow:plan Write plan.json under .forgeflow/tasks/<task-id>
```

Then and only then write `.forgeflow/tasks/<task-id>/plan.json`.
