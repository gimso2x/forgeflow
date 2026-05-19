---
name: example-skill
description: One sentence describing when to use this skill.
validate_prompt: |
  Must state the hard constraints an agent must obey when running this skill.
---

# Skill: <name>

## Purpose

One sentence describing what this skill does and why it exists.

## Trigger

- When should this skill activate?
- List explicit phrases or conditions.

## Input

| Artifact | Source |
|----------|--------|
| `<input-artifact>.md` | Prior stage or user |

## Output Artifacts

| Artifact | Template | Description |
|----------|----------|-------------|
| `<output-artifact>.md` | `templates/<output-artifact>.md` | What this artifact contains |

## Execution

1. Step one.
2. Step two.
3. Step three.

## Constraints

- Hard rules that must not be violated.
- Failure modes and how to handle them.

## Exit Condition

- What must be true for this skill to be considered complete?
- Include artifact existence checks or state transitions.

## Notes

- Design rationale, references to other skills, edge cases.
