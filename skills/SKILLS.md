# ForgeFlow Skills

Skills are markdown documents that live in `skills/`. Each skill defines a bounded operation with explicit inputs, outputs, and trigger conditions.

## Design rules

1. **One skill = one bounded operation.** No skill tries to do everything.
2. **Every skill declares its output artifacts.** If it doesn't write to disk, it's not a skill.
3. **Skills chain; they don't fork.** The output of skill N is the required input of skill N+1.
4. **Trigger phrases are advisory, not magical.** The operator or an adapter decides when to invoke a skill.
5. **Cross-cutting skills are prefixed with `x-`.** They can be invoked at any stage.

## Workflow skills (ordered)

| # | Skill | Purpose | Borrowed from |
|---|-------|---------|---------------|
| 01 | [`clarify`](clarify/SKILL.md) | Resolve ambiguity, explore codebase, emit a **Context Brief** with complexity routing. | engineering-discipline |
| 02 | [`specify`](specify/SKILL.md) | Derive structured **requirements.md** from the brief through a decision interview. | hoyeon |
| 03 | [`plan`](plan/SKILL.md) | Turn requirements into an executable **plan.json** with task contracts. | hoyeon + engineering-discipline |
| 04 | [`run`](run/SKILL.md) | Execute plan tasks using **worker-validator pairs** with checkpoint/recovery. | engineering-discipline |
| 05 | [`review`](review/SKILL.md) | **Information-isolated** verification of executed work against the plan. | engineering-discipline |
| 06 | [`ship`](ship/SKILL.md) | Final handoff/report after verification; branch disposition lives in [`finish`](finish/SKILL.md). | gstack |

## Cross-cutting skills (invoke any time)

| Skill | Purpose | Borrowed from |
|-------|---------|---------------|
| [`x-tdd`](x-tdd.md) | RED-GREEN-REFACTOR enforcement. | superpowers |
| [`x-qa`](x-qa.md) | Browser-based functional QA with regression test generation. | gstack |
| [`x-debug`](x-debug.md) | Reproduce-first, root-cause tracing with reference playbooks. | engineering-discipline |
| [`x-deslop`](x-deslop.md) | Remove LLM-specific code smells: over-commenting, unnecessary abstractions, filler. | engineering-discipline |
| [`x-spec-review`](x-spec-review.md) | Verify correctness vs requirements **before** quality review. | superpowers |
| [`safe-commit`](safe-commit/SKILL.md) | Pre-commit safety review: secrets, scope drift, generated files, verification evidence, final `SAFE`/`UNSAFE`. | so2x-harness |
| [`check-harness`](check-harness/SKILL.md) | Score harness health across entry points, shared context, execution habits, verification, and maintainability. | so2x-harness |
| [`to-issues`](to-issues/SKILL.md) | Convert approved plans into traceable issue draft bundles without publishing them. | mattpocock/skills |
| [`design-interface`](design-interface/SKILL.md) | Define task-local interface contracts before implementation when public boundaries change. | mattpocock/skills |
| [`x-resume`](x-resume.md) | Resume interrupted sessions from checkpoint. | engineering-discipline |
| [`x-learn`](x-learn.md) | Capture typed learnings to `memory/learnings.json` for BM25 surfacing. | hoyeon |
| [`x-office-hours`](x-office-hours.md) | Reframe the problem before writing code. Six forcing questions. | gstack |

## Skill lifecycle in a single task

```
User: "I want to build a daily briefing app"
  → clarify          → brief.json + complexity=medium
  → specify          → requirements.md
  → plan             → plan.json
  → run              → decision-log.json + run-state.json + plan-ledger.json + code changes
  → review           → review-report.json
  → ship             → PR + cleanup
```

## Long-run lifecycle (complex tasks)

```
User: "Refactor the entire payment module"
  → clarify          → brief.json + complexity=large
  → x-office-hours   → reframed goal
  → specify          → requirements.md
  → plan             → plan.json with milestone DAG
  → run (M1)         → checkpoint-1.json + plan-ledger.json
  → x-spec-review    → spec-review-report-1.json
  → review (M1)      → review-report-1.json
  → run (M2)         → checkpoint-2.json
  → x-spec-review    → spec-review-report-2.json
  → review (M2)      → review-report-2.json
  ...
  → ship             → final PR
```

## Adding a new skill

1. Pick the next available number or `x-` prefix.
2. Copy the template from [`_template.md`](_template.md).
3. Create the active contract at `skills/<name>/SKILL.md`; keep historical imports under `docs/legacy/skills/`, not beside active plugin contracts.
4. Fill in Purpose, Trigger, Input, Output, Execution, Constraints, Exit Condition.
5. Add a row to the table above.
6. Run `make validate`.
