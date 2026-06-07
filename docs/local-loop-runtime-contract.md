# Local Loop Runtime Contract

<!-- ForgeFlow 2.0 runtime semantics. This document is executable policy for a future local runner and human/agent operators today. -->

## Purpose

ForgeFlow local loop mode turns a request into a resumable artifact loop:

1. classify the route,
2. choose the next ledger item,
3. run the minimum allowed stage action,
4. record real evidence,
5. decide whether to continue, retry, escalate, block, or ship.

The runtime is not a hidden chat transcript. The state lives in the task directory artifacts.

## Source of Truth

Read in this order:

1. `checkpoint.md` — resume pointer, current stage, next action, latest evidence.
2. `ledger.md` — item status, assignee, retry count, blocker, evidence refs.
3. `implementation-notes.md` — reader summary, decisions, evidence index, command/artifact evidence blocks.
4. `plan.md` — referenced plan item only, except on `small` where `brief.md` is enough.
5. `review-report.md` — only when the current transition depends on review verdict.

Never use chat memory as the runtime source of truth.

## Canonical Status Values

Ledger item status enum:

- `pending`: queued and unclaimed.
- `in_progress`: claimed by the current assignee.
- `blocked`: cannot proceed without a blocker resolution or user decision.
- `done`: verified and linked to evidence.
- `discarded`: removed from the loop scope by an explicit decision.

Stage status enum:

- `in_progress`
- `completed`
- `blocked`

## Core State Machine

```text
pending
  -> in_progress
  -> done
  -> pending            # retry/requeue after failed verification or review changes
  -> blocked            # missing info, unsafe side effect, unavailable tool, conflict
  -> discarded          # explicit scope removal

blocked
  -> pending            # blocker resolved
  -> discarded          # blocker makes item out of scope

done
  -> pending            # review requests re-execution
  -> completed/ship     # all required gates pass
```

Each transition must update `checkpoint.md`, `ledger.md`, and when evidence exists, `implementation-notes.md`.

## Route-Specific Transitions

### small

Use for one narrow change with low uncertainty.

Flow:

```text
clarify -> execute -> self_verify -> ship_summary
```

Rules:

- `plan.md` is optional.
- One ledger item is enough.
- Independent review is skipped unless risk signals appear.
- A single failed verification can retry once; repeated failure promotes to `medium` or `blocked`.
- Ship must report real evidence, not agent claims.

Promotion triggers:

- touched scope grows beyond the brief,
- user-visible behavior requires design/spec judgment,
- verification requires multiple environments,
- more than one retry is needed.

### medium

Use for bounded multi-file work or moderate uncertainty.

Flow:

```text
clarify -> plan -> execute -> review -> re_execute? -> ship
```

Rules:

- `plan.md`, `ledger.md`, `checkpoint.md`, and `implementation-notes.md` are required.
- Review is required before ship.
- Failed review writes re-execution conditions into `checkpoint.md` and requeues only affected ledger items.
- Retry budget: 2 execute attempts per item before block/escalation.

Promotion triggers:

- file ownership conflicts,
- architectural boundary changes,
- external side effects,
- more than 3 plan items with dependencies.

### high

Use for broad changes, multiple subsystems, or non-trivial risk.

Flow:

```text
clarify -> plan -> execute_with_micro_gates -> review -> re_execute? -> ship -> long_run_extract
```

Rules:

- Per-task micro-gates run before marking items `done`.
- Specialist or reviewer roles may be used, but every handoff needs claim markers and evidence refs.
- Worktree isolation is recommended for risky implementation work.
- Retry budget: 2 per item, 3 total loop iterations.
- If scope drift appears, stop and revise plan instead of quietly expanding work.

Promotion triggers:

- fan-out/fan-in needed,
- multiple workers could collide,
- release/compatibility policy is affected,
- repeated blockers reveal missing product decision.

### epic

Use for roadmap-level work that must be decomposed into milestones.

Flow:

```text
clarify -> plan -> roadmap -> milestone_loop* -> review -> ship_per_milestone -> long_run_extract
```

Rules:

- `roadmap.md` is required.
- Each milestone gets its own ledger slice or issue/PR-sized task.
- Do not run the whole epic as one giant prompt. That is how you manufacture soup.
- Fan-out/fan-in is allowed only when path ownership is explicit.
- Human approval is required before cross-milestone merge, release, or destructive cleanup.

## Failure Types

### verification_failed

A real command or deterministic check failed.

Required action:

- record command evidence with non-zero exit or failing result,
- keep or move the item to `pending` if retry budget remains,
- move to `blocked` if the same failure repeats beyond budget.

### review_blocked

Review cannot approve because evidence, scope, or role input is missing.

Required action:

- write missing evidence/scope into `checkpoint.md` Re-Execution Conditions,
- requeue only the affected items,
- do not ship.

### scope_drift

Implementation exceeds approved brief/plan boundaries.

Required action:

- stop the item,
- record deviation in `implementation-notes.md`,
- either revise plan with explicit decision or discard out-of-scope changes.

### needs_user_decision

A safe default does not exist: credential, billing, destructive cleanup, external publish, release, or policy decision.

Required action:

- set stage/item to `blocked`,
- write the exact decision needed,
- do not guess.

### agent_error

Agent/tool failed without producing useful implementation evidence.

Required action:

- record the failure as command/artifact evidence if observable,
- retry with an alternate adapter only if the route budget allows,
- block if retry would hide a real decision or environment problem.

## Retry Budgets

Default budgets:

- `small`: 1 retry.
- `medium`: 2 retries per item.
- `high`: 2 retries per item, 3 total loop iterations.
- `epic`: budget belongs to each milestone, not the entire epic.

A retry requires a changed condition: modified code, modified plan, new evidence, resolved blocker, or revised scope. Blind reruns are noise.

## Route Promotion and Demotion

Promotion is mandatory when the current route cannot safely verify or review the work.

Demotion is allowed when planning proves the scope is narrower than expected.

Record either decision in `implementation-notes.md`:

```text
D-<!-- N --> route_change from=<old> to=<new> reason=<evidence-based reason>
```

## Evidence Requirements

Every `done` item needs at least one evidence ref.

Accepted evidence:

- command evidence block in `implementation-notes.md`,
- artifact evidence block in `implementation-notes.md`,
- CI/check URL,
- review verdict with normalized evidence refs,
- concrete file path plus verified claim.

Rejected evidence:

- "agent says done",
- chat-only claims,
- unrun command names,
- screenshots without a stated claim and source,
- broad summaries with no path, command, URL, or artifact ref.

## Human Gates

Human approval is required before:

- push to third-party target not owned by the user,
- release/tag/publish,
- destructive cleanup that removes unmerged work,
- credential/billing changes,
- canonical rule promotion,
- cross-milestone epic merge.

Local commits and PRs inside the user's repo are allowed when the user has asked for autonomous completion.

## Minimal Runtime Algorithm

```text
read checkpoint.md
read ledger.md task named by Resume Pointer
if no resume pointer:
  choose first pending ledger item
if item blocked:
  report blocker and stop
if item pending:
  claim as in_progress
  run route-allowed action
  record evidence
  update status
if all required items done:
  run route-required review/ship transition
else:
  update checkpoint next action and continue if budget remains
```

## MVP Boundary

The first local runner only needs to:

- parse status from `checkpoint.md` and `ledger.md`,
- print the next action,
- record item status and evidence refs,
- enforce canonical status values,
- refuse ship when required evidence is missing.

It does not need to invoke external coding agents, create worktrees, or merge PRs. Those belong to later phases.
