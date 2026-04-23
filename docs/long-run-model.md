# Long-run model

`long-run` is not a victory lap and it is not a memory dump. It is the narrow stage that decides whether this run produced learning worth carrying forward.

## Purpose

Use `long-run` to preserve durable signal from high-risk or repeatedly useful work:

- reusable workflow patterns
- durable failure modes
- evaluation outcomes
- recovery lessons
- project-level operating decisions

Do not use it for:

- chat summaries
- one-off task progress
- raw logs
- vague “remember this” notes
- worker self-congratulation, the most useless artifact genre yet invented

## Entry condition

`long-run` only appears on the `large_high_risk` route:

```text
clarify -> plan -> execute -> spec-review -> quality-review -> finalize -> long-run
```

The stage requires:

- finalized `run-state`
- approved review evidence
- `eval-record` satisfying `worth_long_run_capture`

If the run has no reusable lesson, the right output is an `eval-record` explaining “do not retain.” Silence is worse: future agents will hallucinate value into the gap.

## Capture decision

A long-run capture is worth keeping only if at least one is true:

1. It changes how future similar tasks should be planned or reviewed.
2. It identifies a failure mode that can be tested or guarded.
3. It records a recovery pattern that reduces future risk.
4. It documents an evaluation result that affects route, gate, or adapter behavior.
5. It creates a project-level decision that should survive beyond the session.

Everything else is noise.

## Output artifact

The canonical output is `eval-record.json`.

Minimum expected content:

- `task_id`
- what was evaluated
- evidence references
- outcome/verdict
- reusable lesson or explicit non-retention rationale
- recommended follow-up, if any

The artifact must be reviewable without chat history. If a future maintainer cannot tell why it exists, it should not exist.

## Relationship to memory

ForgeFlow memory is inspectable local storage, not hidden model memory.

- `memory/patterns/` stores reusable workflow patterns.
- `memory/decisions/` stores durable project-level operating decisions.
- `eval-record.json` is the gate artifact that justifies whether anything should move there.

The long-run stage may recommend a memory write, but the recommendation must point back to evidence. No evidence, no memory. Brutal, but clean.

## Relationship to review

`spec-review` asks: did we build the right thing?

`quality-review` asks: is the result safe, maintainable, and verified?

`long-run` asks: did this run teach us something worth preserving?

Those are three different questions. Merging them creates mush.

## Anti-patterns

### Capturing task status

Bad:

> “Feature X was completed.”

That belongs in run artifacts, not long-run memory.

### Capturing vibes

Bad:

> “The approach worked well.”

If there is no evidence and no reusable rule, it is just a scented candle.

### Capturing everything

Bad:

> Copy the whole transcript into memory.

This poisons future context. Long-run should compress signal, not archive noise.

## Exit condition

`long-run` is complete when one of these is true:

1. `eval-record.json` records a specific reusable lesson and points to evidence.
2. `eval-record.json` records that no durable lesson should be retained and explains why.

Either way, the decision is explicit. No ghost memory. No vibes ledger.
