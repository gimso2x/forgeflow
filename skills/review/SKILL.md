---
name: review
description: Perform independent ForgeFlow review against requirements, plan, and code. Use when the user types /forgeflow:review, after /forgeflow:execute and before /forgeflow:ship.
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must separate spec compliance findings from quality findings.
  Must not approve work with unresolved blockers or missing verification evidence.
---

# Review

Use this skill to review completed ForgeFlow work independently.

## Input

- `brief.md` from clarify stage
- `plan.md` from plan stage
- `implementation-notes.md` from execute stage
- `requirements.md` if available
- Final codebase state
- Verification commands/results

## Output Artifacts

Write `review-report.md` to the active task directory using `templates/review-report.md` as the structure. The report must capture:

- Review Type (spec | quality | security | ux)
- Verdict (approved | changes_requested | blocked) — never use "passed"
- Reviewer (role or identifier)
- Findings with severity (blocker | major | minor | nit) and category (spec-compliance | quality | maintainability | risk | security)
- Spec Compliance checklist (for spec review)
- Quality Assessment checklist (for quality review)
- Open Blockers (list or "none")
- Safe for Next Stage (yes | no)
- Next Action
- Approved By (only if verdict is approved)

## Review Rubrics

These rubrics are applied directly during review. Separate spec and quality reviews use their respective rubrics.

### Spec Review

Questions to answer for every spec review:
- Did the output satisfy the brief objective?
- Were acceptance criteria met?
- Did execution stay inside scope?
- Did the change avoid silent fallback, dual write, or shadow-path ownership drift?
- Is evidence sufficient for the claimed completion?

Automatic fail conditions:
- Missing acceptance coverage
- Unapproved scope drift
- Silent fallback or dual-write drift
- Evidence-free completion claim
- Approved verdict with open blockers or safe_for_next_stage=false

### Quality Review

Questions to answer for every quality review:
- Is the result simple enough?
- Is the verification quality acceptable?
- Are residual risks documented?
- Is maintainability acceptable for the task size?
- Was this the smallest safe change without alternate ownership paths?

Automatic fail conditions:
- Avoidable complexity
- Weak verification
- Hidden residual risk
- Shadow-path ownership drift
- Approved verdict with open blockers or safe_for_next_stage=false

## Exit Condition

- Requirements/acceptance criteria are checked against actual files
- Tests/build/lint are considered or run where appropriate
- Critical/major findings block ship
- `review-report.md` has been written to the active task directory **before** the exit summary
- Approved review has no open blockers and is safe for next stage
- Next step is `/forgeflow:ship` only if review passes

A review that leaves no `review-report.md` is incomplete. The verdict exists only in the artifact, not in chat sentiment.

### Route-aware review behavior

- **small** route: Single quality review. Write `review-report.md` with Review Type: quality.
- **medium** route: Single quality review. Write `review-report.md` with Review Type: quality.
- **high/epic** route: Two separate reviews are **required**:
  1. `/forgeflow:review --type spec` — Write `review-report-spec.md` with Review Type: spec.
  2. `/forgeflow:review --type quality` — Write `review-report-quality.md` with Review Type: quality.

  For high/epic, if `review-report-spec.md` does not exist or has verdict != approved, do not proceed to quality review. Each review is an independent gate.

## File write and output discipline

Default to **artifact-first mode**. Write `review-report.md` under `.forgeflow/tasks/<task-id>/` unless the user explicitly asks for a dry run, exact-output response, or no-write simulation.

If the task directory is missing, bootstrap or recover it first. A review that leaves no artifact is just vibes with punctuation.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

Write only under the current project workspace or the active task directory. Never write inside `skills/<skill>/`.

## Strict response constraints

When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.

When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.

For exact-count list prompts, output numbered lines only. No preamble, heading, fenced block, verdict, or extra commentary.

## Evidence discipline

Review evidence is not fan fiction. Use a blocker-first verdict: unresolved blocker, missing required artifact, failed required verification, or uninspected claimed evidence prevents approval before any quality praise matters.

- Claim only what you directly observed in this review turn or what is explicitly present in provided artifacts.
- If a worker, previous assistant, or user says a command passed, cite it explicitly with the phrase `reported evidence` unless you personally ran or inspected the command output in this turn.
- Use `observed evidence` only for command outputs, artifacts, files, or diffs you directly inspected in this review turn.
- Do not say lint/build/tests/dev-server/runtime verification passed unless you ran the command or inspected the concrete captured output.
- If verification is missing, blocked, or only reported second-hand, mark it as missing or reported; do not convert it into approval-grade evidence.
- Evidence refs must name concrete files, command outputs, diffs, or user-provided artifacts. Avoid vague refs like "verified behavior".
- Referenced repository paths must exist in the reviewed diff/worktree unless explicitly labeled as planned, missing, or user-provided hypothetical paths.
- Do not approve a review that treats nonexistent files, commands, or evidence refs as observed facts. Path hallucination is a blocker, not a typo.
- When command execution is disallowed, use manual inspection language only: "not run", "manual inspection", "requires verification".

## Consistency check

Before approving, check whether the work kept instructions, tools, environment, state, and feedback consistent across artifacts and code. Requirement/contract drift, nonexistent verification tools, ignored environment blockers, stale artifacts, or unclosed feedback from failures are review findings. Label verification evidence as observed, reported, or missing before deciding whether it can support approval.

