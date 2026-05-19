---
description: Clean up and finalize a ForgeFlow task — mark complete, summarize.
---

# /forgeflow:finish

Finalize and clean up a completed ForgeFlow task.

## Instructions

1. Read all artifacts from `.forgeflow/tasks/<task-id>/`.
   - If `run-state.json` contains a `worktree` key or `brief.json` has `use_worktree: true`, handle git worktree cleanup:
     - Merge completed worker worktrees back to the original repo via `merge_worker_worktree()`.
     - Verify merged changes with `git diff --stat`.
     - After finish option is applied, remove the worktree with `git worktree remove <path>` (or leave it if user chose "keep").

2. Verify the task lifecycle:
   - `brief.json` status is `"clarified"` or later
   - `run-state.json` status is `"completed"` (or eval-record shows `"shipped"`)
   - If review was required: `review-report.json` has `"approved"` verdict

3. Generate a summary:
   - What was requested (objective)
   - What was done (files changed, verification results)
   - Review outcome
   - Any open items or follow-ups

4. Report the summary to the user.

5. Optionally archive or clean up the task directory if the user confirms.

6. **Evolution and learning capture**: After finish action completes, run:
   ```bash
   python3 scripts/forgeflow_learn.py extract .forgeflow/tasks/<task-id> --output .forgeflow/evolution/learnings.jsonl
   python3 scripts/forgeflow_learn.py validate .forgeflow/evolution/learnings.jsonl
   python3 scripts/forgeflow_evolution.py observations --task <task-id> --json
   python3 scripts/forgeflow_evolution.py suggest --task <task-id> --json
   ```
   Report extracted learnings count and any suggestions. Do NOT auto-promote or auto-approve rules.


## Status analysis preflight

Read `run-state.json`, review/eval artifacts, and `decision-log.json` from the active `.forgeflow/tasks/<task-id>/` before acting. For multi-task triage, run `python3 scripts/forgeflow_monitor.py --tasks .forgeflow/tasks --recent 10` as read-only evidence; then inspect the selected artifacts directly.
