# Review-summary command decision

Decision: do not add a first-class `review-summary` command yet.

## Why

The current operator surface already exposes the useful summary fields through:

```bash
python3 scripts/run_orchestrator.py status --task-dir <task-dir>
```

`status` returns:

- `task_id`
- `route`
- `current_stage`
- `current_task_id`
- `open_blockers`
- `required_gates`
- `latest_review_verdict`
- `next_action`

That covers the operator question: “can I move forward, and what blocks me?”

The review artifacts themselves remain the source of truth:

- `review-report-spec.json` for `spec-review`
- `review-report.json` or `review-report-quality.json` for `quality-review`
- `run-state.json` approval flags for finalize gating
- `checkpoint.json.latest_review_ref` for persisted review reference

A new command that merely reformats these would add another surface to maintain without enforcing anything new. That is how CLIs become a junk drawer.

## When to reconsider

Add `review-summary` only if at least one of these becomes true:

1. Operators routinely need both spec and quality review verdicts displayed together.
2. `status` becomes too broad and review-specific output starts crowding it.
3. The runtime gains multiple review reports per task and needs deterministic selection rules.
4. CI or another tool needs machine-readable review rollup output independent of general status.

## Proposed future output, if needed

If implemented later, `review-summary` should be read-only and return:

```json
{
  "task_id": "...",
  "route": "large_high_risk",
  "current_stage": "quality-review",
  "spec_review": {
    "artifact": "review-report-spec.json",
    "verdict": "approved",
    "approved_by": "spec-reviewer"
  },
  "quality_review": {
    "artifact": "review-report-quality.json",
    "verdict": "blocked",
    "approved_by": null
  },
  "approval_flags": {
    "spec_review_approved": true,
    "quality_review_approved": false
  },
  "open_blockers": [],
  "next_action": "fix quality blockers before finalize"
}
```

## Exit condition

For now, use `status` plus direct review artifacts. No new command. Boring answer, correct answer.
