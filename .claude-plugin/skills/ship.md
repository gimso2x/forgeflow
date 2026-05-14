---
description: Ship the completed and reviewed work — commit, push, and finalize.
---

# /forgeflow:ship

Ship reviewed work. Requires an `approved` review report.

## Instructions

1. Read `review-report.json` from the task directory.

2. Gate check:
   - `verdict` must be `"approved"`
   - `safe_for_next_stage` must be `true`
   - If not approved, refuse and tell user to address review findings first.

3. Stage and commit all task-related changes with a conventional commit message:
   ```
   feat: <objective summary>
   fix: <bug summary>
   ```
   Reference task-id in the commit body.

4. Push to remote.

5. Write `eval-record.json`:
   ```json
   {
     "schema_version": "0.1",
     "task_id": "<task-id>",
     "outcome": "shipped",
     "review_verdict": "approved",
     "commit_sha": "<sha>",
     "shipped_at": "<ISO 8601>"
   }
   ```

6. Report: commit SHA, files shipped, review verdict.


## Status analysis preflight

Read `run-state.json`, review/eval artifacts, and `decision-log.json` from the active `.forgeflow/tasks/<task-id>/` before acting. For multi-task triage, run `python3 scripts/forgeflow_monitor.py --tasks .forgeflow/tasks --recent 10` as read-only evidence; then inspect the selected artifacts directly.
