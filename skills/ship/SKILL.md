---
name: ship
description: Finalize ForgeFlow work after review: summarize, verify, prepare PR/commit handoff, and preserve evidence.
version: 0.1.0
author: gimso2x
---

# Ship

Use this skill to finalize ForgeFlow work after review passes.

## Input

- Approved `review-report.json` or equivalent review verdict
- `run-state.json`
- `plan.json` if available
- Git diff/status
- Verification evidence

## Output Artifacts

- Final summary / ship manifest containing:
  - changed files
  - verification commands and results
  - review verdict
  - residual risks
  - handoff action: commit, PR, keep, or stop

## Exit Condition

- Working tree state is understood
- Final verification is green or failures are explicitly documented
- Review verdict permits shipping
- Commit/PR/handoff is completed if requested
- User gets a concise final report

## Artifact path rule

Artifact names in this skill are workflow contracts. Do not write files inside the plugin installation directory or `skills/<skill>/` directory. If the user asks you to create files, write them in the current project workspace or an explicit task directory. If no writable task directory is clear, return the artifact content in the response instead of guessing a path.

## Procedure

1. Check git status and diff.
2. Run final verification appropriate to the change.
3. Ensure review passed; do not ship blocked work.
4. Prepare commit/PR/handoff summary.
5. Preserve artifacts/evidence instead of burying them in chat.

Never discard or destructive-clean without explicit confirmation.
