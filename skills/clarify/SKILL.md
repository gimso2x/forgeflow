---
name: clarify
description: Turn a vague request into a scoped ForgeFlow brief and route decision. Use first for new implementation/refactor/debug requests unless the user already provided a complete brief.
version: 0.1.0
author: gimso2x
---

# Clarify

Use this skill to convert a raw request into a ForgeFlow `brief.json`-style context brief and route decision.

## Input

- Raw user request
- Target repository/path if known
- Constraints, acceptance criteria, risk notes if provided
- Existing codebase context if available

## Output Artifacts

- `brief.json` or equivalent brief containing:
  - goal
  - constraints
  - acceptance criteria
  - scope boundary
  - open questions
  - complexity score
  - route: `small`, `medium`, or `large_high_risk`

## Exit Condition

- The request has a clear goal and scope boundary
- Open questions are either answered or explicitly listed
- A route is selected and justified
- Next skill is named:
  - `small` -> `/run` or direct execute path
  - `medium` -> `/plan`
  - `large_high_risk` -> `/plan` with spec/quality review kept separate

## Artifact path rule

Artifact names in this skill are workflow contracts. Do not write files inside the plugin installation directory or `skills/<skill>/` directory. If the user asks you to create files, write them in the current project workspace or an explicit task directory. If no writable task directory is clear, return the artifact content in the response instead of guessing a path.

## Procedure

1. Ask at most 3 clarifying questions. Ask 0 if the request is already clear.
2. Inspect relevant repo context before inventing scope.
3. Score complexity:
   - 5-8: `small`
   - 9-12: `medium`
   - 13-15: `large_high_risk`
4. State the route and why.
5. Produce the brief in a structured form the next skill can consume.

Do not implement here. Clarify is the intake gate, not the coding phase.
