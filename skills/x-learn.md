---
name: x-learn
description: x-learn cross-cutting ForgeFlow skill
validate_prompt: |
  Must capture durable, reusable learnings rather than temporary task progress.
  Must include source evidence and avoid duplicate or low-value lessons.
  Must not store secrets, raw dumps, or session-only TODO state as learnings.
---

# Skill: x-learn

## Purpose

Capture typed learnings from every execution so that future sessions compound knowledge instead of starting from zero.

## Trigger

- After `ship`, or after any significant blocker/resolution.
- User says: `"remember this"`, `"learn from this"`.

## Input

| Artifact | Source |
|----------|--------|
| `decision-log.json` | Session decisions and outcomes |
| `review-report.json` | Review findings with problem/cause/recommendation/evidence |
| `eval-record.json` | Verification and long-run capture evidence |
| PR comments/reviews | Optional external review feedback when provided |
| Source files | Final codebase state for evidence anchors only |

## Output Artifacts

| Artifact | Schema | Description |
|----------|--------|-------------|
| `memory/learnings.jsonl` | JSON lines | Typed knowledge entries with duplicate-safe stable IDs. |

## JSONL Entry Shape

```json
{
  "id": "learn-<sha16>",
  "timestamp": "2026-04-24T09:55:00Z",
  "source": {"task_id": "task-001", "artifact": "review-report.json"},
  "type": "review-finding|decision|issue|verification",
  "problem": "What went wrong or what was hard?",
  "cause": "Root cause or reason.",
  "rule": "What to do next time.",
  "evidence": ["file.py:42"],
  "tags": ["testing", "schema"]
}
```

## Execution

1. **Collect evidence.** Read decision, review, eval, and optional PR/comment artifacts. Do not scrape raw chat logs.
2. **Extract durable lessons only.** A lesson must have `problem`, `cause`, `rule`, and concrete `evidence`.
3. **Classify.** Use the narrowest useful type:
   - `review-finding`: reviewer found a reusable implementation risk
   - `decision`: a tradeoff choice should guide similar future work
   - `issue`: an encountered failure has a known prevention rule
   - `verification`: a verification pattern is worth repeating
4. **Filter junk.** Reject temporary progress, raw dumps, secrets, credentials, and vague rules.
5. **De-duplicate.** Stable ID is derived from `type|problem|cause|rule|evidence`; existing IDs are skipped.
6. **Append JSONL.** Use:
   ```bash
   python3 scripts/forgeflow_learn.py extract <task_dir> --output memory/learnings.jsonl
   python3 scripts/forgeflow_learn.py validate memory/learnings.jsonl
   ```
7. **Index.** If `memory/index/` exists, update the BM25 index.

## Constraints

- Every learning must have a future-facing `rule`. If you can't formulate a rule, it's not a learning yet.
- Every learning must include evidence anchors; unsupported advice is just vibes in a trench coat.
- Tags must be specific enough to retrieve later. Avoid generic tags like "code" or "fix".
- Do not store secrets, raw tool output, copied stack traces, or session-only TODO progress.
- Past learnings are surfaced during `clarify` and `specify` via search on the current goal.

## Exit Condition

- `memory/learnings.jsonl` has zero or more new de-duplicated entries.
- `forgeflow_learn.py validate` passes for the target JSONL file.

## Notes

- This is hoyeon's learning/memory layer extracted into a cross-cutting skill.
- `learnings.jsonl` is the closest thing forgeflow has to long-term memory.
