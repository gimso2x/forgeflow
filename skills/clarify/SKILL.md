---
name: clarify
description: Turn a vague request into a scoped ForgeFlow brief and route decision. Use first for new implementation/refactor/debug requests unless the user already provided a complete brief.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must return a clear route or brief artifact only when the prompt asks for it.
  Must not write files unless the user provides an explicit writable task directory.
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
  - non-blocking unknowns / bounded assumptions
  - complexity score
  - route: `small`, `medium`, or `large_high_risk`

## Exit Condition

- The request has a clear goal and scope boundary
- True blocker questions are answered; non-blocking unknowns are recorded as bounded assumptions
- A route is selected and justified
- Next skill is named:
  - `small` -> `/forgeflow:run` or direct execute path
  - `medium` -> `/forgeflow:plan`
  - `large_high_risk` -> `/forgeflow:plan` with spec/quality review kept separate

## File write and output discipline

Default to **response-only mode**. Do not call Write/Edit or create artifact files unless the user explicitly asks you to write files or provides a clear writable task directory.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `brief.json`, `plan.json`, or `review-report.json` are mentioned without an explicit writable path, return their content in the chat response as fenced text or concise structured bullets. Do not guess a path in the repository root.

If writing is allowed, write only under the current project workspace or the explicit task directory named by the user. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.


## Strict response constraints

When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.

If the user asks for a label-only route selection (for example "Return only the selected route label", "label only", or "route label only"), output exactly one of `small`, `medium`, or `large_high_risk`. Do not add route rationale, headings, JSON, Markdown, or even a friendly sentence. One token-ish label. That's it.

Bad: adding verdicts, JSON artifacts, rationale sections, or extra warnings after the requested list.
Good: if asked for exactly two checks, return exactly two checks.

When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.

## Procedure

1. Inspect relevant repo context before inventing scope.
2. Ask up to 5 clarifying questions when they materially improve requirements. Ask 0 if the request is already actionable, and do not pad the list with nice-to-have trivia.
   - Good questions resolve product behavior, user/audience, success criteria, data/source of truth, rollout/risk constraints, or explicit out-of-scope boundaries.
   - Bad questions ask for implementation chores the agent should infer from repo inspection, preferences that do not change the plan, or confirmations that can be recorded as bounded assumptions.
3. Score complexity:
   - 5-8: `small` — one localized change, usually 1-2 files, low ambiguity, no cross-cutting behavior.
   - 9-12: `medium` — several coordinated files/components, shared state/layout/navigation, moderate test/update surface, but no security/data migration/infra rollback risk.
   - 13-15: `large_high_risk` — auth/security, data migration, payments, production infra, irreversible data changes, broad architecture migration, or many contracts/journeys requiring separate spec and quality review.
4. State the route and why, unless an exact-output/label-only instruction applies.
5. Produce the brief in a structured form the next skill can consume, unless an exact-output/label-only instruction applies.
6. If the request is actionable, record remaining non-blocking unknowns as bounded assumptions and make the next stage obvious without asking the user to do your planning work, unless an exact-output/label-only instruction applies.

Do not implement here. Clarify is the intake gate, not the coding phase.

## UX guardrails

- Do repo inspection before saying the scope is unclear.
- Do not manufacture open questions just to prolong intake; `non-blocking unknowns` are artifact notes, not questions the user must answer.
- Do not ask the user to write the plan for you.
- Do not ask the user to approve the brief content again when the request is already sufficient.
- Do stop at the stage boundary before starting `/forgeflow:plan` or `/forgeflow:run`.
- When the request is already sufficient, end with a closed next-stage question: `요구사항 충분. medium route입니다. 다음 스텝으로 `/forgeflow:plan`을 진행하시겠습니까? (y/n)`
- Bad: `route=medium. plan 직행.`
- Good: `요구사항 충분. medium route입니다. 다음 스텝으로 `/forgeflow:plan`을 진행하시겠습니까? (y/n)`

## Output mode examples

If asked:

```text
/forgeflow:clarify Add a README badge. Return only the selected route label. Do not write files.
```

Return only one of:

```text
small
medium
large_high_risk
```

No explanation. No JSON. No file writes.
