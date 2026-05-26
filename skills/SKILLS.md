# ForgeFlow Skills

Skills are markdown documents that live in `skills/`. Each skill defines a bounded operation with explicit inputs, outputs, and trigger conditions.

## Design rules

1. **One skill = one bounded operation.** No skill tries to do everything.
2. **Every skill declares its output artifacts.** If it doesn't write to disk, it's not a skill.
3. **Skills chain; they don't fork.** The output of skill N is the required input of skill N+1.
4. **Trigger phrases are advisory, not magical.** The operator or an adapter decides when to invoke a skill.
5. **Keep the active skill surface minimal.** Optional discipline, debugging, QA, and learning guidance belongs in docs or prompts unless it is a first-class plugin skill.

## Workflow skills (ordered)

| # | Skill | Purpose |
|---|-------|---------|
| 00 | [`forgeflow`](forgeflow/SKILL.md) | Overview router for slash-style ForgeFlow prompts. |
| 01 | [`clarify`](clarify/SKILL.md) | Bootstrap task workspace, resolve ambiguity, explore codebase, emit a **brief.md** with complexity routing. |
| 02 | [`plan`](plan/SKILL.md) | Turn requirements into an executable **plan.md** with task contracts; includes epic decomposition for epic route. |
| 03 | [`execute`](execute/SKILL.md) | Execute plan tasks with checkpoint/recovery tracking; includes opt-in subagent per-task loop. |
|| 04 | [`review`](review/SKILL.md) | **Information-isolated** verification. Pipeline mode: verify executed work against the plan. Standalone mode: review external input (URL/repo/diff/files) independently with role-based review. |
| 05 | [`ship`](ship/SKILL.md) | Final handoff, evolution rule extraction, and branch disposition (merge/PR/keep/discard). |
| 06 | [`long-run`](long-run/SKILL.md) | Record reusable learnings after high/epic route completion. |
| 07 | [`benchmark`](benchmark/SKILL.md) | Cross-adapter benchmark: same prompt → multiple agents → comparison report. |

## Skill lifecycle in a single task

```
User: "I want to build a daily briefing app"
  → clarify          → task workspace + brief.md (route: medium)
  → plan             → plan.md
  → execute          → implementation-notes.md + code changes
  → review           → review-report.md
  → ship             → final handoff + branch disposition: merge, PR, keep, or discard
```

## Long-run lifecycle (complex tasks)

```
User: "Refactor the entire payment module"
  → clarify          → task workspace + brief.md (route: high)
  → plan             → plan.md with verification targets
  → execute          → implementation-notes.md
  → review (spec pass → quality pass) → review-report.md
  → ship             → final handoff + branch disposition
  → long-run         → eval-record.md
```

## Epic lifecycle (massive tasks)

```
User: "Build a complete e-commerce platform"
  → clarify          → task workspace + brief.md (route: epic)
  → plan             → roadmap.md (epic decomposition: M1: Auth, M2: Cart, M3: Checkout, M_final: Integration)
  → (per milestone)
    → plan           → plan.md
    → execute        → implementation-notes.md
    → review (spec pass → quality pass) → review-report.md
  → ship             → final handoff + branch disposition
  → long-run         → eval-record.md
```

## Standalone review lifecycle (no pipeline)

```
User: "/forgeflow:review https://github.com/org/repo/pull/42"
  → review (standalone)     → synthetic task dir + normalized-input.md + review-report.md
```

```
User: "/forgeflow:review --type security ./src/"
  → review (standalone)     → security-reviewer only → review-report.md
```

## Utility skills

| # | Skill | Purpose |
|---|-------|---------|
| U1 | [`config`](config/SKILL.md) | Manage ForgeFlow project defaults interactively. Toggle auto-chaining and worktree isolation. |

## Adding a new skill

1. Pick a bounded skill name that matches a first-class plugin operation.
2. Copy the template from [`_template.md`](_template.md).
3. Create the active contract at `skills/<name>/SKILL.md`.
4. Fill in Purpose, Trigger, Input, Output, Execution, Constraints, Exit Condition.
5. Add a row to the table above only if the skill is part of the active surface.
