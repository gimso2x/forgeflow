---
name: x-office-hours
description: x-office-hours cross-cutting ForgeFlow skill
validate_prompt: |
  Must reframe the problem before recommending implementation.
  Must surface assumptions, constraints, and simpler alternatives.
  Must not turn the discussion into code changes unless explicitly asked.
---

# Skill: x-office-hours

## Purpose

Reframe the problem before writing code. Six forcing questions that challenge premises and prevent building the wrong thing.

## Trigger

- After `clarify` but before `specify`, especially for large routes.
- User says: `"office hours"`, `"reframe this"`, `"am I building the right thing?"`.

## Input

| Artifact | Source |
|----------|--------|
| `brief.json` | Current Context Brief |
| User request | Original raw input |

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| `brief.json` | Updated with office-hours answers |
| `decision-log.json` | Entry: reframing results, any escalations |

## Execution

Ask these six questions, adapted from the user's goal:

1. **Who is the user?** Be specific. "Developers" is not a user.
2. **What is the user doing right before they need this?** Context matters.
3. **What is the user doing right after?** Handoff matters.
4. **What is the simplest version that still solves the problem?** Cut scope aggressively.
5. **What are you assuming is true that might not be?** Surface hidden dependencies.
6. **What would make this a failure even if the code is perfect?** Business/logic risks.

After the interview, update `brief.json` with:
- `reframed_goal`: The possibly revised goal.
- `scope_cuts`: List of explicitly excluded features.
- `assumptions_validated`: List of assumptions confirmed or flagged.

## Constraints

- This skill can block the pipeline. If the reframed goal contradicts the original, require explicit user confirmation before proceeding.
- Do not skip this for large routes. It prevents multi-day builds of the wrong thing.

## Exit Condition

- All six questions answered and recorded in `brief.json`.
- OR escalation recorded in `decision-log.json` with reason.

## Notes

- This is gstack's `/office-hours` command extracted into a cross-cutting skill.
- Usually adds 5-10 minutes but prevents days of rework.
