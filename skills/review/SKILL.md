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

## Procedure

1. Review from artifacts and code, not worker vibes.
2. Check scope coverage and acceptance criteria.
3. Run or inspect verification.
4. Classify findings: critical, major, minor, info.
5. Return a clear verdict:
   - approved
   - approved_with_minor
   - needs_fix
   - needs_clarification

Do not merge spec-review and quality-review for large/high-risk work.
