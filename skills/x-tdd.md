# Skill: x-tdd

## Purpose

Enforce RED-GREEN-REFACTOR. Write a failing test first, watch it fail, write minimal code to pass, watch it pass, then refactor.

## Trigger

- Before implementing any feature or bugfix.
- User says: `"TDD"`, `"test first"`, or any task in `plan.json` with `verification` set to a test command.

## Input

| Artifact | Source |
|----------|--------|
| `plan.json` | Current task contract (may contain `tdd: true`) |
| Source files | Files to be modified |
| Existing test files | Current test suite |

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| Test files | New or updated tests |
| Source files | Minimal implementation changes |
| `decision-log.json` | Entry: TDD applied / skipped with reason |

## Execution

1. **RED:** Write the test for the desired behavior. Run it. It must fail.
   - If it passes, the test is wrong or the feature already exists. Stop and reassess.
2. **GREEN:** Write the minimal code to make the test pass.
   - Copy-paste from existing code is allowed.
   - Do not generalize yet. Hardcode if needed.
3. **REFACTOR:** Clean up duplication, improve names, optimize structure.
   - Tests must stay green throughout.
4. **Commit:** Commit with message prefixed by the task ID (e.g., `T1: add ThemeContext`).

## Constraints

- No production code without a failing test first.
- No refactoring without green tests.
- If you find yourself writing code before a test, revert to the last git staging area or checkpoint and start over.

## Exit Condition

- All new/modified code is covered by at least one test, OR decision-log documents why TDD was skipped.
- Test suite passes (green).

## Notes

- This is superpowers' `run_tests` mode extracted into a cross-cutting skill.
- Works best when paired with `x-deslop` to remove unreachable guards after test coverage is complete.
