# Skill: ship

## Purpose

Finalize the branch: run tests, audit coverage, present options, and hand off results. This is gstack's `/ship` adapted to ForgeFlow's artifact chain.

## Trigger

- After `review` produces an `approved` or `approved_with_minor` verdict.
- User says: `"ship it"`, `"merge"`, `"I'm done"`.

## Input

- `review-report.json`
- `run-state.json`
- `plan.json`
- Codebase

## Output Artifacts

| Artifact | Schema | Description |
|----------|--------|-------------|
| `ship-manifest.json` | `schemas/ship-manifest.schema.json` | Summary of changes, test results, coverage, and handoff decision. |

## Execution

1. **Run full test suite.** If any test fails, stop and recommend returning to `run`.
2. **Run coverage audit.** If coverage dropped, flag it in the manifest.
3. **Summarize changes.** List files modified, added, deleted. Reference plan tasks.
4. **Present handoff options:**
   - **merge:** Fast-forward merge to main (if clean).
   - **pr:** Open a pull request with auto-generated description.
   - **keep:** Leave the branch as-is for manual handling.
   - **discard:** Revert all changes (requires explicit confirmation).
5. **If merge or pr:**
   - Generate PR description from `plan.json` and `review-report.json`.
   - Include: goal, changes, test strategy, review verdict, risks.
6. **Clean up:**
   - Remove temporary artifacts if configured.
   - Archive `decision-log.json` to `memory/decisions/`.
7. **Write `ship-manifest.json`.**

## Constraints

- Do not merge without an `approved` review verdict.
- `approved_with_minor` can merge but must list minor findings in the manifest.
- Never discard without explicit user confirmation.
- Preserve `brief.json`, `requirements.md`, `plan.json`, `review-report.json` in the repo for auditability.
