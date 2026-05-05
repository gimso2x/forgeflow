---
description: Independent review of completed work — read-only verification with findings.
---

# /forgeflow:review

Review completed work independently. **Read-only — do not modify code.**

## Instructions

1. Read `brief.json`, `plan-ledger.json`, and `run-state.json` from the task directory.

2. Verify:
   - All plan tasks are completed (not just marked done)
   - Verification evidence is real (commands exist and output matches claims)
   - Changes match the stated objective and constraints
   - No regressions: lint, build, test still pass
   - No writes outside the target project

3. Run independent verification: execute lint/build/test commands yourself.

4. Write `review-report.json`:
   ```json
   {
     "schema_version": "0.1",
     "task_id": "<task-id>",
     "review_type": "quality",
     "verdict": "approved|changes_requested",
     "findings": [
       {
         "severity": "P0|P1|P2",
         "description": "...",
         "file": "...",
         "suggestion": "..."
       }
     ],
     "test_verification": {
       "ran": true,
       "passed": true,
       "pass_count": 1082,
       "fail_count": 0
     },
     "safe_for_next_stage": true,
     "reviewed_at": "<ISO 8601>"
   }
   ```

5. **Severity guide**:
   - P0: writes outside project, corrupts config, breaks build
   - P1: false commands, missing artifacts, unverified claims, **dead code, type-unsafe patterns, bare except**
   - P2: unclear wording, weak examples, minor formatting

6. **Code quality gates** (check as P1):
   - Dead code: unreachable branches, unused imports/variables/functions.
   - Type safety: mixed-type return lists (e.g. `gather(return_exceptions=True)` without narrowing), in-place type mutation.
   - Exception handling: bare `except:`, silently swallowed exceptions.
   - Trivial tests: tests verifying string equality instead of actual logic.
   - Global mutable state: module-level dicts, connections, singletons leaking state between tests.

7. If `changes_requested`: set `safe_for_next_stage: false` and list required fixes.
   The implementer must address findings and re-submit.

8. **Hard rule**: Do not use Write/Edit tools during review. Read, Grep, and Bash (verification only).

## Automation / non-interactive approval mode

If the user explicitly includes `--yes`, `--auto-approve`, `--non-interactive`, or says to continue through ForgeFlow stages without further approval, treat that as approval for the current bounded ForgeFlow sequence. Do not pause at the normal stage-boundary y/n prompt; proceed to the next requested ForgeFlow stage after writing the required artifact for the current stage. This only applies inside the stated task scope and never overrides a blocker, failed verification, missing required artifact, or unsafe/destructive action.
