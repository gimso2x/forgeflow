---
name: subagent-execute
description: Opt-in per-plan-step subagent loop for high/epic execute — implementer then spec micro-review then quality micro-review per task. Use when the user types /subagent-execute, /forgeflow:subagent-execute, or /forgeflow:execute --subagent-per-task after an approved plan.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must only run on high or epic routes with an approved plan.md.
  Must use skills/execute/references prompts and write the same execute artifacts as /forgeflow:execute.
  Must not treat micro-review or worker self-report as stage review approval.
  Must not dispatch parallel implementer subagents for steps that touch the same file.
---

# Subagent Execute (opt-in)

Use this skill when the operator wants **Superpowers-style subagent-driven development** inside ForgeFlow: one fresh worker subagent per plan step, then spec micro-review, then quality micro-review, before moving to the next step.

This skill is **optional**. Default execution remains `/forgeflow:execute` (controller-led or selective delegation).

## When to use

Use when **all** are true:

1. Route is **high** or **epic** (medium only if the user explicitly opts in and accepts overhead)
2. `plan.md` exists and the user approved entering execute
3. User invoked `/forgeflow:subagent-execute`, `/subagent-execute`, or `/forgeflow:execute --subagent-per-task`

Do **not** use for small route (overhead exceeds benefit).

## When not to use

- Steps share the same files (use sequential `/forgeflow:execute` or single worker)
- Environment setup step or final integration-only step (controller runs these)
- User asked for default execute without subagent-per-task flag

## Input

Same as [`execute`](../execute/SKILL.md): `brief.md`, `plan.md`, task directory `.forgeflow/tasks/<task-id>/`

## Output Artifacts

Same as execute:

- Code changes per plan
- `implementation-notes.md`, `run-ledger.md`, `checkpoint.md`
- Per-step Evidence: `micro_spec:PASS|FAIL`, `micro_quality:PASS|FAIL` (when quality micro-review runs)

Do **not** write `review-report.md` during this skill. Stage review remains `/forgeflow:review`.

## Reference prompts

| Step | Template | Dispatch tag |
|------|----------|-------------|
| Implementer | `skills/execute/references/implementer-prompt.md` | `implementer-prompt.md` |
| Spec micro-reviewer | `skills/execute/references/spec-reviewer-prompt.md` | `spec-reviewer-prompt.md` |
| Quality micro-reviewer | `skills/execute/references/quality-reviewer-prompt.md` | `quality-reviewer-prompt.md` |

Paste **full plan step text** into each dispatch. Subagents must not read `plan.md` directly.

Each dispatch must record the **Dispatch tag** (prompt filename) in the run-ledger Assignee entry so the audit trail shows which reference prompt drove each subagent. This makes the workflow reproducible and verifies that the correct prompt was used.

## Per-task loop (strict order)

For each plan step in dependency order:

```text
1. Controller sets run-ledger: running, Assignee worker
   → Record dispatch: "implementer-prompt.md"
2. Dispatch implementer subagent (references/implementer-prompt.md)
3. If NEEDS_CONTEXT → provide context and re-dispatch
   If BLOCKED → ledger blocked; stop or escalate to user
4. Controller verifies: git diff --stat + step verification commands
5. Dispatch spec micro-reviewer OR controller spec micro-check
   → Record dispatch: "spec-reviewer-prompt.md"
   → micro_spec:PASS|FAIL in implementation-notes
6. If spec not approved → implementer fixes → re-review spec (loop)
7. Dispatch quality micro-reviewer OR controller quality micro-check
   → Record dispatch: "quality-reviewer-prompt.md"
   → micro_quality:PASS|FAIL in implementation-notes
8. If quality not approved → implementer fixes → re-review quality (loop)
9. Mark step done in run-ledger only after steps 4–8 pass
10. Update checkpoint.md → next step
```

**Never** skip spec before quality. **Never** mark done on worker DONE alone.

## Parallelism

- **Implementer subagents:** one at a time per conflicting file set (same rule as execute delegation)
- **Fan-out:** only when plan marks steps `(none)` dependency and disjoint file scopes; still **fan-in** with per-step micro-gates before marking done
- Do not run two implementers that touch the same file concurrently

## Model hints

When the shell supports role-specific models:

- Mechanical steps (1–2 files, complete spec) → fast/cheap model
- Integration / multi-file steps → standard coding model
- Micro-reviewers → strongest available for spec; standard for quality if step is mechanical

## Relationship to other stages

| Stage | Responsibility |
|-------|----------------|
| This skill | Per-step worker + micro-gates; artifacts in implementation-notes / run-ledger |
| `/forgeflow:review` | Independent stage review; fills `review-report.md` including **Execute Micro-Gates** with re-verification |
| `/forgeflow:ship` | After review approved |

## Exit Condition

- All plan steps `done` or explicitly `blocked` with evidence
- `implementation-notes.md` Status: completed (or blocked)
- Required verification gates recorded (see execute skill)
- Prompt user for stage review (high/epic spec first):

```text
subagent-execute 완료. /forgeflow:review --type spec 을 진행하시겠습니까? (y/n)
```

## File write discipline

→ Same rules as [`execute`](../execute/SKILL.md): artifact-first under `.forgeflow/tasks/<task-id>/`, never write inside `skills/`.

## Automation

If `--yes` / `--auto-approve` is in scope, proceed through **tasks within this skill** without per-task y/n prompts. Still never skip micro-gates or stage review.
