---
description: Plan the task by decomposing it into ordered, verifiable sub-tasks.
---

# /forgeflow:plan

Create an implementation plan. Only needed for `medium` and `high` routes.

## Instructions

1. Read `brief.json` from the active task directory.

2. Decompose the objective into ordered tasks:
   - Each task has: id, description, acceptance criteria, dependencies, estimated complexity
   - Dependencies form a valid DAG
   - No task should exceed ~4 hours estimated work

3. Write `plan-ledger.json`:
   ```json
   {
     "schema_version": "0.1",
     "task_id": "<task-id>",
     "route": "<route>",
     "tasks": [
       {
         "id": "<sub-task-id>",
         "description": "...",
         "acceptance_criteria": ["..."],
         "dependencies": [],
         "status": "pending",
         "complexity": "low|medium|high"
       }
     ],
     "status": "planned"
   }
   ```

4. If design alternatives exist or requirements are ambiguous, record decisions in `decision-log.json` with rationale (e.g. "No retry on timeout — treated as resource bound, not transient"). List possible interpretations when ambiguous.

5. Report: task count, dependency chain, risk notes, next stage (run).

6. **Verify plan gate selection**: When constructing verification gates for `plan.json`, prefer automated gates (`contract_check`, `scope_boundary_check`, `version_consistency_check`, `cross_document_consistency_check`, `total_preservation_check`) over `manual_review` wherever possible. Use `manual_review` only for qualitative judgments. Documentation-only tasks must include at least one automated gate alongside any `manual_review` entry.

## Automation / non-interactive approval mode

If the user explicitly includes `--yes`, `--auto-approve`, `--non-interactive`, or says to continue through ForgeFlow stages without further approval, treat that as approval for the current bounded ForgeFlow sequence. Do not pause at the normal stage-boundary y/n prompt; proceed to the next requested ForgeFlow stage after writing the required artifact for the current stage. This only applies inside the stated task scope and never overrides a blocker, failed verification, missing required artifact, or unsafe/destructive action.
