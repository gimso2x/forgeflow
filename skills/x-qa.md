---
name: x-qa
description: x-qa cross-cutting ForgeFlow skill
validate_prompt: |
  Must select an appropriate QA mode and scope before testing.
  Must capture issues with reproducible evidence and severity.
  Must distinguish report-only findings from fixes and never claim unrun verification.
---

# Skill: x-qa

## Purpose

Run functional QA in a real browser (or equivalent runtime). Find bugs that unit tests miss. Generate regression tests for found bugs.

## Trigger

- After `run` completes, before or during `review`.
- User says: `"qa this"`, `"test the UI"`, or provides a URL.

## Input

| Artifact | Source |
|----------|--------|
| `requirements.md` | Feature paths to exercise |
| `plan.json` | Current task contract |
| Built application | Local server / runtime URL |

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| `qa-report.json` | Bugs found with reproduction steps, severity |
| Test files | Regression tests for confirmed bugs |
| `decision-log.json` | Entry: QA performed / skipped with reason |

## Execution

1. **Identify entry points.** URLs, CLI commands, or API endpoints to exercise.
2. **Explore happy paths.** Can you complete the primary user journey?
3. **Explore edge cases.** Invalid inputs, empty states, network failures, rapid clicks.
4. **Document findings.** Screenshot or log for each issue.
5. **For each bug found:**
   - Write a minimal reproduction.
   - Generate a regression test that fails before the fix and passes after.
   - Fix the bug.
   - Verify the regression test passes.
6. **Append findings to `review-report.json` or write `qa-report.json`.**

## Constraints

- QA is not a replacement for unit tests. It finds different bugs.
- Every found bug must leave behind a regression test.
- Do not hand-wave. If you can't access a browser, say so and skip this skill.

## Exit Condition

- `qa-report.json` exists (may be empty with "QA clean"), OR decision-log documents skip reason.

## Notes

- This is gstack's `/qa` command extracted into a cross-cutting skill.
- QA findings feed back into `requirements.md` as edge cases for the next iteration.
