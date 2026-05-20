# ForgeFlow Skills

Skills are markdown documents that live in `skills/`. Each skill defines a bounded operation with explicit inputs, outputs, and trigger conditions.

## Design rules

1. **One skill = one bounded operation.** No skill tries to do everything.
2. **Every skill declares its output artifacts.** If it doesn't write to disk, it's not a skill.
3. **Skills chain; they don't fork.** The output of skill N is the required input of skill N+1.
4. **Trigger phrases are advisory, not magical.** The operator or an adapter decides when to invoke a skill.
5. **Keep the active skill surface minimal.** Optional discipline, debugging, QA, and learning guidance belongs in docs or prompts unless it is a first-class plugin skill. `subagent-execute` is opt-in and does not replace default `execute`.

## Workflow skills (ordered)

Table numbers reflect skill index, not strict runtime order. For epic work, run `milestone` before `plan`.

| # | Skill | Purpose |
|---|-------|---------|
| 00 | [`forgeflow`](forgeflow/SKILL.md) | Overview router for slash-style ForgeFlow prompts. |
| 01 | [`forgeflow-init`](forgeflow-init/SKILL.md) | Bootstrap a task workspace. |
| 02 | [`clarify`](clarify/SKILL.md) | Resolve ambiguity, explore codebase, emit a **brief.md** with complexity routing. |
| 03 | [`plan`](plan/SKILL.md) | Turn requirements into an executable **plan.md** with task contracts. |
| 04 | [`execute`](execute/SKILL.md) | Execute plan tasks with checkpoint/recovery tracking. |
| 05 | [`review`](review/SKILL.md) | **Information-isolated** verification of executed work against the plan. |
| 06 | [`ship`](ship/SKILL.md) | Final handoff/report after verification. |
| 07 | [`finish`](finish/SKILL.md) | Close the task and handle branch/worktree disposition. |
| 08 | [`milestone`](milestone/SKILL.md) | Create and manage project milestones with dependency DAG. |
| 09 | [`long-run`](long-run/SKILL.md) | Record reusable learnings after high/epic route completion. |
| 10 | [`benchmark`](benchmark/SKILL.md) | Cross-adapter benchmark: same prompt → multiple agents → comparison report. |
| 11 | [`subagent-execute`](subagent-execute/SKILL.md) | **Opt-in:** high/epic per-plan-step subagent loop (implementer → spec micro → quality micro). |

## Skill lifecycle in a single task

```
User: "I want to build a daily briefing app"
  → init             → task workspace
  → clarify          → brief.md (route: medium)
  → plan             → plan.md
  → execute          → implementation-notes.md + code changes
  → review           → review-report.md
  → ship             → final handoff
  → finish           → branch disposition: merge, PR, keep, or discard
```

## Long-run lifecycle (complex tasks)

```
User: "Refactor the entire payment module"
  → init             → task workspace
  → clarify          → brief.md (route: high)
  → plan             → plan.md with verification targets
  → execute          → implementation-notes.md
  → review (spec)    → review-report.md (spec section)
  → review (quality) → review-report.md (quality section)
  → ship             → final handoff
  → finish           → branch disposition
  → long-run         → eval-record.md
```

## Epic lifecycle (massive tasks)

```
User: "Build a complete e-commerce platform"
  → init             → task workspace
  → clarify          → brief.md (route: epic)
  → milestone        → roadmap.md (M1: Auth, M2: Cart, M3: Checkout, M_final: Integration)
  → (per milestone)
    → plan           → plan.md
    → execute        → implementation-notes.md
    → review (spec)  → review-report.md (spec section)
    → review (quality) → review-report.md (quality section)
  → ship             → final handoff
  → finish           → branch disposition
  → long-run         → eval-record.md
```

## Adding a new skill

1. Pick a bounded skill name that matches a first-class plugin operation.
2. Copy the template from [`_template.md`](_template.md).
3. Create the active contract at `skills/<name>/SKILL.md`.
4. Fill in Purpose, Trigger, Input, Output, Execution, Constraints, Exit Condition.
5. Add a row to the table above only if the skill is part of the active surface.
