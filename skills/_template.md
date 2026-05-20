---
name: example-skill
description: One sentence describing when to use this skill.
validate_prompt: |
  Must state the hard constraints an agent must obey when running this skill.
---

# Skill: <name>

One sentence describing what this skill does and why it exists.

## Input

| Artifact | Source |
|----------|--------|
| `<input-artifact>.md` | Prior stage or user |

## Output Artifacts

| Artifact | Template | Description |
|----------|----------|-------------|
| `<output-artifact>.md` | `templates/<output-artifact>.md` | What this artifact contains |

## Procedure

1. Step one.
2. Step two.
3. Step three.

## Exit Condition

- What must be true for this skill to be considered complete?
- Include artifact existence checks or state transitions.

## Constraints

Skill-specific hard rules and failure modes. Shared constraint sections may appear at the top level (see below) or nested under this header — either is valid as long as every constraint is reachable.

### Optional constraint sections (add when relevant)

- **File write and output discipline** → `_shared/discipline.md`
- **Strict response constraints** → `_shared/discipline.md`
- **Automation / non-interactive approval mode** → `_shared/automation.md`
- **Status analysis preflight** → `_shared/preflight.md`

---

### Optional sections (add when relevant)

- **Trigger** — When the skill should activate (only for entry-point skills like benchmark)
- **Notes** — Design rationale, references to other skills, edge cases
