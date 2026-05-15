# End-to-end example: Next.js task through ForgeFlow

This example shows what a developer should expect when they run ForgeFlow in a real project. It is intentionally concrete; the exact wording may vary by adapter, but the artifacts and gates are the same.

**You can find the actual JSON artifacts for this example in the [end-to-end-nextjs-flow/](end-to-end-nextjs-flow/) directory.**

## Scenario

Project: a Next.js app with `app/page.tsx`, `components/`, and `npm test`/`npm run lint` available.

Task:

```text
Add an accessible empty-state card to the dashboard when there are no projects.
It should include a title, short description, and a primary "Create project" link.
```

## 1. Clarify

In Claude Code:

```text
/forgeflow:clarify Add an accessible empty-state card to the dashboard when there are no projects. It should include a title, short description, and a primary "Create project" link.
```

Expected behavior:

- ForgeFlow inspects the repo context.
- It writes a brief artifact under `.forgeflow/tasks/<task-id>/brief.json`.
- It selects a route. This task should usually be `small` or `medium` depending on project uncertainty.
- If requirements are ambiguous, the agent asks only the must-answer questions.

Typical brief summary:

```text
Goal: show an accessible dashboard empty state when the project list is empty.
In scope: dashboard UI, empty-state copy, link target, tests/lint.
Out of scope: project creation backend, auth changes, database migrations.
Acceptance: empty list renders title/description/Create project link; non-empty list still renders projects; lint/tests pass.
Risk: low.
Route: small.
```

## 2. Plan

For `small`, the agent may proceed with a short implicit plan. For `medium` or higher, run:

```text
/forgeflow:plan
```

Expected artifacts:

- `.forgeflow/tasks/<task-id>/plan.json`
- `.forgeflow/tasks/<task-id>/plan-ledger.json`

Typical plan steps:

1. Locate dashboard data/rendering path.
2. Add empty-state component or branch.
3. Add or update a UI test for empty/non-empty states.
4. Run `npm test` and `npm run lint`.

Gate behavior:

- The plan must include verification targets.
- Steps should map back to acceptance criteria.

## 3. Execute

```text
/forgeflow:execute
```

Expected behavior:

- The agent edits only files needed for the approved scope.
- Important decisions are recorded in `.forgeflow/tasks/<task-id>/decision-log.json`.
- Runtime state is updated in `.forgeflow/tasks/<task-id>/run-state.json`.
- Verification commands are run before the agent claims completion.

Example implementation outcome:

```text
Modified:
- app/dashboard/page.tsx
- app/dashboard/page.test.tsx

Verification:
- npm test -- app/dashboard/page.test.tsx
- npm run lint
```

## 4. Review

```text
/forgeflow:review
```

Expected behavior:

- Review is evidence-based and separate from implementation.
- ForgeFlow checks that the implementation satisfies the brief/plan and that verification evidence exists.
- Review writes a review report artifact such as `.forgeflow/tasks/<task-id>/review-report.json` or role-specific review reports.

Typical review verdict:

```text
Approved: yes
Evidence:
- Empty-state test covers zero projects.
- Existing non-empty rendering still passes.
- lint passed.
Open blockers: none.
Next action: ship.
```

If evidence is missing, review blocks and points back to the exact missing command, artifact, or acceptance criterion.

## 5. Ship

```text
/forgeflow:ship
```

Expected behavior:

- The agent summarizes changed files, artifacts, verification, and review verdict.
- It prepares the handoff/PR text if requested.
- It does not erase the `.forgeflow/tasks/<task-id>/` evidence trail.

## What happened when you typed `/forgeflow:clarify`?

ForgeFlow did not replace Claude Code, Codex, or Gemini. It gave the agent a contract to follow:

- create durable artifacts instead of relying on chat memory;
- choose a route based on risk/complexity;
- require plan and verification evidence when needed;
- prevent self-approved claims from bypassing review;
- leave a resumable trail under `.forgeflow/tasks/<task-id>/`.

## Adapter notes

- Claude Code uses `/forgeflow:<stage>` slash skills.
- Codex/Gemini surfaces may expose equivalent prompts or local plugin commands, but the expected artifacts and stage gates remain the same.
- Multi-model orchestration is not required for this example; `orchestra/` stays inactive in a single-agent setup.
