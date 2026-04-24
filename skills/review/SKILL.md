---
name: review
description: Perform independent ForgeFlow review against requirements, plan, and code. Use after /run before /ship.
version: 0.1.0
author: gimso2x
---

# Review

Use this skill to review completed ForgeFlow work independently.

## Input

- `brief.json`
- `requirements.md` if available
- `plan.json` if available
- Final codebase state
- Verification commands/results

## Output Artifacts

- `review-report.json` or equivalent review report containing:
  - review type: quality or spec as appropriate
  - verdict
  - findings by severity
  - blocker list
  - evidence references
  - `safe_for_next_stage`

## Exit Condition

- Requirements/acceptance criteria are checked against actual files
- Tests/build/lint are considered or run where appropriate
- Critical/major findings block ship
- Approved review has no open blockers and is safe for next stage
- Next step is `/ship` only if review passes

## File write and output discipline

Default to **response-only mode**. Do not call Write/Edit or create artifact files unless the user explicitly asks you to write files or provides a clear writable task directory.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `brief.json`, `plan.json`, or `review-report.json` are mentioned without an explicit writable path, return their content in the chat response as fenced text or concise structured bullets. Do not guess a path in the repository root.

If writing is allowed, write only under the current project workspace or the explicit task directory named by the user. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.


## Strict response constraints

When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.

Bad: adding verdicts, JSON artifacts, rationale sections, or extra warnings after the requested list.
Good: if asked for exactly two checks, return exactly two checks.

When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.

For exact-count list prompts, output numbered lines only. Do not output a preamble, heading, fenced block, verdict, artifact JSON, explanatory paragraph, or empty response. If the prompt gives only a hypothetical diff/task, still return the requested review checks as generic checks for that scenario.

Example exact-count response must be plain text lines, not a fenced block:

1. Check that the README badge markdown matches the requested badge label and target URL.
2. Check that the README badge change does not alter unrelated README content.

No heading. No preamble. No code fence. No third line.

## Procedure

1. Review from artifacts and code, not worker vibes.
2. Check scope coverage and acceptance criteria.
3. Run or inspect verification only if the user allowed command execution.
4. Classify findings: critical, major, minor, info.
5. Return a clear verdict unless the user asked for a narrower output.

Do not merge spec-review and quality-review for large/high-risk work.

## Output mode examples

If asked:

```text
/review Dry run only. List exactly two review checks. Do not write files. Do not run commands.
```

Return exactly two review checks. Do not add a verdict, artifact JSON, or extra commentary.
