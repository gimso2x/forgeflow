---
name: x-debug
description: x-debug cross-cutting ForgeFlow skill
validate_prompt: |
  Must reproduce the issue and trace root cause before proposing a fix.
  Must not patch symptom sites until the original trigger is traced or explicitly ruled out.
  Must report evidence, scope, fix, risk, and verification.
---

# Skill: x-debug

## Purpose

Fix a bug using reproduce-first, 4-phase root cause analysis. Never guess.

## Trigger

- A test fails, a user reports a bug, or unexpected behavior appears.
- User says: `"debug this"`, `"why is this broken?"`.

## Input

| Artifact | Source |
|----------|--------|
| `plan.json` | Current task contract |
| `run-state.json` | Failure details |
| Source files | Relevant codebase |

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| Fixed source files | Root cause fix |
| Regression test | Test that fails before fix, passes after |
| `decision-log.json` | Entry: bug description, root cause, fix summary |

## Execution

1. **REPRODUCE:** Create the smallest possible reproduction.
   - If you can't reproduce it, you can't fix it.
2. **TRACE SOURCE:** Walk backward from the observed symptom to the original trigger.
   - Inspect the immediate failing operation, then each caller and input source.
   - Use stack trace instrumentation when the call chain is hidden.
   - Use test bisection with `docs/debugging/find-polluter.sh` when state pollution appears only during a suite.
   - Stop only when the source is identified or explicitly ruled out in `decision-log.json`.
3. **HYPOTHESIZE:** List all possible causes. Order by likelihood.
4. **ISOLATE:** Test each hypothesis with the smallest possible experiment.
   - Change one thing at a time.
   - Use logging, breakpoints, or binary search through code history.
5. **VERIFY:** Apply the fix and confirm the reproduction now passes.
   - Run the full test suite to check for regressions.
6. **PREVENT:** Add a regression test that fails before the fix and passes after.
7. **DOCUMENT:** Write a decision entry in `decision-log.json` with root cause, fix, and regression test location.

## Constraints

- No fixes without reproduction.
- No fixes at the symptom site until the original trigger has been traced or explicitly ruled out.
- No multi-line changes in the isolate phase.
- If the root cause is outside the codebase (dependency, environment), document it and escalate.

## Reference Playbooks

Use these when the failure mode matches. They are debugging references, not artifact contracts.

- `docs/debugging/root-cause-tracing.md` — trace backward from symptom to original trigger.
- `docs/debugging/condition-based-waiting.md` — replace blind sleeps with observable readiness checks.
- `docs/debugging/condition-based-waiting-example.ts` — concrete TypeScript example for condition waits.
- `docs/debugging/defense-in-depth.md` — layer checks so one missed assumption does not become a silent failure.
- `docs/debugging/find-polluter.sh` — isolate test pollution by running candidate tests one by one.

## Exit Condition

- Bug is reproduced, root cause identified, fix verified, regression test passes.
- OR decision-log documents why reproduction failed.

## Notes

- This is engineering-discipline's bug-fix policy extracted into a cross-cutting skill.
- Always pair with `x-learn` to capture the bug pattern.