## Test verification gate

Review MUST independently verify test results before approving. This is a hard gate:

1. **Run the test suite yourself.** Do not trust worker-reported pass/fail counts. Execute `npm test`, `pytest`, `make test`, or whatever test command is appropriate for the project.
2. **Parse the output.** If any test fails, the review verdict MUST be `changes_requested` — never `approved`.
3. **Record evidence.** Include the test command, total count, pass count, and fail count in findings.
4. **Flaky test disclaimer.** If tests are flaky and fail intermittently, run them once more. If they still fail, they fail. A flaky test failure is still a failure for review purposes.
5. **No test command found.** If no test command exists or tests cannot be run, record this as `reported evidence: no test command found` and note it as a minor finding. Do not treat this as a blocker, but do not claim tests pass.

This gate applies regardless of route size. Even small-route reviews must run tests if a test command is available.

## Git safety summary

- Name the exact diff scope reviewed: files, directories, commit range, or staged changes.
- Name verification evidence: commands run, artifacts inspected, or missing evidence.
- Treat broad staging, destructive git actions, and dirty unrelated user work as review risks unless explicitly justified and approved.

## Automation / non-interactive approval mode

If the user explicitly includes `--yes`, `--auto-approve`, `--non-interactive`, or says to continue through ForgeFlow stages without further approval, treat that as approval for the current bounded ForgeFlow sequence. Do not pause at the normal stage-boundary y/n prompt; proceed to the next requested ForgeFlow stage after writing the required artifact for the current stage. This only applies inside the stated task scope and never overrides a blocker, failed verification, missing required artifact, or unsafe/destructive action.

## Status analysis preflight

Before reviewing, reconstruct the task state from artifacts instead of chat memory:

- Read `implementation-notes.md` for current stage/status, decisions, deviations, progress, evidence, and blockers.
- Read `plan.md` to confirm planned tasks, requirements, contracts, and verification plan.
- Read `brief.md` for route, scope, acceptance criteria, and constraints.

## Procedure

1. Read `brief.md` to determine route and expected review scope.
2. Review from artifacts and code, not worker vibes.
3. Check scope coverage and acceptance criteria, including every fulfills, journey, and verification plan target from the plan.
4. Start with blocker elimination: missing artifacts, missing observed evidence, failed verification, or unresolved open blockers force `blocked` or `changes_requested` before minor findings are considered.
5. **Run the test suite** (see Test verification gate above). If any test fails, verdict MUST be `changes_requested`.
6. Run or inspect other verification (lint, type check, build) if the user allowed command execution.
7. Separate observed evidence from reported or missing evidence before choosing a verdict.
8. **Review implementation-notes.md**: Check every recorded deviation and open question:
    - Each deviation must be justified. Unjustified deviations are scope drift.
    - Open questions with status `open` are blockers until resolved.
    - Tradeoffs should be evaluated: was the chosen alternative the smallest safe option?
    - If `implementation-notes.md` is missing entirely, note it as a minor finding (the execute stage should have created it).
9. Apply the appropriate review rubric (Spec or Quality — see Review Rubrics section above). For quality review, also apply these discipline heuristics:
   - Every changed line should trace directly to the user's request; anything else needs explicit scope approval.
   - Flag drive-by refactors, speculative abstractions, or unrelated cleanup as scope drift unless the plan explicitly authorized them.
   - Was the change the smallest safe change that satisfies the request?
   - **Architectural Depth**: Did the implementation introduce shallow modules (pass-throughs) or miss deepening opportunities? Does the new structure improve locality and leverage?
   - Did the change avoid silent fallback, dual write, and shadow-path ownership drift?
   - Did the implementation follow existing codebase patterns instead of inventing a new local religion?
   - Were assumptions about types, APIs, behavior, and test coverage verified against actual files?
   - If performance was touched, was the bottleneck measured before and after the change?
10. Classify findings by severity: blocker, major, minor, nit.
11. **Write `review-report.md`** (or `review-report-spec.md` / `review-report-quality.md` for high/epic) to the active task directory. The verdict in the file is the only valid verdict.
12. Return a clear verdict in chat that matches the file. If verdict is `changes_requested` or `blocked`, update `implementation-notes.md` so status reflects the review gate.
13. **다음 단계 안내** — 반드시 사용자에게 출력:
    - If `approved`: "리뷰 통과. 출하 준비 완료. `/forgeflow:ship`을 실행해주세요."
    - If `changes_requested`: "수정이 필요합니다:" + 각 P0/P1 이슈를 `file:line — description` 형태로 나열 + "`/forgeflow:execute`로 수정 후 다시 `/forgeflow:review`를 요청해주세요."
    - Do NOT auto-proceed to ship. 반드시 사용자가 다음 단계를 실행하도록 대기.
14. Do not call `/forgeflow:ship` unless verdict=approved, safe_for_next_stage=yes, and open_blockers=none are all true in the **written** `review-report.md`.

Do not merge spec-review and quality-review for high/epic work.

## Output mode examples

If asked:

```text
/forgeflow:review Dry run only. List exactly two review checks. Do not write files. Do not run commands.
```

Return exactly two review checks. Do not add a verdict, extra commentary, or file writes.
