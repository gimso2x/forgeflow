# Developer Handoff Template

Use this template when ForgeFlow output must be handed to a human developer or another AI coding agent. Keep it concise and executable.

```markdown
# <Task title> — Developer Handoff

## Background
- Why this task exists.
- Links or artifact refs that define the current state.

## Goal
- The concrete outcome to produce.

## In scope
- Files, modules, commands, and behavior that may change.

## Out of scope
- Explicit non-goals and things not to refactor.

## Acceptance criteria
- [ ] Observable behavior or artifact that proves completion.
- [ ] Required tests/validators pass.
- [ ] Review evidence is recorded.

## File locations
- `.forgeflow/tasks/<task-id>/brief.json`
- `.forgeflow/tasks/<task-id>/plan-ledger.json`
- `<repo path(s) to edit>`

## Execution order
1. Read `brief.json`, `plan-ledger.json`, and any linked review/evidence artifacts.
2. Confirm the assigned `plan-ledger.tasks[].files` boundary.
3. Implement only the assigned scope.
4. Run the listed verification commands.
5. Update run-state/evidence refs or write a final handoff note.

## Verification
```bash
<commands to run>
```

## Handoff summary
- Changed files:
- Verification result:
- Remaining risks:
- Recommended next stage: `/forgeflow:review` or `/forgeflow:ship`
```

## Rules

- Do not depend on hidden chat history; every claim should point to an artifact, file path, command output, or review report.
- If a required artifact is missing, stop and request/produce it before implementation.
- If the task boundary conflicts with another active worker, mark the task blocked instead of editing shared files.
