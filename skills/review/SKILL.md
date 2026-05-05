---
name: review
description: Perform independent ForgeFlow review against requirements, plan, and code. Use when the user types /forgeflow:review, after /forgeflow:run and before /forgeflow:ship.
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
- `review-report.json` has been written to the active task directory **before** the exit summary
- Approved review has no open blockers and is safe for next stage
- Next step is `/forgeflow:ship` only if review passes

A review that leaves no `review-report.json` is incomplete. The verdict exists only in the artifact, not in chat sentiment.

### Route-aware review behavior

- **small** route: Single quality review. Write `review-report.json` with `review_type: "quality"`.
- **medium** route: Single quality review. Write `review-report.json` with `review_type: "quality"`.
- **large_high_risk** route: Two separate reviews are **required**:
  1. `/forgeflow:review` (spec) — Write `review-report-spec.json` with `review_type: "spec"`.
  2. `/forgeflow:review` (quality) — Write `review-report-quality.json` with `review_type: "quality"`.

  For large_high_risk, if `review-report-spec.json` does not exist or has `verdict != "approved"`, do not proceed to quality review. Each review is an independent gate.

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
- If a worker, previous assistant, or user says a command passed, cite it explicitly with the phrase `reported evidence` unless you personally ran or inspected the command output in this turn.
- Use `observed evidence` only for command outputs, artifacts, files, or diffs you directly inspected in this review turn.
- Do not say lint/build/tests/dev-server/runtime verification passed unless you ran the command or inspected the concrete captured output.
- If verification is missing, blocked, or only reported second-hand, mark it as missing or reported; do not convert it into approval-grade evidence.
- `evidence_refs` must name concrete files, command outputs, diffs, or user-provided artifacts. Avoid vague refs like "verified behavior".
- Referenced repository paths must exist in the reviewed diff/worktree unless explicitly labeled as planned, missing, or user-provided hypothetical paths.
- Do not approve a review that treats nonexistent files, schemas, commands, or evidence refs as observed facts. Path hallucination is a blocker, not a typo.
- When command execution is disallowed, use manual inspection language only: "not run", "manual inspection", "requires verification".

## Test verification gate

Review MUST independently verify test results before approving. This is a hard gate:

1. **Run the test suite yourself.** Do not trust worker-reported pass/fail counts. Execute `npm test`, `pytest`, `make test`, or whatever test command is appropriate for the project.
2. **Parse the output.** If any test fails, the review verdict MUST be `changes_requested` — never `approved`.
3. **Record evidence.** Include the test command, total count, pass count, and fail count in `evidence_refs` and `findings`.
4. **Flaky test disclaimer.** If tests are flaky and fail intermittently, run them once more. If they still fail, they fail. A flaky test failure is still a failure for review purposes.
5. **No test command found.** If no test command exists or tests cannot be run, record this as `reported evidence: no test command found` and note it as a minor finding. Do not treat this as a blocker, but do not claim tests pass.

This gate applies regardless of route size. Even small-route reviews must run tests if a test command is available.

## Git safety summary

`docs/review-model.md owns git-safety policy`. Do not redefine git safety in this skill; apply that model during review.

- Name the exact diff scope reviewed: files, directories, commit range, or staged changes.
- Name verification evidence: commands run, artifacts inspected, or missing evidence.
- Treat broad staging, destructive git actions, and dirty unrelated user work as review risks unless explicitly justified and approved.


## Automation / non-interactive approval mode

If the user explicitly includes `--yes`, `--auto-approve`, `--non-interactive`, or says to continue through ForgeFlow stages without further approval, treat that as approval for the current bounded ForgeFlow sequence. Do not pause at the normal stage-boundary y/n prompt; proceed to the next requested ForgeFlow stage after writing the required artifact for the current stage. This only applies inside the stated task scope and never overrides a blocker, failed verification, missing required artifact, or unsafe/destructive action.

## Procedure

1. Read `brief.json` to determine route and expected review scope.
2. Review from artifacts and code, not worker vibes.
3. Check scope coverage and acceptance criteria.
4. **Run the test suite** (see Test verification gate above). If any test fails, verdict MUST be `changes_requested`.
5. Run or inspect other verification (lint, type check, build) if the user allowed command execution.
6. Separate observed evidence from reported or missing evidence before choosing a verdict.
7. **Check for stuck signals**: review `decision-log.json` for entries with actor `stuck-detector` or category `escalation`. If the worker hit a stuck condition but continued editing anyway, that's a major finding — the worker ignored an escalation signal.
8. For quality review, apply discipline heuristics without creating a separate stage:
   - Every changed line should trace directly to the approved request.
   - Was the change the smallest safe change that satisfies the request?
   - Did the change avoid silent fallback, dual write, and shadow-path ownership drift?
   - Did the implementation follow existing codebase patterns instead of inventing a new local religion?
   - Were assumptions about types, APIs, behavior, and test coverage verified against actual files?
   - If performance was touched, was the bottleneck measured before and after the change?
9. Classify findings: critical, major, minor, info.
10. **Write `review-report.json`** (or `review-report-spec.json` / `review-report-quality.json` for large_high_risk) to the active task directory. The verdict in the file is the only valid verdict.
11. Return a clear verdict in chat that matches the file. If verdict is `changes_requested` or `blocked`, update `run-state.json` in the active task directory so status reflects the review gate, for example `review_blocked`.
12. Do not call `/forgeflow:ship` unless `verdict=approved`, `safe_for_next_stage=true`, and `open_blockers=[]` are all true in the **written** `review-report.json`.

Do not merge spec-review and quality-review for large/high-risk work.

## Output mode examples

If asked:

```text
/forgeflow:review Dry run only. List exactly two review checks. Do not write files. Do not run commands.
```

Return exactly two review checks. Do not add a verdict, artifact JSON, or extra commentary.
