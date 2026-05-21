# 컨텍스트 브리프 (Context Brief)

<!-- ForgeFlow brief template. Fill each section during clarify. -->
<!-- Write prose in the user's primary language. Preserve canonical labels, enum values, commands, paths, and artifact filenames in English. -->

## 목표 (Objective)
<!-- One-sentence description of what this task accomplishes -->

## 라우트 (Route)
<!-- small | medium | high | epic -->
<!-- Route sub-band (medium only): medium-light | medium-full — from brief.md raw_score -->
<!-- Route rationale: why this route is sufficient and smallest safe choice -->

## 라우트 근거 (Route Rationale)
<!-- Evidence behind route selection: scope, risk, dependencies, rollback, ambiguity -->

## 라우트 하위 밴드 (Route Sub-band)
<!-- medium-light (10-16.9) | medium-full (17-24.9) | n/a for other routes -->

## WHERE 근거 (WHERE Grounding)
<!-- Project context for calibrating intake depth -->
- **Project type**: <!-- user-facing app | API/service | dev tool/library | infrastructure -->
- **Situation**: <!-- greenfield | brownfield extension | brownfield refactor | hybrid -->
- **Ambition**: <!-- toy/experiment | feature/MVP | product -->

## 범위 포함 (In Scope)
-

## 범위 제외 (Out of Scope)
-

## 제약 조건 (Constraints)
-

## 인수 기준 (Acceptance Criteria)
- [ ]

## 위험 수준 (Risk Level)
<!-- low | medium | high | critical -->

## 위험 보정 요소 (Risk Modifiers)
<!-- Check all that apply -->
- [ ] Sensitive data
- [ ] External exposure
- [ ] Irreversible operations
- [ ] High scale

## 모호성 점수 (Ambiguity Score)
<!-- 0.0 to 1.0. Above 0.2 requires blocker resolution or bounded assumptions. -->

## 가정 (Assumptions)
<!-- Bounded assumptions for non-blocking unknowns -->
-

## 적용된 진화 규칙 (Applied Evolution Rules)
<!-- Rules loaded during clarify. Project active rules are required; global rules are advisory. -->
- **Project active rules**: <!-- .forgeflow/evolution/active/*.md that matched -->
- **Global advisory rules**: <!-- ~/.forgeflow/evolution/active/*.md that matched -->
- **Ignored rules**: <!-- rules checked but not applicable, with reason -->

## 열린 질문 (Open Questions)
<!-- Blockers that must be resolved before proceeding -->
-

## specialist 필요 여부 (Specialists)
<!-- Required: (none | security-review | ux-review | perf-review | frontend-execute | backend-execute | infra-execute) -->
<!-- Suggested specialists: advisory candidates from request keywords and repo context -->
<!-- Skipped: (none | list) -->
<!-- Skip rationale: -->

## 작업량 메모 (Budget Note)
<!-- Advisory only: expected size/complexity, e.g. small single-file, medium coordinated files, high multi-component, epic milestone-scale -->

## 추천 다음 스킬 (Suggested Next Skill)
<!-- /forgeflow:execute | /forgeflow:plan | /forgeflow:milestone | /forgeflow:review | /forgeflow:ship -->

## 검증 게이트 (Verification Gates)
<!-- Auto-detected from tech stack -->
- [ ]

## 최소 검증 (Min Verification)
<!-- small: build|lint|type_check (fastest available) -->
<!-- medium: lint + type_check + test (if exists) -->
<!-- high: build + lint + type_check + test -->
<!-- epic: full suite + milestone integration tests -->

## 환경 사전 점검 (Environment Preflight)
<!-- git repo status, lockfile/dependency check, etc. -->
