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
     "status": "not_started|in_progress|completed|blocked",
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
   - Do not add features or edge-case handling not in the brief. Only implement what is explicitly required.

6. **Scope gate**: Before implementing, list each requirement from brief/plan. Every line of code must trace to a stated requirement. Remove any feature not in the brief immediately.

7. **Test isolation**: Tests must pass independently via `python -m pytest tests/ -v` in a fresh shell.
   - Use `tmp_path` fixtures for files/DBs. No shared `reset_database()` patterns.
   - External resources (servers) must be started in fixtures, not assumed running.
   - Module-level mutable state must be isolated per test via `monkeypatch` or snapshot/restore.
   - Never hard-code ports. Use OS-assigned or `unused_port` fixtures.
   - Tests must pass in any execution order.

8. **State management**: Avoid module-level mutable state.
   - No `db_connection = None` style globals. Use constructors or context managers.
   - When globals are unavoidable, provide a reset function and isolate in tests.
   - Prefer class instances or function parameters over module-level state.

9. **Design assumptions**: When a requirement is ambiguous, state the decision before implementing.
   - Add `# DESIGN DECISION: ...` comments with rationale for unstated choices (retry behavior, defaults, error strategy).
   - Record in `decision-log.json`. Include "why", not just "what".

10. When all tasks are done: set status `"completed"`, report files changed and verification summary.

## Bounded verification fix loop

When a lint/build/test/typecheck command fails after an implementation change, do not stop at the first failure. Record each failed command, exit code, and concise failure summary in `run-state.json.evidence_refs` using a compact string such as `verification:FAIL attempt=1 command="npm run lint" exit=1 reason="react-hooks/set-state-in-effect"`, increment `run-state.retries.execute`, apply the smallest scoped fix, then rerun the focused verification. Repeat for at most 3 attempts. Mark work complete only after the latest required verification passes and add a final `verification:PASS ...` evidence ref; if failures remain, set `run-state.status` to `blocked` and keep the latest failure evidence.

## Automation / non-interactive approval mode

If the user explicitly includes `--yes`, `--auto-approve`, `--non-interactive`, or says to continue through ForgeFlow stages without further approval, treat that as approval for the current bounded ForgeFlow sequence. Do not pause at the normal stage-boundary y/n prompt; proceed to the next requested ForgeFlow stage after writing the required artifact for the current stage. This only applies inside the stated task scope and never overrides a blocker, failed verification, missing required artifact, or unsafe/destructive action.
