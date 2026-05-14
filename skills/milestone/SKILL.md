---
name: milestone
description: Create and manage hierarchical milestones for a project. Use when the user types /forgeflow:milestone.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must expose milestone creation and status tracking.
  Must enforce milestone schema output.
---

# Milestone

## Purpose

Manage large projects by breaking them down into hierarchical milestones and tracking progress. Absorbs GSD's `/gsd:new-milestone` and `/gsd:progress` concepts.

## Trigger

- When the user types `/forgeflow:milestone`, `/forgeflow:milestone new`, or `/forgeflow:milestone progress`.
- When a task is too large and needs to be split into multiple phases (M1, M2, etc.).

## Input

| Artifact | Source |
|----------|--------|
| `brief.json` | Active task workspace |
| `roadmap.json` | (Optional) Active task workspace |

## Output Artifacts

| Artifact | Schema | Description |
|----------|--------|-------------|
| `roadmap.json` | `schemas/milestone.schema.json` | The overarching milestone definitions and statuses. |

## Execution

1. Analyze the project objective and complexity.
2. If creating a new milestone, break down the objective into logical, sequential phases (e.g., M1: MVP, M2: Scale).
3. Write the milestones to `roadmap.json` conforming to `schemas/milestone.schema.json`.
4. If tracking progress, read `roadmap.json` and `run-state.json` to report the current completion percentage and the next actionable phase.

## Constraints

- Do not write code during the milestone phase.
- Ensure all milestone tasks have clear definitions and map to future ForgeFlow tasks.
- If a roadmap already exists, update the status instead of overwriting unless requested.

## Exit Condition

- `roadmap.json` is created or updated in the active task directory.
- The user is presented with a clear summary of the milestones and asked for approval to proceed to planning the first milestone.

## Notes

- Absorbs the core value of GSD into ForgeFlow for tracking Epic-level tasks.