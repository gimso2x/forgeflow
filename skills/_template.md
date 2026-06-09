---
name: example-skill
description: One sentence describing when to use this skill.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must state the hard constraints an agent must obey when running this skill.
dependencies:
  - skills/_shared/discipline.md
---

# Skill: <name>

One sentence describing what this skill does and why it exists.

> **Router skills only** (`forgeflow`, `clarify`): also add `intent`, `inputs`, and `outputs` to frontmatter. See `skills/forgeflow/SKILL.md` and `scripts/validate_advisory_contract.py`.

## Reference inventory

- references/\<topic\>.md — optional Markdown link row; required for large workflow skills per `docs/skill-modularization.md`.

## Input

| Artifact | Source |
|----------|--------|
| `<input-artifact>.md` | Prior stage or user |

## Output Artifacts

| Artifact | Template | Description |
|----------|----------|-------------|
| `<output-artifact>.md` | `templates/<output-artifact>.md` | What this artifact contains |

> **Read-only utility exception**: `status` prints a report only — no disk artifacts.

## Procedure

1. …

## Constraints

- …

## Exit Condition

- …

## 차단 요소 (Blocked By)

none
