# 리뷰 보고서 (Review Report)

<!-- ForgeFlow review template. Created during review stage. -->
<!-- Write prose in the user's primary language. Preserve canonical labels, enum values, commands, paths, and artifact filenames in English. -->
<!-- high/epic: spec pass fills Spec Compliance first; quality pass completes Quality Assessment in this same file. -->

## 사용자용 요약 (Reader Summary)
<!-- Summarize verdict, main findings, verification confidence, blockers, and next action in the user's language. -->

## 리뷰 유형 (Review Type)
<!-- spec | quality | security | ux -->
<!-- small/medium: quality only. high/epic: spec pass then quality pass (same file). -->

## 판정 (Verdict)
<!-- approved | changes_requested | blocked -->

## 리뷰어 (Reviewer)
<!-- Role or identifier -->

## 라우트 준수 (Route Compliance)
<!-- Did execution follow the selected route stages? -->

## 발견 사항 (Findings)

### Finding 1: <!-- title -->
- **Severity**: <!-- blocker | major | minor | nit -->
- **Category**: <!-- spec-compliance | quality | maintainability | risk | security -->
- **Description**:
- **Evidence**:
  - Observed:
  - Expected:
  - Missing:
- **Remediation**:

## 명세 준수 (Spec Compliance)
<!-- For spec review -->
- [ ] Brief objective satisfied
- [ ] Acceptance criteria met
- [ ] Execution stayed inside scope
- [ ] No silent fallback or dual-write drift
- [ ] Evidence sufficient for completion claim
- [ ] Route stages followed correctly

## 품질 평가 (Quality Assessment)
<!-- For quality review -->
- [ ] Result is simple enough
- [ ] Verification quality acceptable
- [ ] Residual risks documented
- [ ] Maintainability acceptable for task size
- [ ] Smallest safe change
- [ ] No unnecessary abstractions added
- [ ] TDD cycle followed (red → green → refactor) <!-- only when plan step required TDD -->

## Execute 마이크로 게이트 (Execute Micro-Gates)
<!-- high/epic only. Per-step gates from execute; NOT a substitute for this review pass. -->
<!-- Copy summary from implementation-notes Evidence (micro_spec:*, micro_quality:*) and run-ledger. -->
<!-- Stage reviewer must re-verify; treat micro-gate results as reported evidence unless independently observed. -->

| Plan step | micro_spec | micro_quality | Assignee (ledger) | Stage re-verified |
|-----------|------------|---------------|-------------------|-------------------|
| <!-- step name --> | <!-- PASS/FAIL/skip --> | <!-- PASS/FAIL/skip/n/a --> | <!-- worker/specialist/spec-reviewer --> | <!-- yes | no --> |

## 증거 분류 (Evidence Classification)
<!-- Summarize evidence quality -->
- **Observed evidence**: <!-- what was directly verified in THIS review turn -->
- **Reported evidence**: <!-- executor claims, micro_spec/micro_quality from execute, run-ledger refs -->
- **Missing evidence**: <!-- what should exist but doesn't -->

## 열린 blocker (Open Blockers)
<!-- List blockers or "none" -->

## 다음 단계 진행 가능 여부 (Safe for Next Stage)
<!-- yes | no -->

## 진화 규칙 리뷰 (Evolution Rule Review)
<!-- approved | changes_requested | not_applicable -->
- **Candidates Reviewed**:
- **Activation Guidance**:
- **Scope Check**:
- **Evidence Check**:

## 다음 작업 (Next Action)
<!-- What should happen next -->

## 승인자 (Approved By)
<!-- Name/role, only if verdict is approved -->

## 잔여 위험 (Residual Risks)
<!-- Risks that remain after this review -->
-

## 코드 품질 지표 (Code Quality Metrics)
<!-- Quantitative metrics from implementation-notes.md or collected during review -->

| Metric | Value | Verdict |
|--------|-------|---------|
| TS errors | <!-- count, blocker if > 0 --> | <!-- PASS/FAIL --> |
| Type assertions | <!-- count --> | <!-- PASS/REVIEW --> |
| Debug artifacts | <!-- count, blocker if > 0 --> | <!-- PASS/FAIL --> |
| Max component LOC | <!-- largest component, major if > 150L --> | <!-- PASS/FLAG --> |
| Log volume | <!-- agent output size --> | <!-- PASS/NORMALIZE --> |

<!-- If any metric exceeds blocker threshold, generate an automatic finding above. -->
