# Execution Patterns and Operator Prompts

> Reference for ForgeFlow's execution patterns, worktree isolation rules, and operator prompts. Extracted from forgeflow SKILL.md.

## Execution Patterns

Different routes use different execution strategies for parallel workers and reviewers.

### Pattern: producer-reviewer (default, all routes)

The implementer (producer) writes code. A separate review pass (reviewer) inspects the result. Every route uses this at minimum.

```
producer → artifact → reviewer → verdict
```

### Pattern: pipeline (sequential gates)

Steps execute in order with verification gates between them. Used when steps have data or state dependencies.

```
step 1 → gate → step 2 → gate → step 3 → final gate
```

Applied by default for medium routes and all routes with ordered plan steps.

### Pattern: fan-out/fan-in (parallel workers)

Multiple independent workers execute in parallel, then a single reviewer consolidates.
Use this for high/epic routes when plan tasks touch different files with no shared state.

```
worker A ──┐
worker B ──┤ → reviewer → verdict
worker C ──┘
```

**Worktree isolation requirement (high/epic):**
When fan-out activates, each parallel worker **must** operate in an isolated git worktree to prevent file conflicts. This is a safety prerequisite, not optional.

- **Bootstrap**: `git worktree add <storage-root>/worktrees/<task-id>-<worker-id> -b <branch>`
- **Mapping**: Each worker's task_dir maps to its own worktree. Workers never share a working directory.
- **Merge**: After all workers complete, fan-in merges worktrees back to the main branch. Resolve conflicts before review.
- **Cleanup**: After ship, remove worktrees with `git worktree remove <storage-root>/worktrees/<task-id>-<worker-id>`.

If the adapter/shell does not support worktree creation, fall back to sequential execution with a warning — do not run parallel workers in the same working tree.

**Worktree pre-merge verification gate (fan-in):**

Before merging any worktree back, verify ALL items:

1. **Clean state**: `git -C <worktree-path> status --porcelain` must be empty. Uncommitted changes → commit or discard first.
2. **Branch divergence**: `git log --oneline <main-branch>..<worker-branch>` — list commits for review. If unexpected commits exist → investigate before merge.
3. **No cross-worktree conflicts**: For each worktree pair (A, B), check `git diff --name-only <A-branch> <B-branch>` for overlapping files. Overlaps → resolve before merge.
4. **Verification pass**: Each worktree must have at least 1 verification gate PASS in its implementation-notes.md Evidence. No evidence → do not merge.
5. **Merge**: `git merge --no-ff <worker-branch>` — always create merge commit for traceability. `--ff` is forbidden for fan-in merges.

Record in implementation-notes.md: `worktree_gate:PASS worker=<id> commits=<N> conflicts=<N>`.

**Worktree cleanup checklist (ship):**

After ship completes:
1. List all worktrees: `git worktree list`
2. For each worktree in `<storage-root>/worktrees/`:
   - Verify branch is merged: `git branch --merged <main-branch>` includes the worker branch.
   - Remove worktree: `git worktree remove <path>`
   - Delete worker branch (optional): `git branch -d <worker-branch>`
3. Record: `worktree_cleanup:done removed=<N> remaining=<N>`

### When to use which pattern

| Route | Default pattern | When to upgrade |
|-------|----------------|-----------------|
| small | pipeline + producer-reviewer | Never — single worker is sufficient |
| medium | pipeline + producer-reviewer | Upgrade to fan-out when 3+ independent file groups |
| high | fan-out/fan-in + producer-reviewer | Always — separate spec and quality reviews |
| epic | fan-out/fan-in per milestone | Always — milestone-level parallel execution |

### Review depth by route

| Route | During execute (`/forgeflow:execute`) | After execute (`/forgeflow:ff-review`) |
|-------|--------------------------------------|-------------------------------------|
| small | Self-check + one fast relevant verification gate; no micro-reviewer subagents | Single **fast-review quality** pass: changed-file scope + acceptance sanity + one observed gate + blocker scan |
| medium | Step verification + contract checkpoint per plan step | Single **quality** pass |
| high | Per-step **spec micro-check** (controller or `references/spec-reviewer-prompt.md`); optional quality micro-check after spec passes | **Spec** pass then **quality** pass (sequential, same `review-report.md`) |
| epic | Same as high, per milestone plan step | Same as high, per milestone completion |

Execute micro-gates do not replace stage review. Worker self-report and micro-review are input; stage review records them in `review-report.md` → **Execute Micro-Gates** and re-verifies with observed evidence (see `templates/review-report.md`).

Subagent dispatch templates: `skills/execute/references/` (`implementer-prompt.md`, `spec-reviewer-prompt.md`, `quality-reviewer-prompt.md`).

Plans for high/epic routes should explicitly name the execution pattern in the Architecture Notes section.

## Operator Prompts

Small task:

```text
Use ForgeFlow. Clarify this request, choose the route, execute the smallest safe change,
then state what evidence justifies review and finalize.
```

Medium task:

```text
Use ForgeFlow. Clarify first, select the route, write a concrete plan with expected artifacts and verification,
then execute only after the plan is clear.
```

Large/high route task:

```text
Use ForgeFlow. Treat this as high route. Clarify, plan, execute,
run spec and quality review passes separately on review-report.md, and call out residual risk before finalize.
```

Epic/massive scale task:

```text
Use ForgeFlow. Treat this as an epic. Clarify, plan with epic decomposition,
then for each milestone: plan, execute, and review. Track progress in roadmap.md.
```
