# Automation / Non-Interactive Approval Mode

Shared rules for handling automated ForgeFlow stage transitions.

## Flags

The following flags enable automated stage transitions:

- `--yes` — approve the current stage boundary only
- `--auto-approve` — same as `--yes`
- `--non-interactive` — suppress interactive prompts where possible
- `--auto` — **auto-chain**: proceed through all remaining stages without stopping at stage boundaries

## --auto chaining behavior

When `--auto` is active (set via flag, `brief.md` auto field, or user instruction), the agent:

1. Writes the required artifact for the current stage
2. Invokes the next stage skill directly in the same turn
3. Continues chaining until the workflow completes or hits an auto-break condition

### Chain sequence by route

| Route | Auto-chain sequence |
|-------|-------------------|
| small | clarify → execute → review → ship → finish |
| medium | clarify → plan → execute → review → ship → finish |
| high | clarify → plan → execute → review(spec) → review(quality) → ship → finish |
| epic | clarify → milestone → plan → execute → review(spec) → review(quality) → ship → finish |

### Auto-break conditions (--auto stops here)

The agent must **stop and wait for user input** when any of these occur, even under `--auto`:

- **Failed verification**: build, lint, type_check, or test failure that the bounded fix loop cannot resolve
- **Blockers**: unresolved open questions or missing dependencies in `brief.md`
- **Review verdict: `changes_requested`**: must present findings and wait for user direction before re-executing
- **Destructive actions**: `finish` discard confirmation, force-push, branch deletion
- **Ambiguous route or scope change**: when the request no longer matches the original brief
- **Missing required artifact**: any mandatory artifact that could not be produced

### --auto does NOT bypass

- Safety confirmations for `--real` external execution
- Discard confirmation in `finish` (always requires exact `discard` input)
- The 4-option choice in `finish` (merge/PR/keep/discard)
- Quality improvement loop-back in `ship` (if issues found, ask before returning to execute)

## General rule

If the user explicitly includes any of the flags above, or says to continue through ForgeFlow stages without further approval, treat that as approval for the current bounded ForgeFlow sequence. This only applies inside the stated task scope and never overrides a blocker, failed verification, missing required artifact, or unsafe/destructive action.
