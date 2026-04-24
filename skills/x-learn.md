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
| `review-report.json` | Review findings |
| Source files | Final codebase state |

## Output Artifacts

| Artifact | Schema | Description |
|----------|--------|-------------|
| `memory/learnings.json` | JSON lines | Typed knowledge entries with BM25 indexing. |

## Execution

1. **Extract learnings.** For each significant event (bug, workaround, convention discovery, failed approach), create an entry:
   ```json
   {
     "timestamp": "2026-04-23T09:55:00Z",
     "task_id": "task-001",
     "type": "bug|workaround|convention|failure|success",
     "problem": "What went wrong or what was hard?",
     "cause": "Root cause or reason.",
     "rule": "What to do next time.",
     "tags": ["react", "testing", "performance"]
   }
   ```
2. **Append to `memory/learnings.json`.**
3. **Index.** If `memory/index/` exists, update the BM25 index.

## Constraints

- Every learning must have a `rule`. If you can't formulate a rule, it's not a learning yet.
- Tags must be from a controlled vocabulary or domain-specific. No generic tags like "code" or "fix".
- Past learnings are surfaced automatically during `clarify` and `specify` via BM25 search on the current goal.

## Exit Condition

- `learnings.json` has a new entry with timestamp and category.

## Notes

- This is hoyeon's learning/memory layer extracted into a cross-cutting skill.
- `learnings.json` is the closest thing forgeflow has to long-term memory.
