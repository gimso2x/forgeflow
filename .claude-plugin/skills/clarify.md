---
description: Clarify requirements from the user request and produce a verified brief.
---

# /forgeflow:clarify

Clarify the task requirements. Reads or creates `brief.json`.

## Instructions

1. Read existing `brief.json` from `.forgeflow/tasks/<task-id>/` if present.

2. If the user provided a description alongside this command, incorporate it.

3. Ensure the brief contains:
   - Clear, testable objective
   - Constraints and non-goals
   - Risk level
   - Affected files/components (if known)

4. Write/update `brief.json` with status `"clarified"`.

5. Determine next stage:
   - Route `small`: proceed to `/forgeflow:run`
   - Route `medium` or `large_high_risk`: proceed to `/forgeflow:plan`

6. Report: what was clarified, any open questions, next stage.
