# ForgeFlow Skills

Skills are markdown documents that live in `skills/`. Each skill defines a bounded operation with explicit inputs, outputs, and trigger conditions.

## Design rules

1. **One skill = one bounded operation.** No skill tries to do everything.
2. **Every skill declares its output artifacts.** If it doesn't write to disk, it's not a skill.
3. **Skills chain; they don't fork.** The output of skill N is the required input of skill N+1.
4. **Trigger phrases are advisory, not magical.** The operator or an adapter decides when to invoke a skill.
5. **Keep the active skill surface minimal.** Optional discipline, debugging, QA, and learning guidance belongs in docs, prompts, runtime policy, or tests unless it is a first-class plugin skill.

## Workflow skills (ordered)

| # | Skill | Purpose | Borrowed from |
|---|-------|---------|---------------|
| 00 | [`forgeflow`](forgeflow/SKILL.md) | Overview router for slash-style ForgeFlow prompts. | ForgeFlow |
| 01 | [`init`](init/SKILL.md) | Bootstrap a task workspace without auto-chaining. | ForgeFlow runtime |
| 02 | [`clarify`](clarify/SKILL.md) | Resolve ambiguity, explore codebase, emit a **Context Brief** with complexity routing. | engineering-discipline + andrej-karpathy-skills |
| 03 | [`plan`](plan/SKILL.md) | Turn requirements into an executable **plan.json** with task contracts. | hoyeon + engineering-discipline + andrej-karpathy-skills |
| 04 | [`execute`](execute/SKILL.md) | Execute plan tasks using **worker-validator pairs** with checkpoint/recovery. | engineering-discipline + andrej-karpathy-skills |
| 05 | [`review`](review/SKILL.md) | **Information-isolated** verification of executed work against the plan. | engineering-discipline + andrej-karpathy-skills |
| 06 | [`ship`](ship/SKILL.md) | Final handoff/report after verification; branch disposition lives in [`finish`](finish/SKILL.md). | gstack |
| 07 | [`finish`](finish/SKILL.md) | Close the task and handle branch/worktree disposition. | ForgeFlow |
| 08 | [`milestone`](milestone/SKILL.md) | Create and manage project milestones. | GSD |

## Removed optional skills

The active plugin/runtime surface intentionally excludes optional `specify`, `verify`, and `x-*` skills. Their useful ideas are absorbed into the core workflow skills, prompts, docs, runtime policy, and tests instead of remaining as separate user-facing skills.

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
  → milestone        → roadmap.json (M1: Auth, M2: Cart, M3: Checkout)
  → (per milestone)
    → plan           → plan.json
    → execute        → run-state.json
    → review (spec)  → review-report-spec.json
    → review (qual)  → review-report-quality.json
  → ship             → final handoff
  → finish           → branch disposition
```

## Adding a new skill

1. Pick a bounded skill name that matches a first-class plugin operation.
2. Copy the template from [`_template.md`](_template.md).
3. Create the active contract at `skills/<name>/SKILL.md`.
4. Historical imports belong under `docs/legacy/skills/`, not beside active plugin contracts.
5. Fill in Purpose, Trigger, Input, Output, Execution, Constraints, Exit Condition.
6. Add a row to the table above only if the skill is part of the active surface.
7. Run `make validate`.
