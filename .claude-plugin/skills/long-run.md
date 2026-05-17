---
description: Record reusable learnings after high-risk task completion. Produces eval-record.json. High-risk route only unless manually invoked for reusable patterns.
---

# /forgeflow:long-run

Record learnings after high-risk task completion. This is a high-risk route only stage when triggered automatically, but it may be invoked manually after any task where reusable patterns were identified.

## When to run

- Automatically after high-risk route finalize completes.
- Manually via `/forgeflow:long-run` when reusable implementation patterns, verification patterns, or durable failure rules were identified.
- Do **not** require this for small or medium routes.

## Output

Write `.forgeflow/tasks/<task-id>/eval-record.json` with reusable learning only:

```json
{
  "schema_version": "0.1",
  "task_id": "<task-id>",
  "route": "large_high_risk|epic|manual",
  "source_stage": "long-run",
  "reusable_patterns": [],
  "failure_rules": [],
  "evidence_refs": [],
  "recorded_at": "<ISO 8601>"
}
```

## Rules

1. Preserve only learning that can improve future tasks.
2. Include evidence refs from `run-state.json`, review reports, or decision logs.
3. Do not store session chatter, one-off progress, or user-private context.
4. Report whether the record was written and which reusable patterns or failure rules were captured.
