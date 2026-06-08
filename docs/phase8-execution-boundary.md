# Phase 8: Real Adapter Execution Boundary

> Design document for the first real adapter execution slice.
> Source: Issue #183

## Context

Phases 0-7.4 proved the local loop runtime skeleton:

- queue/status/next task selection
- stub adapter step execution
- verification-gated `done`
- retry/blocker metadata
- ship boundary ledger
- learning/preflight candidate capture
- disposable full-loop E2E without credentials

That is enough scaffolding. Phase 8 should not add more philosophy — it should specify the first real execution boundary.

## Problem Statement

ForgeFlow's artifact contract is solid: brief → plan → implementation-notes → review-report → ship-summary. But the actual **execution** of implementation steps is left entirely to the agent's interpretation. There is no boundary between "the plan said to do X" and "X was actually done correctly."

This matters because:
1. Agents can claim completion without evidence
2. Review cannot distinguish "ran tests" from "tests pass"
3. Multi-adapter workflows have no shared execution contract

## Design: Execution Boundary Contract

### Boundary definition

The execution boundary is the point where a plan step transitions from "planned" to "executed." It is enforced by **evidence gates**, not by trust.

```
Plan Step → [Execution Boundary] → Evidence Gate → Verified Step
```

### Evidence Gate Schema

Each plan step in `ledger.md` must produce:

| Field | Required | Description |
|-------|----------|-------------|
| `step_id` | yes | Unique identifier from plan.md |
| `status` | yes | `pending` \| `in_progress` \| `completed` \| `blocked` \| `skipped` |
| `evidence` | yes | List of evidence items (command output, file path, artifact) |
| `evidence_type` | yes | `command_output` \| `file_created` \| `file_modified` \| `artifact_written` \| `manual_verification` |
| `verification_command` | conditional | Command that proves completion (required for `command_output` type) |
| `verified_at` | conditional | ISO timestamp when evidence was confirmed (set by verify step) |
| `verifier` | conditional | Agent/model that performed verification |

### Adapter execution contract

For multi-adapter scenarios (different models or tools executing different steps):

1. **Step claim**: Before executing, adapter writes `status: in_progress` to `ledger.md` with its adapter ID.
2. **Evidence write**: After execution, adapter appends evidence items.
3. **Verification**: A separate verification pass (could be same or different adapter) runs `verification_command` and sets `verified_at`.
4. **Conflict resolution**: If two adapters claim the same step, the one with the earlier claim wins. The other must re-read and adapt.

### Boundary enforcement in pipeline

```
execute stage:
  for each plan step:
    1. Claim step in ledger.md
    2. Implement changes
    3. Write evidence (files changed, commands run, artifacts produced)
    4. Run verification_command if defined
    5. Mark step completed with verified_at if verification passes
    6. If verification fails: mark blocked, record failure in implementation-notes.md

review stage:
  for each completed step:
    1. Read evidence from ledger.md
    2. Verify evidence_type matches claimed evidence
    3. Re-run verification_command for critical steps
    4. Flag steps with missing or unverifiable evidence
```

### Implementation milestones

| Milestone | Scope | Dependencies |
|-----------|-------|-------------|
| M1: Evidence gate schema in ledger.md | Schema update only | ledger.md template |
| M2: Execute writes evidence per step | execute SKILL.md update | M1 |
| M3: Review validates evidence | ff-review SKILL.md update | M2 |
| M4: Multi-adapter step claiming | Adapter config update | M2 |
| M5: Cross-adapter conflict resolution | New: step-locking protocol | M4 |

### What this does NOT do

- Does not add a runtime/daemon — ForgeFlow remains prompt-driven
- Does not require a specific tool or API — evidence is Markdown
- Does not change the existing artifact contract — it adds a verification layer
- Does not replace human review — evidence gates augment, not replace

## Open questions

1. Should `verification_command` be auto-detected from plan.md or explicitly authored?
2. What is the minimum evidence for a "file_modified" type — diff, hash, or just path?
3. Should multi-adapter execution require worktree isolation even for small routes?

## Resolution

These questions should be resolved during M1 implementation, not in this design doc.
