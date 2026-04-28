# Matt Pocock Skills Absorption Backlog

Date: 2026-04-28
Status: Revised draft issue bundle after Claude/Codex review
Source design: `docs/plans/2026-04-28-mattpocock-skills-absorption-plan.md`

Cross-cutting acceptance criterion for all issues:

- The change must strengthen an existing ForgeFlow stage or artifact and must not create a new required source of truth, runtime state, approval checkpoint, or persistence lane.

## Issue 1 — Add ForgeFlow-native `to-issues` draft artifact model

Priority: P0
Human gate: not_required after design approval
Blocked by: none

### Problem

ForgeFlow has strong planning artifacts, but no native way to translate an approved `plan.json` into issue-ready backlog slices. Operators currently have to manually restate the plan when creating GitHub issues, which loses traceability and can accidentally create a second planning surface.

### Proposal

Add an optional `to-issues` support skill and model doc that turns an approved plan into vertical issue drafts while preserving artifact authority.

### Scope

Create:

- `skills/to-issues/SKILL.md`
- `docs/to-issues-model.md`
- either `examples/artifacts/issues.sample.json` plus schema-backed contract, or a decision note explaining why markdown issue bundles are enough

The skill should accept:

- required: approved `plan.json`
- optional: `brief.json`, `contracts.md`
- optional publication adapter metadata: labels, milestones, target repo context

The output should include one issue draft per vertical slice with:

- stable draft issue id before publication
- title
- summary
- ForgeFlow-native gate field, for example `human_gate: required|not_required`
- optional human-blocker detail naming the needed answer or artifact
- blocked-by relationships using draft ids or existing issue ids
- acceptance checks derived from plan intent
- verification expectations derived from plan and contracts
- trace links to `plan.json.steps[].id`, `fulfills`, and stable `contracts.md` anchors when available

### Artifact authority rules

- `plan.json` owns scope, decomposition, and acceptance intent.
- `contracts.md` owns boundary, interface, compatibility, and invariant constraints.
- issue drafts are derived execution artifacts and cannot add net-new acceptance requirements without an explicit decision note.
- if a traced plan step, `fulfills` link, or contract section changes, the issue bundle must be regenerated or explicitly marked stale.

### Applicability threshold

Use `to-issues` only when:

- a plan needs multiple independently verifiable slices, or
- the user wants a publication-ready backlog bundle, or
- the work needs human-gated and agent-ready chunks separated before execution

Do not use it for one-file or one-step tasks.

### Discovery issue rule

Discovery-only issue drafts must include:

- the question
- evidence to gather
- artifact to produce
- decision unblocked

### Acceptance criteria

- The new skill has frontmatter, Input Artifacts, Output Artifacts, Procedure, Applicability, Exit Condition, and file-write discipline.
- The model preserves ForgeFlow's artifact-first flow and does not add a canonical stage.
- The skill output feeds existing planning/execution artifacts and does not create a separate approval gate.
- The artifact format decision is explicit: schema-backed `issues.json` plus sample, or markdown-only bundle plus decision note.
- Draft issues are vertical tracer bullets, not horizontal component chores; the model includes either examples or a rubric for this distinction.
- Every issue draft traces to at least one plan step or follows the discovery issue rule.
- Contract trace links use stable section headings/anchors or are omitted until such anchors exist.
- `AFK`/`HITL` are not artifact values; if mentioned, they appear only as upstream translation commentary.
- GitHub labels/milestones are adapter metadata, not core artifact identity.
- No GitHub API call is implied unless the user explicitly asks to publish.

### Verification

Run:

- `make validate`
- focused skill/markdown validation target if available
- `git diff --check`

### Non-goals

- No runtime state changes.
- No automatic GitHub publishing.
- No mandatory issue generation for small tasks.
- No GitHub-shaped artifact model as the core abstraction.

---

## Issue 2 — Add contract-first `design-interface` support skill

Priority: P0
Human gate: not_required after design approval
Blocked by: none

### Problem

Interface-heavy changes need better front-loaded contract design. Current planning guidance mentions contracts, but it does not force explicit comparison of interface shapes when the boundary is risky.

### Proposal

Add an optional `design-interface` support skill that translates the upstream `design-an-interface` idea into ForgeFlow's contract artifact model.

### Scope

Create:

- `skills/design-interface/SKILL.md`
- `docs/contract-design-model.md` or extend an existing contract doc if that is cleaner

The skill is used inside clarify/plan work. It produces inputs to existing artifacts; it is not a pre-plan lane.

Default output:

- `contracts.md` section

Optional output:

- `interface-spec.json` only if a contract schema already exists or this issue explicitly creates a decision explaining why JSON is needed

The design output should include:

- problem and callers
- public surface
- invariants
- compatibility constraints
- error behavior
- migration concerns
- at least two materially different interface options for non-trivial boundaries
- chosen option and rejected alternatives
- note on compatibility with existing contracts, if any exist

### Applicability threshold

Use `design-interface` for:

- externally consumed boundaries
- migration-sensitive boundaries
- compatibility-sensitive API/module seams
- ambiguity-heavy interfaces where multiple shapes are plausible

