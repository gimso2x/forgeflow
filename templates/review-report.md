# 리뷰 보고서 (Review Report)

<!-- ForgeFlow review template. Created during review stage. -->
<!-- Write prose in the user's primary language. Preserve canonical labels, enum values, commands, paths, and artifact filenames in English. -->
<!-- high/epic: spec pass fills Spec Compliance first; quality pass completes Quality Assessment in this same file. -->
<!-- standalone: Standalone Input Source and Reviewer Role Summary sections are filled; skip inapplicable sections. -->

## Standalone 입력 소스 (Standalone Input Source)
<!-- Standalone mode only. Pipeline mode: delete this section. -->
- **Input Type**: <!-- URL | repo | diff | file-bundle | artifact -->
- **Original Input**: <!-- URL, path, or diff summary -->
- **Fetch Status**: <!-- success | partial | failed -->
- **Normalized Brief**: <!-- Auto-generated brief -->
- **Scope**: <!-- Files/directories/commit range -->
- **Constraints**: <!-- Review focus, excluded paths, additional rules -->

## 사용자용 요약 (Reader Summary)
<!-- Summarize verdict, main findings, verification confidence, blockers, and next action in the user's language. -->
<!-- Review/ship: read this section first on resume — expand Findings only when needed. -->

## 리뷰 유형 (Review Type)
<!-- spec | quality | security | ux -->
<!-- small/medium: quality only. high/epic: spec pass then quality pass (same file). -->

## 판정 (Verdict)
<!-- approved | changes_requested | blocked -->

## 리뷰어 (Reviewer)
<!-- Role or identifier -->

## 라우트 준수 (Route Compliance)
<!-- Pipeline mode only. Standalone mode: delete this section. -->
<!-- Did execution follow the selected route stages? -->

## 발견 사항 (Findings)

### Finding 1: <!-- title -->
- **Severity**: <!-- blocker | major | minor | nit -->
- **Category**: <!-- spec-compliance | quality | maintainability | risk | security -->
- **Role**: <!-- spec-reviewer | quality-reviewer | security-reviewer | ux-reviewer | perf-reviewer -->
- **Confidence**: <!-- HIGH | MEDIUM | LOW | CONFLICT -->
- **Description**:
- **Evidence**:
  - Observed:
  - Expected:
  - Missing:
- **Remediation**:

## 리뷰어 역할 요약 (Reviewer Role Summary)
<!-- Standalone mode and high/epic: summarize per-role verdicts and findings. -->
<!-- Small/medium pipeline: may be omitted or list quality-reviewer only. -->
- <!-- spec-reviewer -->: <!-- verdict -->, <!-- N --> findings (<!-- blockers --> blockers, <!-- majors --> major)
- <!-- quality-reviewer -->: <!-- verdict -->, <!-- N --> findings (<!-- blockers --> blockers, <!-- majors --> major)
- Cross-role conflicts: <!-- count --> (marked with ⚠)

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
<!-- Pipeline mode, high/epic only. Standalone mode or small/medium: delete this section. -->
<!-- Per-step gates from execute; NOT a substitute for this review pass. -->
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
<!-- Pipeline mode only. Standalone mode: delete this section (always not_applicable). -->
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
<!-- Pipeline mode or standalone with code input. Skip if reviewing non-code artifacts. -->
<!-- Quantitative metrics from implementation-notes.md or collected during review -->

| Metric | Value | Verdict |
|--------|-------|---------|
| TS errors | <!-- count, blocker if > 0 --> | <!-- PASS/FAIL --> |
| Type assertions | <!-- count --> | <!-- PASS/REVIEW --> |
| Debug artifacts | <!-- count, blocker if > 0 --> | <!-- PASS/FAIL --> |
| Max component LOC | <!-- largest component, major if > 150L --> | <!-- PASS/FLAG --> |
| Log volume | <!-- agent output size --> | <!-- PASS/NORMALIZE --> |

<!-- If any metric exceeds blocker threshold, generate an automatic finding above. -->

## 오버라이드 기록 (Override Log)
<!-- Record human overrides here. Only updated when human dismisses, escalates, or accepts risk. -->
<!-- Standalone mode: this section is critical — human judgment is the final gate. -->
<!-- Pipeline mode: may be empty if no overrides were applied. -->
- <!-- Finding N -->: <!-- dismissed | escalated | risk-accepted --> by <!-- human --> — "<!-- reason -->"

## 독립 모드 메타데이터 (Standalone Mode Metadata)
<!-- Standalone mode only. Pipeline mode: delete this section. -->
- **Synthetic Task Dir**: <!-- .forgeflow/tasks/standalone-<timestamp>/ -->
- **Input Source Artifact**: <!-- input-source.md path -->
- **Normalized Input Artifact**: <!-- normalized-input.md path -->
- **Review Triggered By**: <!-- direct user request | --type flag | auto-detected -->
- **Active Reviewer Roles**: <!-- list roles that ran -->
- **Review Completed At**: <!-- ISO timestamp -->
