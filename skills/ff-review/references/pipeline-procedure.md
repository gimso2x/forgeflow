# Review Pipeline Procedure

Use this reference from `skills/ff-review/SKILL.md` for post-execute review. Keep review read-only: findings that require code or product changes must be recorded and handed back to execute.

## Steps

1. Read `checkpoint.md` when present, then `_shared/preflight.md` minimum read set. Read `brief.md` Acceptance Criteria and route; expand only when scope is disputed.
2. Review from artifacts and code, not worker self-report.
3. Check scope coverage and acceptance criteria, including every fulfills, journey, and verification plan target from the plan.
4. **Scope Boundary Verification**: read `scope_boundary` from `brief.md`, identify actually modified files, compare planned vs actual, and check route threshold. Record violations in `review-report.md` frontmatter `scope_boundary` field.
5. **Plan Conformance Gate**: verify every non-skipped, non-deferred task in `plan.md` against execution evidence.
6. Start with blocker elimination: missing artifacts, missing observed evidence, failed verification, or unresolved open blockers force `blocked` or `changes_requested` before minor findings.
7. **Run independent verification**. For small routes, run the fastest relevant observed gate; if cheap tests exist for changed behavior, run them. If any selected gate fails, verdict must be `changes_requested`.
8. Run or inspect other verification (lint, type check, build) when command execution is allowed.
9. Separate observed evidence from reported or missing evidence before choosing a verdict.
10. Review `implementation-notes.md`: deviations need justification; open questions with status `open` are blockers; evaluate whether tradeoffs are the smallest safe option.
11. Cross-check `ledger.md`: claimed task completions in implementation-notes must match ledger status. For high/epic, a `done` step without expected `micro_spec:PASS` is a major spec-compliance finding.
12. Fill `review-report.md` -> Execute Micro-Gates for high/epic from implementation-notes and ledger. Re-run spec/quality checks independently; do not approve because micro-gates passed during execute.
13. If `<storage-root>/evolution/active/*.md` exists (resolved via `forgeflow_storage.py`), verify consistency with active project rules. Do not generate or validate new evolution rules; that is ship's responsibility.
14. Run route-appropriate role lanes and apply the review rubric plus role checklist. For quality review with diff/code input, apply `skills/ff-review/references/deep-code-analysis.md`.
15. Classify findings by severity: blocker, major, minor, nit.
16. Write or update `review-report.md` to the active task directory. For high/epic, spec and quality passes update the same file. The verdict in the file is the only valid verdict.
17. Verify execute completion checklist before approval: implementation plan stated, changed files listed, component/function roles explained, edge cases enumerated for medium/high/epic, verification commands run and recorded.
18. Return a clear verdict in chat that matches the file. If verdict is `changes_requested` or `blocked`, update `implementation-notes.md` so status reflects the review gate.

## Plan Conformance Gate

For each task in `plan.md` with status other than `skip` or `deferred`:

1. **Task traceability**: `implementation-notes.md` or `ledger.md` must show evidence this task was worked on. Zero mentions is a major `plan-conformance / task-missing` finding.
2. **File coverage**: if the task lists files, those files must have been created or modified. Missing files are major `plan-conformance / file-missing` findings.
3. **Verification completion**: each task verification step must produce observable evidence. Missing verification is a major `plan-conformance / verification-skipped` finding.
4. **Fulfills coverage**: if the task has `fulfills` links, evidence must show the criterion was addressed. Unfulfilled links are major `plan-conformance / criterion-unfulfilled` findings.

Write results to `review-report.md` -> **Plan Task Conformance**. Any blocker-severity conformance gap prevents approval. Small route traces only the primary task and listed files unless escalated; medium+ routes require full traceability.

## Three-lane routing

For high/epic routes, split review into 3 mandatory lanes. All lanes must approve for final PASS; any lane returning BLOCK or REQUEST_CHANGES forces overall ITERATE.

- **Architecture lane**: structural fitness, boundary integrity, coupling/cohesion, cross-cutting concern coverage. Uses `architecture-reviewer`.
- **Product lane**: `brief.md` Goal Contract functional completeness, acceptance criteria coverage, user-facing behavior correctness. Uses `spec-reviewer`.
- **Code lane**: code quality, security, performance, maintainability. Uses `quality-reviewer`.

Lane rules:

- high/epic -> all 3 lanes.
- medium -> architecture lane + code lane; product lane is merged into architecture.
- small -> single-pass quality review.

Record lane results in `review-report.md` -> **3-Lane Review Summary**. Each lane finding gets `lane: architecture | product | code`. Do not merge lane passes into a single turn for high/epic work; run lanes sequentially in separate turns, updating the same `review-report.md`.

## Quality review heuristics

For quality review, check:

- Every changed line traces directly to the request or approved plan.
- Drive-by refactors, speculative abstractions, and unrelated cleanup are flagged as scope drift unless explicitly authorized.
- The change is the smallest safe change that satisfies the request.
- Architectural depth improves locality and leverage without introducing shallow pass-through modules.
- The change avoids silent fallback, dual write, and shadow-path ownership drift.
- Existing codebase patterns are followed.
- Assumptions about types, APIs, behavior, and test coverage were verified against actual files.
- Performance changes include measurement when the bottleneck is in scope.

## Next-step output

- If `approved` and `--auto` is active: invoke `/forgeflow:ship` directly (see `_shared/automation.md`).
- If `approved` without `--auto`: tell the user review passed and `/forgeflow:ship` is ready. If worktree isolation is active, warn that `/forgeflow:ship` is needed for cleanup and update `checkpoint.md` with `Next Action: /forgeflow:ship (worktree cleanup pending)`.
- If `changes_requested` and all findings are artifact-only, auto-fix ForgeFlow metadata artifacts, update `checkpoint.md`, then re-invoke `/forgeflow:ff-review`.
- If `changes_requested` includes code findings, stop and present P0/P1 findings as `file:line - description`, then hand it back to execute.
- Do not auto-proceed to ship unless `--auto` is active.
