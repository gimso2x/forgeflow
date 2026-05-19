---
name: long-run
description: Record reusable learnings after high-risk task completion. Produces eval-record.md with evidence-backed reusable patterns, failure rules, and improvement suggestions. High-risk route only unless manually invoked. Use when the user types /forgeflow:long-run.
version: 0.3.0
author: gimso2x
validate_prompt: |
  Must preserve only learning that can improve future tasks.
  Must not store session chatter, one-off progress, or user-private context.
  Must produce eval-record.md following templates/eval-record.md format only when reusable patterns or failure rules are identified.
  Must point every pattern or rule back to evidence -- no evidence, no memory.
---

# Long-run

Capture durable signal from high-risk or repeatedly useful work. This is not a summary tool -- it is a memory gate that decides what is worth preserving for future tasks.

## When to run

- Automatically after high-risk route finalize completes.
- Manually via `/forgeflow:long-run` when reusable implementation patterns, verification patterns, or durable failure rules were identified.
- Do **not** require this for small or medium routes unless patterns are genuinely reusable.

## Capture decision

Before writing anything, answer: **Is this reusable outside the current task?**

Only capture:

- **Reusable workflow patterns**: approaches that worked and can be repeated (e.g., "generated output validation should compare target schema against actual sections")
- **Durable failure modes**: root causes that will recur (e.g., "marker-only validation has low reliability")
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

## Output

Write `.forgeflow/tasks/<task-id>/eval-record.md` following the format in `templates/eval-record.md`:

- **Outcome**: success | partial | failed
- **What Worked**: specific patterns with evidence references
- **What Failed**: specific failure modes with root causes
- **Reusable Patterns**: patterns worth reusing in future tasks
- **Failure Rules**: anti-patterns or mistakes to avoid
- **Recommendations**: for future tasks of similar nature

Every entry must be specific enough that a future agent can act on it without additional context.

## Relationship to memory

ForgeFlow memory is inspectable local storage:

- `memory/patterns/` stores reusable workflow patterns
- `memory/decisions/` stores durable project-level operating decisions
- `eval-record.md` is the gate artifact that justifies whether anything should move there

The long-run stage may recommend a memory write, but the recommendation must point back to evidence. No evidence, no memory.

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
| Skipping this after high-risk work | Reusable lessons are lost; same mistakes recur |
| Auto-committing to memory without review | Unvalidated patterns pollute the knowledge base |

## Exit condition

- `eval-record.md` is written to the active task directory with at least one evidence-backed entry, **or**
- `eval-record.md` records that no durable lesson should be retained and explains why.

Either way, the decision is explicit. No ghost memory. No vibes ledger.
