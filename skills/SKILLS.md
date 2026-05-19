# ForgeFlow Skills

Skills are markdown documents that live in `skills/`. Each skill defines a bounded operation with explicit inputs, outputs, and trigger conditions.

## Design rules

1. **One skill = one bounded operation.** No skill tries to do everything.
2. **Every skill declares its output artifacts.** If it doesn't write to disk, it's not a skill.
3. **Skills chain; they don't fork.** The output of skill N is the required input of skill N+1.
4. **Status analysis is a runtime/reporting surface, not a workflow stage.** Read `run-state.json`, review reports, eval records, and `scripts/forgeflow_monitor.py` before deciding resume/fix/finish, but do not create a separate status skill.
5. **Trigger phrases are advisory, not magical.** The operator or an adapter decides when to invoke a skill.
6. **Keep the active skill surface minimal.** Optional discipline, debugging, QA, and learning guidance belongs in docs, prompts, runtime policy, or tests unless it is a first-class plugin skill.
7. **Harness concepts stay inside the existing workflow.** ForgeFlow handles Instructions/Tools/Environment/State/Feedback through stage artifacts and evidence; Do not create a separate harness stage or parallel source of truth.

## Workflow skills (ordered)

| # | Skill | Purpose | Borrowed from |
|---|-------|---------|---------------|
| 00 | [`forgeflow`](forgeflow/SKILL.md) | Overview router for slash-style ForgeFlow prompts. | ForgeFlow |
| 01 | [`forgeflow-init`](forgeflow-init/SKILL.md) | Bootstrap a task workspace without auto-chaining. | ForgeFlow runtime |
| 02 | [`clarify`](clarify/SKILL.md) | Resolve ambiguity, explore codebase, emit a **Context Brief** with complexity routing. | engineering-discipline + andrej-karpathy-skills |
| 03 | [`plan`](plan/SKILL.md) | Turn requirements into an executable **plan.json** with task contracts. | hoyeon + engineering-discipline + andrej-karpathy-skills |
| 04 | [`execute`](execute/SKILL.md) | Execute plan tasks using **worker-validator pairs** with checkpoint/recovery. | engineering-discipline + andrej-karpathy-skills |
| 05 | [`review`](review/SKILL.md) | **Information-isolated** verification of executed work against the plan. | engineering-discipline + andrej-karpathy-skills |
| 06 | [`ship`](ship/SKILL.md) | Final handoff/report after verification; branch disposition lives in [`finish`](finish/SKILL.md). | gstack |
| 07 | [`finish`](finish/SKILL.md) | Close the task and handle branch/worktree disposition. | ForgeFlow |
| 08 | [`milestone`](milestone/SKILL.md) | Create and manage project milestones with dependency DAG and integration verification. | GSD + Ultraplan |
| 09 | [`long-run`](long-run/SKILL.md) | Record reusable learnings after high-risk task completion. Produces eval-record.json. | ForgeFlow |

## Removed optional skills

The active plugin/runtime surface intentionally excludes optional `specify`, `verify`, and `x-*` skills. Their useful ideas are absorbed into the core workflow skills, prompts, docs, runtime policy, and tests instead of remaining as separate user-facing skills. Tool-specific root prompts should include the active workflow skills directly instead of keeping separate adapter-only discipline shims. Use `scripts/forgeflow_monitor.py` for read-only status analysis instead of adding a separate user-facing status skill.

## Skill lifecycle in a single task

```
User: "I want to build a daily briefing app"
  → init             → task workspace
  → clarify          → brief.json + complexity=medium
  → plan             → plan.json
  → execute          → decision-log.json + run-state.json + plan-ledger.json + code changes
  → review           → review-report.json
  → ship             → final handoff
  → finish           → branch disposition: merge, PR, keep, or discard
```

## Long-run lifecycle (complex tasks)

```
User: "Refactor the entire payment module"
  → init             → task workspace
  → clarify          → brief.json + complexity=high
  → plan             → plan.json with verify_plan targets
  → execute          → decision-log.json + run-state.json + plan-ledger.json
  → review (spec)    → review-report-spec.json
  → review (quality) → review-report-quality.json
  → ship             → final PR
  → finish           → branch disposition
```

## Epic lifecycle (massive tasks)

```
User: "Build a complete e-commerce platform"
  → init             → task workspace
  → clarify          → brief.json + complexity=epic
  → milestone        → roadmap.json (M1: Auth, M2: Cart, M3: Checkout, M_final: Integration)
  → (per milestone)
    → plan           → plan.json
    → execute        (updates run-state.json)
    → review (spec)  → review-report-spec.json
    → review (qual)  → review-report-quality.json
  → ship             → final handoff
  → finish           → branch disposition
  → long-run         → eval-record.json (reusable patterns, failure rules)
```

## Adding a new skill

1. Pick a bounded skill name that matches a first-class plugin operation.
2. Copy the template from [`_template.md`](_template.md).
3. Create the active contract at `skills/<name>/SKILL.md`.
4. Historical imports belong under `docs/legacy/skills/`, not beside active plugin contracts.
5. Fill in Purpose, Trigger, Input, Output, Execution, Constraints, Exit Condition.
6. Add a row to the table above only if the skill is part of the active surface.
7. Run `make validate`.
