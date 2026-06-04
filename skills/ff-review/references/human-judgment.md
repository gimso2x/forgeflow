# Human Final Judgment Gate

AI review results are **advisory**, not auto-approval. The review report is a structured recommendation. The human decides what to act on.

## Advisory label system

Every finding carries a confidence level that determines how it should be treated:

- **HIGH confidence** (observed evidence): Finding is based on directly inspected code, command output, or file content. The human should treat this as actionable unless they have context the reviewer doesn't.
- **MEDIUM confidence** (reported evidence): Finding is based on executor claims, CI output, or third-party reports. The human should verify before acting.
- **LOW confidence** (inferred): Finding is based on patterns, heuristics, or assumptions without direct evidence. The human should validate before acting. All evidence-less comments are LOW confidence by definition.
- **CONFLICT**: Two reviewer roles disagree. Marked with `⚠ requires human decision`. The human must resolve — the report records both positions without taking sides.

Record confidence level in each finding:
```
- **Confidence**: HIGH | MEDIUM | LOW | CONFLICT
```

## Priority classification

Findings are surfaced to the human in this priority order:

1. **Blocker** — Must be resolved before any approval. AI will never approve with open blockers.
2. **Major** — Should be resolved. AI may approve with major findings only if human explicitly accepts the risk.
3. **Conflict** (⚠) — Requires human decision regardless of severity.
4. **Minor** — Advisory. Human decides whether to address.
5. **Nit** — Low-priority suggestions. May be evidence-less observations.

## Override process

The human can override any AI finding:

- **Dismiss**: Mark a finding as `dismissed` with a reason. Record in the report: `Overridden by <human>: <reason>`.
- **Escalate**: Promote a minor/nit to major. Record: `Escalated by <human>: <reason>`.
- **Accept risk**: Accept a blocker/major as-is. Record: `Risk accepted by <human>: <reason>`. This is the only way to ship with unresolved major findings.

Overrides are recorded in `review-report.md` → **Override Log** section:
```
## Override Log
- Finding <N>: <action> by <human> — "<reason>"
```

A review with overrides must still be written to the artifact before it counts. Chat overrides without artifact updates are not binding.

## Ship gate

- Pipeline mode: Ship requires explicit human confirmation (`/forgeflow:ship`). AI `approved` verdict enables but does not execute ship unless `--auto` is active.
- Standalone mode: The review report is the final artifact. No ship stage exists unless the user explicitly starts a pipeline from the review output.
- `--auto` mode: AI may proceed to ship after `approved`, but only when all conditions are met (verdict=approved, safe_for_next_stage=yes, open_blockers=none, no unresolved conflicts). `--auto` does not override human judgment — it automates the mechanical step after judgment is complete.
