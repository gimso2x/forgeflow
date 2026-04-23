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

1. Scan changed files for smells.
2. Fix one smell category at a time.
3. Run tests after each category.
4. If tests break, revert and skip that category.
5. Write a summary to `decision-log.json`.

## Constraints

- Do not change behavior. Only structure and style.
- If a smell is debatable, leave it and note it in the review.

## Exit Condition

- No TODO orphans, no dead imports, no hallucinated APIs remain.
- OR decision-log documents items flagged for human review.

## Notes

- This is engineering-discipline's cleanup policy extracted into a cross-cutting skill.
- Run after `run` and before `review`.
