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

## Artifact path rule

Artifact names in this skill are workflow contracts. Do not write files inside the plugin installation directory or `skills/<skill>/` directory. If the user asks you to create files, write them in the current project workspace or an explicit task directory. If no writable task directory is clear, return the artifact content in the response instead of guessing a path.

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
