# ForgeFlow Skills

Skills are markdown documents that live in `skills/`. Each skill defines a bounded operation with explicit inputs, outputs, and trigger conditions.

## Design rules

1. **One skill = one bounded operation.** No skill tries to do everything.
2. **Every skill declares its output artifacts.** If it doesn't write to disk, it's not a skill.
3. **Skills chain; they don't fork.** The output of skill N is the required input of skill N+1.
4. **Trigger phrases are advisory, not magical.** The operator or an adapter decides when to invoke a skill.
5. **Keep the active skill surface minimal.** Optional discipline, debugging, QA, and learning guidance belongs in docs or prompts unless it is a first-class plugin skill.

## Workflow skills (ordered)

Surface tiers:

- **Core workflow**: `clarify`, `ff-plan`, `execute`, `ff-review`, `ship`
- **Support**: `forgeflow`, `long-run`, `ff-loop`
- **Utility / optional**: `benchmark`, `qa`, `unstuck`

`ff-config` is listed separately under Utility skills because it manages project defaults rather than advancing a task artifact chain.

| # | Skill | Version | Purpose |
|---|-------|---------|---------|
| 00 | [`forgeflow`](forgeflow/SKILL.md) | 1.12.1 | Overview router for slash-style ForgeFlow prompts. |
| 01 | [`clarify`](clarify/SKILL.md) | 0.6.0 | Bootstrap task workspace, resolve ambiguity, explore codebase, emit a **brief.md** with complexity routing. |
| 02 | [`ff-plan`](ff-plan/SKILL.md) | 0.6.0 | Turn requirements into an executable **plan.md** with task contracts; includes epic decomposition for epic route. |
| 03 | [`execute`](execute/SKILL.md) | 0.7.0 | Execute plan tasks with checkpoint/recovery tracking; includes opt-in subagent per-task loop. |
| 04 | [`ff-review`](ff-review/SKILL.md) | 0.6.0 | **Information-isolated** verification. Pipeline mode: verify executed work against the plan. Standalone mode: review external input (URL/repo/diff/files) independently with role-based review. |
| 05 | [`ship`](ship/SKILL.md) | 0.4.0 | Final handoff, evolution rule extraction, and branch disposition (merge/PR/keep/discard). |
| 06 | [`long-run`](long-run/SKILL.md) | 0.5.0 | Record reusable learnings after high/epic route completion. |
| 07 | [`benchmark`](benchmark/SKILL.md) | 0.3.0 | Cross-adapter benchmark: same prompt → multiple agents → comparison report. |
| 08 | [`ff-loop`](ff-loop/SKILL.md) | 0.1.0 | Full lifecycle loop — one command from clarify through ship with auto-retry, route promotion, and re-plan. |
| 09 | [`qa`](qa/SKILL.md) | 0.1.0 | Lightweight 3-point QA verdict (Completeness, Correctness, Actionability) on any ForgeFlow artifact. |
| 10 | [`unstuck`](unstuck/SKILL.md) | 0.1.0 | Break through implementation blocks using lateral thinking personas (hacker, researcher, simplifier, architect, contrarian). |
| 11 | [`status`](status/SKILL.md) | 0.1.0 | Show current task status, project task list, and active blockers. Read-only, no artifacts written. |

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
User: "/forgeflow:ff-review https://github.com/org/repo/pull/42"
  → review (standalone)     → synthetic task dir + normalized-input.md + review-report.md
```

```
User: "/forgeflow:ff-review --type security ./src/"
  → review (standalone)     → security-reviewer only → review-report.md
```

## Utility skills

| # | Skill | Version | Purpose |
|---|-------|---------|---------|
| U1 | [`ff-config`](ff-config/SKILL.md) | 0.6.0 | Manage ForgeFlow project defaults interactively. Toggle auto-chaining and worktree isolation. |
| U2 | [`audit-report`](audit-report.md) | — | Historical skill audit report (v1.12.0 deep audit). Reference only, not a runtime skill. |

## Adding a new skill

1. Pick a bounded skill name that matches a first-class plugin operation.
2. Copy the template from [`_template.md`](_template.md).
3. Create the active contract at `skills/<name>/SKILL.md`.
4. Fill in Purpose, Trigger, Input, Output, Execution, Constraints, Exit Condition.
5. Add a row to the table above only if the skill is part of the active surface.
