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

For exact-count list prompts, output numbered lines only. Do not output a preamble, heading, fenced block, command equivalent, git action, artifact JSON, or final verdict.

Example exact-count response:

```text
1. Confirm the approved README badge change is the only intended ship item.
2. Confirm the final handoff summary names the badge change and any residual risk.
```

No heading. No preamble. No third line.

## Procedure

1. Check git status and diff only if command execution is allowed.
2. Run final verification only if command execution is allowed.
3. Ensure review passed; do not ship blocked work.
4. Prepare commit/PR/handoff summary.
5. Preserve artifacts/evidence instead of burying them in chat.

Never discard or destructive-clean without explicit confirmation.

## Output mode examples

If asked:

```text
/ship Dry run only. List exactly two ship checks. Do not write files. Do not run commands.
```

Return exactly two ship checks. Do not add command equivalents, git actions, artifact writes, or a final verdict unless requested.
