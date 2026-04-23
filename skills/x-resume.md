# Skill: x-resume

## Purpose

Resume an interrupted session from the last valid checkpoint. Never restart from zero.

## Trigger

- Session crashed, was cancelled, or timed out.
- User says: `"resume"`, `"continue from last checkpoint"`.
- `run` or `review` failed and needs recovery without losing progress.

## Input

| Artifact | Source |
|----------|--------|
| `checkpoint.json` | Last saved checkpoint |
| `run-state.json` | Current execution state |
| `session-state.json` | Full session context |
| `plan-ledger.json` | Plan vs runtime truth |

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| Restored workspace | Files and state rolled forward to checkpoint |
| `decision-log.json` | Entry: resume event, recovered state |

## Execution

1. Load `checkpoint.json` to determine last valid state.
2. Load `plan-ledger.json` to see which tasks were completed, failed, or in-progress.
3. Reconstruct the context: re-read `brief.json`, `requirements.md`, `plan.json`.
4. Replay completed tasks from ledger (do not re-execute unless output is missing).
5. Identify the first incomplete task.
6. Resume execution from that task.
7. Log the resume event in `decision-log.json`.

## Constraints

- Do not re-execute tasks whose outputs already exist and are valid.
- If checkpoint is corrupted, fall back to the previous checkpoint.
- If no checkpoint exists, this skill cannot run. Escalate to user.

## Exit Condition

- Workspace state matches `checkpoint.json` + replayed completed tasks.
- Next task is identified and ready for execution.

## Notes

- This implements `harness-v1-principles.md` #6 and #8.
- Checkpoints should be written automatically by the orchestrator after every task completion.
