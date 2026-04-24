---
name: x-deslop
description: x-deslop cross-cutting ForgeFlow skill
validate_prompt: |
  Must review only changed files unless the user explicitly expands scope.
  Must remove LLM-specific slop without changing intended behavior.
  Must preserve tests and verification evidence for any cleanup edit.
---

# Skill: x-deslop

## Purpose

Remove LLM-specific code smells. Corrective cleanup after any significant generation session.

## Trigger

- After `run` completes.
- User says: `"clean up"`, `"deslop"`, `"slop"`, or any request to improve generated code quality.

## Input

| Artifact | Source |
|----------|--------|
| Source files | Files modified during `run` |
| Test files | Current test suite |
| `requirements.md` | Expected behavior baseline |

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| Cleaned source files | Deslopped code |
| `decision-log.json` | Entry: cleanup items flagged or removed |

## Smell catalog

| Smell | Detection | Fix |
|-------|-----------|-----|
| Over-commenting | Comments restate the code | Delete obvious comments. Keep "why" comments. |
| Unnecessary abstractions | Single-use interfaces, wrappers | Inline if used once. Extract only if reused ≥3 times. |
| Defensive paranoia | Excessive null checks, try/catch | Flag checks that lack test coverage as removal candidates. Do not auto-remove. |
| Verbose naming | `getUserDataFromDatabaseRepository` | Shorten to domain-idiomatic names. |
| Filler | Unused imports, dead code, TODOs without tickets | Delete. |
| Premature generics | `T` used once | Replace with concrete type. |

## Execution

1. Identify the changed files first. Prefer `git diff`; if unavailable, use the run artifact's changed-file list.
2. Review only changed files. Do not clean unrelated code "while here".
3. Scan changed files through three lenses:
   - **Reuse:** replace duplicated helpers or reimplemented standard-library behavior with existing utilities.
   - **Quality:** remove unnecessary abstractions, parameter sprawl, leaky boundaries, magic strings, and obvious comments.
   - **Efficiency:** flag repeated work, missed independent concurrency, hot-path bloat, and unbounded resource growth without inventing premature optimization.
4. Fix one smell category at a time.
5. Run tests after each category.
6. If tests break, revert and skip that category.
7. Write a summary to `decision-log.json`.

## Constraints

- Do not change behavior. Only structure and style.
- If a smell is debatable, leave it and note it in the review.

## Exit Condition

- No TODO orphans, no dead imports, no hallucinated APIs remain.
- OR decision-log documents items flagged for human review.

## Notes

- This is engineering-discipline's cleanup policy extracted into a cross-cutting skill.
- Run after `run` and before `review`.
