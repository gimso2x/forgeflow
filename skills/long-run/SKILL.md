---
name: long-run
description: Record reusable learnings after high or epic route completion. Produces eval-record.md with evidence-backed reusable patterns, failure rules, and improvement suggestions. High/epic route only unless manually invoked. Use when the user types /long-run or /forgeflow:long-run.
version: 0.5.0
author: gimso2x
dependencies:
  - skills/_shared/discipline.md
  - skills/_shared/isolation.md
validate_prompt: |
  Must preserve only learning that can improve future tasks.
  Must not store session chatter, one-off progress, or user-private context.
  Must produce eval-record.md following templates/eval-record.md format only when reusable patterns or failure rules are identified.
  Must point every pattern or rule back to evidence -- no evidence, no memory.
---

# Long-run

Capture durable signal from high or epic route work. This is not a summary tool -- it is a memory gate that decides what is worth preserving for future tasks.

Shared file-write, cache-location, and provider-E2E claim rules: `_shared/discipline.md`.

## Input

| Artifact | Source |
|----------|--------|
| `brief.md` | Clarify stage |
| `plan.md` | Plan stage |
| `implementation-notes.md` | Execute stage |
| `run-ledger.md` | Execute stage |
| `review-report.md` | Review stage |

## When to run

- Automatically after high or epic route ship completes.
- Manually via `/forgeflow:long-run` when reusable patterns or failure rules were identified during high/epic work.
- Do **not** require this for small or medium routes.

## Capture decision

Before writing anything, answer: **Is this reusable outside the current task?**

Only capture:

- **Reusable workflow patterns**: approaches that worked and can be repeated
- **Durable failure modes**: root causes that will recur
- **Evaluation outcomes**: gate policies that prevented defects
- **Recovery lessons**: how a stuck situation was resolved
- **Project-level operating decisions**: constraints or conventions discovered during work

Do not capture:

- Task status ("Feature X was completed") -- belongs in task artifacts
- Chat summaries or session chatter
- One-off progress notes
- Raw logs or verbose output
- Worker self-congratulation -- the most useless artifact genre yet invented
- Vague sentiments ("The approach worked well") -- if there is no evidence and no reusable rule, it is just a scented candle

## Output Artifacts

| Artifact | Template | Description |
|----------|----------|-------------|
|| `eval-record.md` | `templates/eval-record.md` | Evidence-backed learning record with outcome, patterns, failure rules |
|| `telemetry-event.md` | `templates/telemetry-event.md` | Per-task event log (stage transitions, token usage, boundary alerts) |
|| `metrics-dashboard.md` | `templates/metrics-dashboard.md` | Aggregated period report (stage duration, failure distribution, token cost, route distribution) |

Write `.forgeflow/tasks/<task-id>/eval-record.md` following the format in `templates/eval-record.md`:

- **Outcome**: success | partial | failed
- **What Worked**: specific patterns with evidence references
- **What Failed**: specific failure modes with root causes
- **Reusable Patterns**: patterns worth reusing in future tasks
- **Failure Rules**: anti-patterns or mistakes to avoid
- **Recommendations**: for future tasks of similar nature
- **Memory Recommendation**: optional promotion note; long-run does not write memory directly
- **Evolution Rule Candidates**: optional candidate notes for recurring workflow rules; long-run records candidates only and does not write `.forgeflow/evolution/proposed/` files directly

Every entry must be specific enough that a future agent can act on it without additional context.

## Telemetry Collection

Long-run is responsible for writing per-task telemetry events and generating periodic summary reports.

### Per-task event log

Write `.forgeflow/telemetry/<task-id>.md` following `templates/telemetry-event.md`:

- Record one event block per stage transition (stage_start, stage_complete, stage_fail).
- Record token_usage events when token counts are available from the adapter.
- Record boundary_alert events when route boundaries or isolation safety rules are triggered.
- Each event block includes: event type, stage, duration, tokens used, model, adapter, route, specialist, outcome, and failure_type.

### Periodic summary report

Generate `.forgeflow/telemetry/summary.md` following `templates/metrics-dashboard.md`:

- Aggregate telemetry events across tasks within a reporting period (weekly or monthly).
- Compute stage duration percentiles (p50, p90), failure distribution, token cost by adapter, worktree stability, and route distribution.
- Overwrite the previous summary or create a new period-specific file.

### Surface usage audit

Every 2-4 weeks, run a usage audit before adding or preserving low-use public surface:

```bash
make usage-audit
```

This writes `.forgeflow/telemetry/surface-usage-audit.md` from recent git history plus current `.forgeflow/tasks/` and `.forgeflow/telemetry/` artifacts. Use it to answer:

- Which `/forgeflow:*` entrypoints were actually mentioned recently?
- Which task artifacts are actually being produced?
- Which support/utility skills are mostly inventory cost?
- Does work still converge through the Core workflow rather than fragmenting into many entrypoints?

Zero usage is a maintenance-review signal, not automatic deletion. If the same surface is low-use for two consecutive audits, document why it remains or propose merge/removal in the next harness-improvement task.

## Relationship to memory

`eval-record.md` is the only required long-run artifact in the slim v1.x distribution. This skill does **not** create or update memory directories by default.

When durable learning should be promoted outside the task artifact, write a **Memory Recommendation** in `eval-record.md` instead of mutating memory directly:

- Target type: `project-pattern`, `project-decision`, or `global-advisory`
- Suggested path or owner if the project already has a memory store
- Evidence refs from `brief.md`, `implementation-notes.md`, `run-ledger.md`, or `review-report.md`
- Privacy check confirming no user-private context or session chatter is being retained

The recommendation must point back to evidence and wait for explicit operator/project process before any memory write. No evidence, no memory.

## Relationship to evolution

Long-run may record evolution rule candidates in `eval-record.md` when a high/epic retrospective exposes a recurring workflow pattern. It does **not** write `.forgeflow/evolution/proposed/` files directly.

Evolution rule materialization is handled by the **ship** stage. Ship runs in all routes (small, medium, high, epic), reads `eval-record.md` as one input, and decides whether to turn candidate notes into proposed rule artifacts.

## Procedure

1. Review the task's `brief.md`, review reports, and any decision artifacts.
2. Extract only patterns/failures that are reusable outside this task.
3. For each candidate, verify it has concrete evidence (command output, test result, code diff, decision reference).
4. Write `eval-record.md` following `templates/eval-record.md` format.
5. If patterns warrant memory writes, note them in the Recommendations section with target paths.
6. Report what was captured and why it matters for future work.

## Anti-patterns

| Anti-Pattern | Why It Fails |
|---|---|
| Capturing task status | Belongs in task artifacts, not long-run memory |
| Capturing vibes without evidence | No actionable signal; wastes future context |
| Capturing everything | Noise drowns signal; becomes useless |
| Skipping this after high/epic work | Reusable lessons are lost; same mistakes recur |
| Auto-committing to memory without review | Unvalidated patterns pollute the knowledge base |

## Constraints

- No evidence, no rule — every pattern must reference concrete evidence from task artifacts.
- Do not store session chatter, one-off progress, or user-private context.
- Evolution rule materialization belongs in ship; long-run may only record candidate notes in `eval-record.md`.

## Exit Condition

- `eval-record.md` is written to the active task directory with at least one evidence-backed entry, **or**
- `eval-record.md` records that no durable lesson should be retained and explains why.

Either way, the decision is explicit. No ghost memory. No vibes ledger.
