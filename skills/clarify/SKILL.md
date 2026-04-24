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

## File write and output discipline

Default to **response-only mode**. Do not call Write/Edit or create artifact files unless the user explicitly asks you to write files or provides a clear writable task directory.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `brief.json`, `plan.json`, or `review-report.json` are mentioned without an explicit writable path, return their content in the chat response as fenced text or concise structured bullets. Do not guess a path in the repository root.

If writing is allowed, write only under the current project workspace or the explicit task directory named by the user. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.

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

## Output mode examples

If asked:

```text
/clarify Add a README badge. Return only the selected route label. Do not write files.
```

Return only one of:

```text
small
medium
large_high_risk
```

No explanation. No JSON. No file writes.
