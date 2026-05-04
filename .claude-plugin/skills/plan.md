---
description: Plan the task by decomposing it into ordered, verifiable sub-tasks.
---

# /forgeflow:plan

Create an implementation plan. Only needed for `medium` and `large_high_risk` routes.

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