Skip it for obviously local changes already constrained by existing patterns.

### Acceptance criteria

- The skill is explicitly optional and does not replace `/forgeflow:plan`.
- The skill output feeds `contracts.md` and/or `plan` artifacts and creates no separate approval gate, lifecycle state, or persistence lane.
- The output strengthens contract metadata rather than creating a parallel design source of truth.
- The output format rule is explicit: default markdown contract section; JSON only through existing schema or a decision note.
- It avoids generic brainstorming fluff by requiring callers, invariants, compatibility, testing surface, and migration impact.
- It can be invoked during clarify/plan work without creating a new stage boundary.

### Verification

Run:

- `make validate`
- `git diff --check`

### Non-goals

- No mandatory parallel subagents.
- No new canonical `/forgeflow:design` stage.
- No interface design detached from existing repo patterns.

---

## Issue 3 — Add refactor-mode branch to `plan` guidance

Priority: P1
Human gate: not_required
Blocked by: none

### Problem

Refactors have different failure modes from feature work: behavior drift, unsafe migration boundaries, weak rollback plans, and tests that accidentally lock internals. ForgeFlow's `plan` skill should make those risks explicit without spawning another workflow.

### Proposal

Fold `request-refactor-plan` style guidance into `skills/plan/SKILL.md` as a refactor-mode branch.

### Scope

Modify:

- `skills/plan/SKILL.md`

Create if useful:

- `docs/refactor-planning-decision.md`

Refactor-mode entry criteria:

- behavior-preserving structural change across an existing public surface
- migration-sensitive internal reorganization
- test-sensitive decomposition work
- removal or replacement of implementation machinery while preserving user-visible behavior

When the task enters refactor mode, planning should require:

- preserved public behavior statement, or a decision explaining why the refactor is internal-only
- explicit non-goals
- migration boundary
- rollback, escape hatch, or explicit not-applicable note for contained internal refactors
- tiny always-green implementation steps
- regression verification strategy
- note on whether existing tests cover the affected public behavior

### Representation rule

Every refactor-specific requirement must map to an existing artifact field or a named markdown section. If no canonical representation exists, the issue must stop and produce a schema/decision note first.

### Acceptance criteria

- Existing `plan.json` schema constraints remain intact unless a separate decision proves a schema change is needed.
- Refactor guidance is a branch inside `plan`, not a new command or stage.
- Refactor-mode entry criteria are documented.
- The guidance prefers public-behavior verification over implementation-detail tests.
- The plan exit condition mentions refactor-specific checks only when applicable.
- The implementation proves where each refactor-specific requirement is represented.
- The change does not create a new required planning artifact outside the existing plan flow.

### Verification

Run:

- `make validate`
- any skill contract validation used by the repo
- `git diff --check`

### Non-goals

- No `/forgeflow:refactor-plan` command.
- No broad rewrite of the planning skill.
- No schema changes unless a separate decision proves they are needed.

---

## Issue 4 — Add issue-readiness and git-safety policy language

Priority: P1
Human gate: not_required
Blocked by: Issue 1 for issue-readiness semantics; can proceed independently only for git-safety wording

### Problem

The upstream repo has useful safety and triage instincts, but some are Claude-specific or label-system-specific. ForgeFlow should absorb the cross-agent policy language without binding itself to one tool or a heavy issue state machine.

### Proposal

Document cross-agent issue-readiness and git-safety heuristics in ForgeFlow's model/review docs and summarize them in support skills where appropriate.

### Canonical ownership

- `docs/to-issues-model.md` owns issue-readiness semantics.
- `docs/review-model.md` or a focused `docs/git-guardrail-decision.md` owns review/git-safety semantics.
- `skills/review/SKILL.md` may summarize and apply policy, but must not redefine it.

### Scope

Modify or create the smallest appropriate set among:

- `docs/review-model.md`
- `docs/git-guardrail-decision.md`
- `skills/review/SKILL.md`
- `docs/to-issues-model.md` only by referencing the Issue 1 canonical model, not redefining it

Do not add `skills/safe-commit/SKILL.md` unless that surface already exists and a separate decision makes it part of the product model.

Policy language to absorb:

- issue drafts distinguish human-gated work from agent-ready work in ForgeFlow-native terms
- issue drafts separate user-facing behavior from implementation guesses
- root cause should be investigated before filing fix-oriented issues when feasible
- broad staging is forbidden unless explicitly justified
- destructive git actions require explicit user approval
- reviews must name the exact diff scope and verification evidence
- dirty user work is preserved by default

### Acceptance criteria

- Claude-specific hook setup is not presented as ForgeFlow canon.
- The policy language applies equally to Claude, Codex, and future adapters.
- Normative policy has one canonical owner; skills link to or summarize it.
- Review guidance becomes stricter without duplicating existing text pointlessly.
- If labels are mentioned, they are examples or publication metadata, not required runtime state.
- Issue-readiness wording references Issue 1's model and does not define a competing model.

### Verification

Run:

- `make validate`
- `git diff --check`

### Non-goals

- No global `.claude` settings changes.
- No new runtime label state machine.
- No GitHub issue mutation in this task.
- No new safe-commit runtime surface in this slice.
