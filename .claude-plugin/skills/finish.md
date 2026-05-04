---
description: Clean up and finalize a ForgeFlow task — mark complete, summarize.
---

# /forgeflow:finish

Finalize and clean up a completed ForgeFlow task.

## Instructions

1. Read all artifacts from `.forgeflow/tasks/<task-id>/`.

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
