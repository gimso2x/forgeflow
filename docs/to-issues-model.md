# To-Issues Model

## Purpose

`to-issues` converts an approved ForgeFlow plan into issue-ready draft slices without turning GitHub issues into the source of truth.

The model absorbs the useful part of `mattpocock/skills` `to-issues`: make work small, publishable, and traceable. It rejects the bad version: a second planning system wearing a GitHub hat.

## Position in ForgeFlow

`to-issues` is an optional helper skill. It is not a new canonical stage.

Default flow:

```text
clarify -> specify -> plan -> optional to-issues -> run -> review -> ship
```

Artifact authority stays simple:

| Concern | Owner |
|---------|-------|
| Scope, decomposition, acceptance intent | `plan.json` |
| Interfaces, invariants, compatibility boundaries | `contracts.md` |
| Labels, milestones, target repository | adapter metadata |
| Runtime progress | `plan-ledger.json` / `run-state.json` |
| Published GitHub issue ids | publication adapter output, not `to-issues` |

## Output artifact

The optional machine-readable artifact is `issue-drafts.json`, validated by `schemas/issue-drafts.schema.json`.

A markdown issue bundle is allowed for human-only planning, but schema-backed JSON is preferred when any adapter might publish later.

Minimum fields per draft:

- stable draft id, for example `draft-contract-boundary`
- title
- summary
- `slice_type: vertical|discovery`
- `human_gate: required|not_required`
- `blocked_by` draft ids or already-known external ids
- trace links to `plan.json.steps[].id`
- `fulfills` links copied from the plan when available
- stable `contracts.md` anchors when available
- acceptance checks derived from plan intent
- verification expectations derived from plan and contracts

## Vertical slice rubric

A good issue draft is a vertical tracer bullet:

- it produces one user- or operator-visible outcome;
- it can be reviewed independently;
- it has concrete verification evidence;
- it traces to at least one plan step;
- it does not merely say "update backend", "add frontend", or "write tests".

Horizontal chores are allowed only when they unblock a vertical slice and carry explicit trace or discovery justification. Otherwise they are fake progress. Fake progress is expensive confetti.

## Discovery issue rule

A discovery draft is valid only when implementation is blocked by missing information.

It must include:

- the question;
- evidence to gather;
- artifact to produce;
- decision unblocked.

Discovery drafts use `slice_type: discovery` and `human_gate: required`.

## Staleness rule

An issue draft bundle becomes stale if any of these change:

- traced plan step ids;
- `fulfills` links;
- referenced contract anchors;
- acceptance checks in the source plan;
- publication target metadata after the bundle was prepared for a specific repository.

Stale bundles must be regenerated or marked stale in a decision log before use.

## Issue readiness policy

Issue readiness means a draft is safe for an agent or human to pick up without replaying the whole planning conversation.
It distinguishes **human-gated work from agent-ready work** in ForgeFlow-native terms:

- `human_gate: required` means the draft needs a product, security, access, release, or irreversible-scope decision before execution.
- `human_gate: not_required` means the draft has enough plan trace, acceptance checks, and verification expectations for an agent to execute within the approved scope.
- The gate is readiness metadata, not a new lifecycle state.

A ready draft separates **user-facing behavior from implementation guesses**:

- user-facing behavior belongs in the summary, acceptance checks, and verification expectations;
- implementation guesses belong in notes or constraints only when backed by the approved plan, contracts, or repo evidence;
- speculative fixes should not masquerade as accepted requirements.

Root cause should be investigated before filing fix-oriented issues when feasible. If the root cause is unknown, create a discovery draft instead of pretending the fix is obvious.

GitHub labels and milestones are publication metadata. They may help humans triage after publication, but ForgeFlow does not create a runtime issue state machine from labels, milestones, or GitHub project columns.

## Publication boundary

`to-issues` never calls the GitHub API.
Publishing is a later adapter action. Labels and milestones are adapter metadata. They do not define core artifact identity.
This boundary also means `to-issues` does not mutate issues, infer completion from labels, or require a GitHub-specific workflow to be considered canonical.

## Example

See `examples/artifacts/issue-drafts.sample.json`.
