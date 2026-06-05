# Re-Execution Conditions

Use this reference from `skills/ff-review/SKILL.md` when review verdict is `changes_requested` or `blocked`.

## Procedure on FAIL verdict

1. Write `review-report.md` with findings and verdict as normal.
2. Update `checkpoint.md` Re-Execution Conditions section:
   - **Failure Analysis**: each major/blocker finding with root cause and required fix.
   - **Corrected Execution Conditions**: constraints, scope, or verification gates that must change.
   - **Rollback Instructions**: files to revert (`git restore <paths>` or `git stash`).
   - **Loop Counter**: current iteration number, incremented from ledger or starting at 1.
3. Record reusable root-cause patterns in Memory Bank:

   ```bash
   python3 scripts/forgeflow_fact_store.py add --content "<root cause pattern>" --type bug_fix --domain <domain> --source-task <task-id>
   ```

4. In auto mode, directly invoke `/forgeflow:execute` with the re-execution conditions.
5. In manual mode, present the conditions and ask: `re-execution conditions 생성됨. 다시 /forgeflow:execute을 진행하시겠습니까? (y/n)`.

## Loop safety

- Maximum 3 re-execution cycles per task.
- If loop counter reaches 3, set verdict to `blocked` and stop for user escalation.
- Each cycle must reduce the finding count. If findings do not decrease, recommend re-planning instead of re-executing.
