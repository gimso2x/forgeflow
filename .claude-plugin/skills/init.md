---
description: Initialize a new ForgeFlow task with task-id, objective, and risk level.
---

# /forgeflow:init

Initialize a ForgeFlow task. Creates the task directory and brief artifact.

## Instructions

1. Ask the user for (or accept as arguments):
   - `task-id`: short identifier (e.g. `feat-auth`, `fix-login`)
   - `objective`: one-sentence description of what to accomplish
   - `risk`: `low`, `medium`, or `high` (default: `medium`)

2. Create the task directory: `.forgeflow/tasks/<task-id>/`

3. Write `brief.json`:
   ```json
   {
     "schema_version": "0.1",
     "task_id": "<task-id>",
     "objective": "<objective>",
     "risk": "<risk>",
     "status": "init",
     "created_at": "<ISO 8601 timestamp>"
   }
   ```

4. Determine route based on risk:
   - `low` → `small` (skip plan, go straight to run)
   - `medium` → `medium` (plan → run → review)
   - `high` → `large_high_risk` (full pipeline with verify)

5. Report: task-id, route, next stage (clarify).
