---
name: review
description: Perform independent ForgeFlow review against requirements, plan, and code. Use after /forgeflow:run before /forgeflow:ship.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must separate spec compliance findings from quality findings.
  Must not approve work with unresolved blockers or missing verification evidence.
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

When writing `review-report.json`, it **must** conform to `schemas/review-report.schema.json` exactly:

```json
{
  "schema_version": "0.1",
  "task_id": "readme-badge-task",
  "review_type": "quality",
  "verdict": "approved",
  "findings": ["No blockers found in the hypothetical README badge diff."],
  "approved_by": "forgeflow-review",
  "next_action": "Proceed to /forgeflow:ship.",
  "safe_for_next_stage": true,
  "open_blockers": [],
  "evidence_refs": ["hypothetical README badge diff"]
}
```

Do not add non-schema fields such as `findings_by_severity`, `blocker_list`, or `evidence_references`. Use verdict values exactly: `approved`, `changes_requested`, or `blocked`; never `passed`.

## Exit Condition

- Requirements/acceptance criteria are checked against actual files
- Tests/build/lint are considered or run where appropriate
- Critical/major findings block ship
- Approved review has no open blockers and is safe for next stage
- Next step is `/forgeflow:ship` only if review passes

## File write and output discipline

Default to **artifact-first mode**. Review should write `review-report.json` under the active task directory unless the user explicitly asks for a dry run, exact-output response, or no-write simulation.

Canonical writable location:

- explicit task directory provided by the user, or
- repo-local `.forgeflow/tasks/<task-id>/` created via `/forgeflow:init` or `python3 scripts/run_orchestrator.py init ...`.

If the task directory is missing, bootstrap or recover it first. A review that leaves no artifact is just vibes with punctuation.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `review-report.json` are mentioned without an explicit path, write them to the active task directory, not the repository root and not chat-only fallback.

If writing is allowed, write only under the current project workspace or the active task directory. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.


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

## Evidence discipline

Review evidence is not fan fiction.

- Claim only what you directly observed in this review turn or what is explicitly present in provided artifacts.
- If a worker, previous assistant, or user says a command passed, cite it as reported evidence unless you personally ran or inspected the command output in this turn.
- Do not say lint/build/tests/dev-server/runtime verification passed unless you ran the command or inspected the concrete captured output.
- If verification is missing, blocked, or only reported second-hand, mark it as missing or reported; do not convert it into approval-grade evidence.
- `evidence_refs` must name concrete files, command outputs, diffs, or user-provided artifacts. Avoid vague refs like "verified behavior".
- When command execution is disallowed, use manual inspection language only: "not run", "manual inspection", "requires verification".

## Git safety summary

`docs/review-model.md owns git-safety policy`. Do not redefine git safety in this skill; apply that model during review.

- Name the exact diff scope reviewed: files, directories, commit range, or staged changes.
- Name verification evidence: commands run, artifacts inspected, or missing evidence.
- Treat broad staging, destructive git actions, and dirty unrelated user work as review risks unless explicitly justified and approved.

## Procedure

1. Review from artifacts and code, not worker vibes.
2. Check scope coverage and acceptance criteria.
3. Run or inspect verification only if the user allowed command execution.
4. Separate observed evidence from reported or missing evidence before choosing a verdict.
5. For quality review, apply discipline heuristics without creating a separate stage:
   - Every changed line should trace directly to the approved request.
   - Was the change the smallest safe change that satisfies the request?
   - Did the change avoid silent fallback, dual write, and shadow-path ownership drift?
   - Did the implementation follow existing codebase patterns instead of inventing a new local religion?
   - Were assumptions about types, APIs, behavior, and test coverage verified against actual files?
   - If performance was touched, was the bottleneck measured before and after the change?
6. Classify findings: critical, major, minor, info.
7. Return a clear verdict unless the user asked for a narrower output.

Do not merge spec-review and quality-review for large/high-risk work.

## Output mode examples

If asked:

```text
/forgeflow:review Dry run only. List exactly two review checks. Do not write files. Do not run commands.
```

Return exactly two review checks. Do not add a verdict, artifact JSON, or extra commentary.
