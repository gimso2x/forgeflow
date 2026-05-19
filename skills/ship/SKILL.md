---
name: ship
description: "Finalize ForgeFlow work after review: summarize, verify, prepare PR/commit handoff, and preserve evidence. Use when the user types /forgeflow:ship."
version: 0.1.0
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
  - handoff action: report completed; branch disposition remains pending for `finish`

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
- repo-local `.forgeflow/tasks/<task-id>/` created via `/forgeflow-init` or `python3 scripts/run_orchestrator.py init ...`.

If the task directory is missing, bootstrap or recover it first. Shipping without persisted evidence is how people end up debugging ghosts.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `review-report.json` or final handoff notes are mentioned without an explicit path, preserve them under the active task directory, not the repository root and not chat-only fallback.

If writing is allowed, write only under the current project workspace or the active task directory. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.


## Strict response constraints

When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.

Bad: adding verdicts, JSON artifacts, rationale sections, or extra warnings after the requested list.
Good: if asked for exactly two checks, return exactly two checks.

When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.

For exact-count list prompts, output numbered lines only. Do not output a preamble, heading, fenced block, command equivalent, git action, artifact JSON, or final verdict.

Example exact-count response must be plain text lines, not a fenced block:

1. Confirm the approved README badge change is the only intended ship item.
2. Confirm the final handoff summary names the badge change and any residual risk.

No heading. No preamble. No code fence. No third line.

## Status analysis preflight

Before preparing handoff, read `run-state.json`, latest review report(s), and `eval-record.json` when present. If the workspace has several task dirs, use `python3 scripts/forgeflow_monitor.py --tasks .forgeflow/tasks --recent 10` as read-only status analysis to pick the active task, then verify the exact artifacts yourself.

## Procedure

1. Check git status and diff only if command execution is allowed.
2. Run final verification only if command execution is allowed.
3. Ensure review passed; do not ship blocked work.

### 4. Final Polish & Simplification Loop (Inspired by /simplify)

Before generating the final manifest, perform an iterative refinement loop on the **actually changed code** (`git diff HEAD~1 HEAD` or equivalent) until the delta converges to zero.

#### Principles:
- **Phase 1: Identification**: Focus exclusively on the diff. Ignore noise from unrelated files.
- **Phase 2: Triple-Lens Analysis**:
    - **Lens 1 (Code Reuse)**: Replace new logic with existing utils, constants, or types. Avoid reinventing the wheel.
    - **Lens 2 (Code Quality)**: Eliminate "stringly-typed" code, redundant wrappers, and abstraction boundary violations.
    - **Lens 3 (Efficiency)**: Optimize hot paths, improve concurrency, and remove redundant resource reads (considering Server Component context).
- **Phase 3: Iterative Refinement**:
    - **Converge to Zero**: Repeat the refinement cycle until no further meaningful improvements are identified by the three lenses.
    - **Comment Preservation**: **NEVER delete comments** during simplification. Comments are vital "Why" signals.
    - **False Positive Filtering**: Only apply changes that have clear value "now". Avoid over-engineering for hypothetical future needs.

#### Verification:
- Run focused tests after each refinement cycle to ensure no behavioral regressions.
- If a simplification breaks a test, immediately revert (`git restore`) and skip that specific change.

5. Prepare the final handoff summary.
6. **Update checkpoint.json**: Set `current_stage: "shipped"`, `next_action` to "완료. 후속 작업이 필요하면 새 태스크를 생성하세요.", `open_blockers: []`, and `updated_at` to the current timestamp. This prevents stale checkpoint state from confusing future sessions.
7. Preserve artifacts/evidence instead of burying them in chat.

Never discard, merge, PR, or destructive-clean from `ship`; hand branch disposition to `finish` and require explicit confirmation there.

## Output mode examples

If asked:

```text
/forgeflow:ship Dry run only. List exactly two ship checks. Do not write files. Do not run commands.
```

Return exactly two ship checks. Do not add command equivalents, git actions, artifact writes, or a final verdict unless requested.
