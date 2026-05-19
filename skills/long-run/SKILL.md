---
name: long-run
description: Record reusable learnings after high or epic route completion. Produces eval-record.md with evidence-backed reusable patterns, failure rules, and improvement suggestions. High/epic route only unless manually invoked. Use when the user types /long-run or /forgeflow:long-run.
version: 0.3.0
author: gimso2x
validate_prompt: |
  Must preserve only learning that can improve future tasks.
  Must not store session chatter, one-off progress, or user-private context.
  Must produce eval-record.md following templates/eval-record.md format only when reusable patterns or failure rules are identified.
  Must point every pattern or rule back to evidence -- no evidence, no memory.
---

# Long-run

Capture durable signal from high or epic route work. This is not a summary tool -- it is a memory gate that decides what is worth preserving for future tasks.

## When to run

- Automatically after high or epic route finalize completes.
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

## Relationship to evolution

ForgeFlow supports an evolution pipeline that turns observed patterns into enforceable workflow rules. Evolution rules are stored as Markdown files in `.forgeflow/evolution/`.

### Rule lifecycle

```
observe → propose → validate → activate → retire
```

1. **Observe**: During long-run, a reusable pattern or failure rule is identified with concrete evidence.
2. **Propose**: Write each rule candidate using `templates/evolution-rule.md` to `.forgeflow/evolution/proposed/<rule-name>.md` with trigger, application stage, expected behavior, enforcement mode, false-positive guard, and evidence reference from `eval-record.md`.
3. **Validate**: The rule candidate must be reviewed through a normal review cycle. Do not auto-commit rules.
4. **Activate**: Move validated project rules to `.forgeflow/evolution/active/`. Future clarify/plan/execute stages load active project rules automatically. Global rules remain advisory and require explicit user approval before writing outside the repository.
5. **Retire**: When a rule no longer applies or causes friction, move it to `.forgeflow/evolution/retired/` with a retirement reason.

### Scope boundary

- **Project scope**: Rules that apply to the current repository. Stored in the repo's `.forgeflow/evolution/`.
- **Global scope**: Rules that apply across projects. Stored in the user's global ForgeFlow config. Requires explicit user approval to promote.

### Capture criteria for rule candidates

A pattern or failure rule is a valid evolution candidate only when:

1. It has concrete evidence from `eval-record.md` (command output, test result, code diff, or decision reference).
2. It describes a trigger condition and expected behavior, not just a vague sentiment.
3. It is not already covered by an active rule.
4. It is not project-specific trivia disguised as a general rule.
5. It defines whether the scope is `project` or `global-advisory`; global candidates must not become hard enforcement rules.

### Anti-patterns

| Anti-Pattern | Why It Fails |
|---|---|
| Auto-committing rules without review | Unvalidated rules become technical debt |
| Proposing rules without evidence | Rules without grounding become cargo cult |
| Retiring rules silently | Lost history makes the same mistake recur |

## Procedure

1. Review the task's `brief.md`, review reports, and any decision artifacts.
2. Extract only patterns/failures that are reusable outside this task.
3. For each candidate, verify it has concrete evidence (command output, test result, code diff, decision reference).
4. Write `eval-record.md` following `templates/eval-record.md` format, including `Evolution Rule Candidates` when a rule is warranted.
5. For each warranted rule candidate, create or update `.forgeflow/evolution/proposed/<rule-name>.md` from `templates/evolution-rule.md`; create the proposed directory first if it is missing.
6. If a candidate is suggested for global reuse, keep `Scope: global-advisory` and `Enforcement Mode: advisory`; do not write outside the repository unless the user explicitly approves it.
7. If patterns warrant memory writes, note them in the Recommendations section with target paths.
8. Report what was captured and why it matters for future work.

## Anti-patterns

| Anti-Pattern | Why It Fails |
|---|---|
| Capturing task status | Belongs in task artifacts, not long-run memory |
| Capturing vibes without evidence | No actionable signal; wastes future context |
| Capturing everything | Noise drowns signal; becomes useless |
| Skipping this after high/epic work | Reusable lessons are lost; same mistakes recur |
| Auto-committing to memory without review | Unvalidated patterns pollute the knowledge base |

## Exit Condition

- `eval-record.md` is written to the active task directory with at least one evidence-backed entry, **or**
- `eval-record.md` records that no durable lesson should be retained and explains why.

Either way, the decision is explicit. No ghost memory. No vibes ledger.
