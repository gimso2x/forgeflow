---
name: ship
description: "Finalize ForgeFlow work after review: summarize, verify, prepare PR/commit handoff, and preserve evidence. Use when the user types /ship or /forgeflow:ship."
version: 0.2.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must confirm review approval, intended diff scope, and final verification before shipping.
  Must not hide residual risks or unrelated dirty working tree changes.
---

# Ship

Use this skill to prepare the final handoff after review passes.

`ship` does not merge, discard, clean up, or decide branch disposition. Use `finish` for branch disposition after the user gives explicit direction.

## Input

- Approved `review-report.md` or equivalent review verdict
- `brief.md` if available
- `plan.md` if available
- Git diff/status
- Verification evidence

## Output Artifacts

Write a `ship-summary.md` in the active task directory using `templates/ship-summary.md` as the structure. The summary must capture:

- Changed files
- Verification commands and results
- Review verdict
- Residual risks
- Handoff action: report completed; branch disposition remains pending for `finish`

## Exit Condition

- Working tree state is understood
- Final verification is green or failures are explicitly documented
- Review verdict permits shipping
- Final handoff is completed
- User gets a concise final report

## File write and output discipline

Default to **artifact-first mode**. Ship should preserve the final handoff evidence in the active task directory unless the user explicitly asks for a dry run, exact-output response, or no-write simulation.

Canonical writable location:

- explicit task directory provided by the user, or
- repo-local `.forgeflow/tasks/<task-id>/`

If the task directory is missing, bootstrap or recover it first. Shipping without persisted evidence is how people end up debugging ghosts.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `review-report.md` or final handoff notes are mentioned without an explicit path, preserve them under the active task directory, not the repository root and not chat-only fallback.

If writing is allowed, write only under the current project workspace or the active task directory. Never write inside the plugin installation directory, marketplace cache (including `.claude/plugins/cache`, `.codex/plugins`, `.cursor/plugins`, or `~/.cursor/plugins/local`), or `skills/<skill>/`.

## Strict response constraints

When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.

Bad: adding verdicts, extra rationale sections, or warnings after the requested list.
Good: if asked for exactly two checks, return exactly two checks.

When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.

For exact-count list prompts, output numbered lines only. Do not output a preamble, heading, fenced block, command equivalent, git action, or final verdict.

Example exact-count response must be plain text lines, not a fenced block:

1. Confirm the approved README badge change is the only intended ship item.
2. Confirm the final handoff summary names the badge change and any residual risk.

No heading. No preamble. No code fence. No third line.

## Status analysis preflight

Before preparing handoff, read the latest `review-report.md`, `brief.md`, and `eval-record.md` when present from the active task directory. Identify the active task by inspecting `.forgeflow/tasks/` directories and finding the one with the most recent artifacts.

## Procedure

1. Check git status and diff only if command execution is allowed.
2. Run final verification only if command execution is allowed.
3. Ensure review passed; do not ship blocked work.
4. Confirm there is no unresolved blocker, and that handoff evidence is preserved in the active task directory before preparing the final summary.

5. **Final Polish and Simplification Loop**: Analyze the **actually changed code** (`git diff HEAD~1 HEAD` or equivalent) for quality before shipping. This is a read-first analysis: if modifications are needed, hand back to execute rather than editing code during ship.

#### Analysis (read-only)

- **Phase 1: Identification**: Focus exclusively on the diff. Ignore noise from unrelated files.
- **Phase 2: Triple-Lens Analysis**:
    - **Lens 1 (Code Reuse)**: Identify new logic that duplicates existing utils, constants, or types.
    - **Lens 2 (Code Quality)**: Identify stringly-typed code, redundant wrappers, and abstraction boundary violations.
    - **Lens 3 (Efficiency)**: Identify hot-path inefficiencies, missed concurrency, and redundant resource reads.

#### If issues found

If the Triple-Lens analysis identifies meaningful improvements:
- Record each finding in `ship-summary.md` under a "Simplification candidates" section.
- Ask the user: "품질 개선 후보가 발견되었습니다. `/forgeflow:execute`로 돌아가 수정하시겠습니까? (y/n)"
- Do NOT modify code during ship. Ship is verification + handoff, not implementation.

#### If no issues found

Proceed to step 6 directly.

6. Write `ship-summary.md` to the active task directory.
7. Preserve artifacts/evidence instead of burying them in chat.

Never discard, merge, PR, or destructive-clean from `ship`; hand branch disposition to `finish` and require explicit confirmation there.

## Output mode examples

If asked:

```text
/forgeflow:ship Dry run only. List exactly two ship checks. Do not write files. Do not run commands.
```

Return exactly two ship checks. Do not add command equivalents, git actions, artifact writes, or a final verdict unless requested.
