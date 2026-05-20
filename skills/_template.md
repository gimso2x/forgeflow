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

## File write and output discipline

→ Read `_shared/discipline.md` for the common rules.
Skill-specific writing rules go here.

## Constraints

- Hard rules that must not be violated.
- Failure modes and how to handle them.

---

### Optional sections (add when relevant)

- **Trigger** — When the skill should activate (only for entry-point skills like benchmark)
- **Notes** — Design rationale, references to other skills, edge cases
- **Automation / non-interactive approval mode** → `_shared/automation.md`
- **Status analysis preflight** → `_shared/preflight.md`
