# Review Report

<!-- ForgeFlow review template. Created during review stage. -->
<!-- high/epic: spec pass fills Spec Compliance first; quality pass completes Quality Assessment in this same file. -->

## Review Type
<!-- spec | quality | security | ux -->
<!-- small/medium: quality only. high/epic: spec pass then quality pass (same file). -->

## Verdict
<!-- approved | changes_requested | blocked -->

## Reviewer
<!-- Role or identifier -->

## Route Compliance
<!-- Did execution follow the selected route stages? -->

## Findings

### Finding 1: <!-- title -->
- **Severity**: <!-- blocker | major | minor | nit -->
- **Category**: <!-- spec-compliance | quality | maintainability | risk | security -->
- **Description**:
- **Evidence**:
  - Observed:
  - Expected:
  - Missing:
- **Remediation**:

## Spec Compliance
<!-- For spec review -->
- [ ] Brief objective satisfied
- [ ] Acceptance criteria met
- [ ] Execution stayed inside scope
- [ ] No silent fallback or dual-write drift
- [ ] Evidence sufficient for completion claim
- [ ] Route stages followed correctly

## Quality Assessment
<!-- For quality review -->
- [ ] Result is simple enough
- [ ] Verification quality acceptable
- [ ] Residual risks documented
- [ ] Maintainability acceptable for task size
- [ ] Smallest safe change
- [ ] No unnecessary abstractions added
- [ ] TDD cycle followed (red → green → refactor) <!-- only when plan step required TDD -->

## Execute Micro-Gates
<!-- high/epic only. Per-step gates from execute; NOT a substitute for this review pass. -->
<!-- Copy summary from implementation-notes Evidence (micro_spec:*, micro_quality:*) and run-ledger. -->
<!-- Stage reviewer must re-verify; treat micro-gate results as reported evidence unless independently observed. -->

| Plan step | micro_spec | micro_quality | Assignee (ledger) | Stage re-verified |
|-----------|------------|---------------|-------------------|-------------------|
| <!-- step name --> | <!-- PASS/FAIL/skip --> | <!-- PASS/FAIL/skip/n/a --> | <!-- worker/specialist/spec-reviewer --> | <!-- yes | no --> |

## Evidence Classification
<!-- Summarize evidence quality -->
- **Observed evidence**: <!-- what was directly verified in THIS review turn -->
- **Reported evidence**: <!-- executor claims, micro_spec/micro_quality from execute, run-ledger refs -->
- **Missing evidence**: <!-- what should exist but doesn't -->

## Open Blockers
<!-- List blockers or "none" -->

## Safe for Next Stage
<!-- yes | no -->

## Evolution Rule Review
<!-- approved | changes_requested | not_applicable -->
- **Candidates Reviewed**:
- **Activation Guidance**:
- **Scope Check**:
- **Evidence Check**:

## Next Action
<!-- What should happen next -->

## Approved By
<!-- Name/role, only if verdict is approved -->

## Residual Risks
<!-- Risks that remain after this review -->
-
