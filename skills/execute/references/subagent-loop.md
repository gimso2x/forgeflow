# Subagent Per-Task Loop

> Reference for `--subagent-per-task` mode. Extracted from execute SKILL.md.

For **high/epic** routes when the user wants every plan step to run implementer → spec micro-review → quality micro-review subagents in strict sequence, enable this mode via `/forgeflow:execute --subagent-per-task`. Default `/forgeflow:execute` remains controller-led with optional delegation.

## When to use

Use when **all** are true:

1. Route is **high** or **epic** (medium only if the user explicitly opts in and accepts overhead)
2. `plan.md` exists and the user approved entering execute
3. User invoked `/forgeflow:execute --subagent-per-task` or explicitly requested subagent-driven execution

Do **not** use for small route (overhead exceeds benefit).

## When not to use

- Steps share the same files (use sequential controller-led execution)
- Environment setup step or final integration-only step (controller runs these)
- User asked for default execute without `--subagent-per-task`

## Per-task loop (strict order)

For each plan step in dependency order:

```text
1. Controller sets ledger: running, Assignee worker, Claim Marker with role/scope/timestamp
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
9. Mark step done in ledger only after steps 4–8 pass
10. Update checkpoint.md → next step
```

**Never** skip spec before quality. **Never** mark done on worker DONE alone.

## Parallelism

- **Implementer subagents:** one at a time per conflicting file set (same rule as execute delegation)
- **Fan-out:** only when plan marks steps `(none)` dependency and disjoint file scopes; write a Claim Marker for each fanned-out task before dispatch, then **fan-in** with per-step micro-gates before marking done
- Do not run two implementers that touch the same file concurrently

## Model hints

When the shell supports role-specific models:

- Mechanical steps (1–2 files, complete spec) → fast/cheap model
- Integration / multi-file steps → standard coding model
- Micro-reviewers → strongest available for spec; standard for quality if step is mechanical

## Subagent reference prompts

Dispatch templates live beside this skill (paste full plan step text; never point subagents at `plan.md`):

| Role | File |
|------|------|
| Implementer / specialist worker | `references/implementer-prompt.md` |
| Spec micro-reviewer (high/epic) | `references/spec-reviewer-prompt.md` |
| Quality micro-reviewer (high/epic, after spec) | `references/quality-reviewer-prompt.md` |
