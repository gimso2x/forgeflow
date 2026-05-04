---
description: Execute the planned implementation with evidence-backed verification.
---

# /forgeflow:run

Implement the task. Updates `run-state.json` with progress and verification evidence.

## Instructions

1. Read `brief.json` and `plan-ledger.json` (if route requires planning).

2. For `small` route: implement the full objective directly.
   For `medium`/`large_high_risk`: work through plan tasks in dependency order.

3. For each sub-task or implementation step:
   - Make the smallest useful change
   - Run verification commands (lint, build, test) that actually exist
   - Record results in `run-state.json`

4. `run-state.json` format:
   ```json
   {
     "schema_version": "0.1",
     "task_id": "<task-id>",
     "status": "running|completed|failed",
     "progress": {
       "percentage": 0-100,
       "current_task": "<sub-task-id>",
       "completed_tasks": []
     },
     "evidence": [
       {
         "command": "...",
         "exit_code": 0,
         "summary": "..."
       }
     ],
     "updated_at": "<ISO 8601>"
   }
   ```

5. **Rules**:
   - `progress.percentage` must be recalculated on every write
   - Timestamps must be real ISO 8601 (not placeholder zeros)
   - Only report commands that exist — verify before claiming
   - If verification fails, record the failure; do not mark complete

6. When all tasks are done: set status `"completed"`, report files changed and verification summary.
