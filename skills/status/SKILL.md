---
name: status
description: Show current ForgeFlow task status, project task list, and active blockers. Use when the user types /status or /forgeflow:status, or asks what's the status, 현재 상태, 진행 상황, 뭐 하고 있었지, or wants to see all tasks in the project.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must list tasks under the active project storage root.
  Must show task ID, current stage, status, and route for each task.
  Must highlight blocked tasks and active blockers.
  Must work without any running provider — reads artifacts from disk only.
  Must not modify any artifacts.
dependencies:
  - skills/_shared/discipline.md
---

# Status

Use this skill to display the current status of ForgeFlow tasks for the active project.

## Input

- `--task-dir <path>`: Show detailed status for a specific task (optional)
- `--project-dir <path>`: Project root to resolve storage path (defaults to current working directory)
- No arguments: show all tasks for the current project

## Output

Prints a status report to the user. Does **not** write any artifacts.

## Procedure

1. **Resolve project storage root**:
   ```bash
   python3 <forgeflow-checkout>/scripts/forgeflow_storage.py --project-dir <repo-root> --resolve
   ```
   This outputs `<storage-root>`. If it fails, report that ForgeFlow is not initialized for this project and suggest running `/forgeflow:ff-config`.

2. **If `--task-dir` is provided**: show detailed status for that single task:
   - Read `<task-dir>/run-state.json` for task identity and project info
   - Read `<task-dir>/checkpoint.md` for current stage, status, next action, and blockers
   - Read `<task-dir>/brief.md` YAML frontmatter for route, specialist, and scope boundary
   - Read `<task-dir>/ledger.md` for task item progress summary
   - Print:
     ```
     Task: <task-id>
     Stage: <current stage> | Status: <status>
     Route: <route> | Specialist: <primary>
     Next Action: <from checkpoint.md>
     Blockers: <from checkpoint.md or "none">
     Scope: <files_planned> files planned, boundary: <boundary_status>
     
     Ledger Summary:
       done: N | in_progress: N | blocked: N | pending: N | discarded: N
     ```

3. **If no `--task-dir`**: scan `<storage-root>/tasks/` for all task directories:
   - For each directory that contains `run-state.json`:
     - Read `checkpoint.md` (or `brief.md` if checkpoint doesn't exist) for stage and status
     - Read `brief.md` YAML frontmatter for route
   - Print a summary table:
     ```
     ForgeFlow Project: <project-name> (<project-slug>)
     Storage: <storage-root>
     
     Tasks:
       <task-id-1>  | clarify  | in_progress | medium  | Blockers: 2
       <task-id-2>  | ship     | completed   | small   | 
       <task-id-3>  | execute  | blocked     | high    | Blockers: 1
     
     Summary: 3 tasks (1 active, 1 completed, 1 blocked)
     ```

4. **Highlight blocked tasks**: If any task has status `blocked`, print an additional section:
   ```
   ⚠ Blocked Tasks:
     <task-id>: <blocker description from checkpoint.md>
   ```
   Suggest running `/forgeflow:unstuck` or `/forgeflow:ff-review` for resolution.

5. **Learning preflight (optional)**: If `<storage-root>/learning/` exists, show the count of learning candidates:
   ```
   Learning: N candidates accumulated (run /forgeflow:long-run to process)
   ```

## Exit Condition

- Status report has been displayed to the user
- No artifacts were modified

## Constraints

- **Read-only**: This skill never writes, modifies, or deletes artifacts
- **No provider dependency**: Works entirely from file system artifacts
- **Graceful degradation**: If a task directory has partial artifacts (e.g., missing checkpoint.md), show what is available and note the gap

## Output mode examples

For label-only requests like `/forgeflow:status --task-dir ~/.forgeflow/projects/my-app/tasks/feat-auth-a3f`:
Return the stage name only (e.g., `execute`).
