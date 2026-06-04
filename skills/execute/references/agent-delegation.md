# Agent Delegation for Specialist Work

> Reference for controller-led delegation in execute. Extracted from execute SKILL.md.

This is **controller-led delegation**: the execute controller decides which steps to delegate and handles result verification. This is distinct from `--subagent-per-task` mode (see `references/subagent-loop.md`), where every plan step runs through implementer → micro-review subagents automatically.

When `brief.md` includes required specialists and the task scope justifies delegation, use the Agent tool to spawn specialist sub-agents for independent plan steps. This prevents context exhaustion and enables parallel execution.

Base prompt: `references/implementer-prompt.md` (paste **full plan step text**, file allow/deny lists, task directory).

## When to delegate

Delegate to a sub-agent when ALL of these conditions are met:
1. Brief lists a relevant specialist (e.g., `frontend-execute`, `backend-execute`) **or** route is high/epic with fan-out/fan-in in plan Architecture Notes
2. The plan step has no unresolved dependencies on other in-progress steps
3. The step involves isolated file changes that won't conflict with parallel work
4. The main context is getting large enough that delegating preserves quality

Do NOT delegate when:
- The step modifies shared files that other steps also touch
- The step is step-1 (environment setup) or the final verification step
- The task is `small` route (overhead exceeds benefit)

## How to delegate

Use the Agent tool with `references/implementer-prompt.md`. Required prompt fields:

- Full plan step text (objective, files, acceptance criteria, verification)
- `Files you MAY change` / `Files you MUST NOT change`
- Task directory `<task-dir>`
- Report format: `DONE` | `DONE_WITH_CONCERNS` | `NEEDS_CONTEXT` | `BLOCKED`

**Red flags (never):**
- Tell subagent to read `plan.md` instead of pasting step text
- Mark step `done` when agent reports DONE without `git diff --stat` + verification
- Skip micro-gates on high/epic after delegated work
- Dispatch parallel implementers for steps that touch the same file

## Agent result handling

After the agent returns:
1. Verify the claimed changes exist (`git diff --stat`)
2. Run verification commands to confirm the agent's evidence
3. Set ledger **Assignee** to `specialist` while verifying; then apply **Per-task micro-gates**
4. Update `implementation-notes.md` with verified result — agent self-report alone is not evidence

Handle worker status:
- **NEEDS_CONTEXT** — provide missing context; re-dispatch or complete as controller
- **BLOCKED** — mark ledger `blocked`; do not mark step `done`
- **DONE_WITH_CONCERNS** — record concerns; run micro-gates before `done`

## Parallel delegation

For steps with no mutual dependencies (check plan.md dependencies):
- Spawn multiple agents in a single message with parallel Agent tool calls
- Each agent must receive its exact file scope to prevent conflicts
- After ALL agents return, run cross-document consistency checks
- Mark steps completed only after verification + micro-gates (high/epic), not when agents report done
