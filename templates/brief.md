---
schema: brief/v2
task_id: <!-- TASK_ID -->
route: <!-- small|medium|high|epic -->
specialist:
  primary: <!-- none|security|ux|perf|correctness|maintainability -->
  secondary: <!-- none|security|ux|perf|correctness|maintainability -->
  rationale: <!-- why -->
scope_boundary:
  files_planned: <!-- N -->
  files_limit: <!-- route에 따른 임계값 (small=3, medium=8, high=20, epic=unlimited) -->
  boundary_status: <!-- within | at_limit | exceeds -->
ambiguity:
  objective: <!-- 1-10 -->
  scope: <!-- 1-10 -->
  constraints: <!-- 1-10 -->
  acceptance: <!-- 1-10 -->
  score: <!-- computed 0.0-1.0 -->
  rounds: <!-- N -->
  status: <!-- pass | bounded_assumption -->
---

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

## 공통 프로젝트 컨텍스트 (Common Project Context)
<!-- Read from <storage-root>/project-draft.md when present. Record only task-relevant sections and repo-relative pointers, not long copied source docs. -->
- **Source**: <!-- <storage-root>/project-draft.md | unavailable -->
- **Planning/WBS pointers**: <!-- paths or n/a -->
- **Architecture/contract pointers**: <!-- paths or n/a -->
- **Verification hints**: <!-- commands/gates or n/a -->

## 범위 포함 (In Scope)
-

## 범위 제외 (Out of Scope)
-

## 범위 위상 (Scope Topology)
<!-- Top-level components (1-6) confirmed during Round 0. Updated if new components discovered. -->
-

## 도메인 온톨로지 (Domain Ontology)
<!-- Key domain terms and their definitions as used in this task. Simplified from gajae-code ontology tracking. -->
<!-- Optional — fill when domain-specific terminology needs shared understanding. -->

## 제약 조건 (Constraints)
-

## 인수 기준 (Acceptance Criteria)
- [ ]

## Goal Contract
<!-- Goal Contract: objective pass/fail conditions (inspired by roach-pi verifier pattern). -->
<!-- This section makes "done" unambiguous — review uses these to judge PASS/FAIL. -->
- **성공 기준 (Success Criteria):** <!-- 작업 완료의 객관적 조건 (measurable, observable) -->
- **필수 증거 (Evidence Required):** <!-- PASS 판정에 필요한 관찰 가능 결과 (command output, test results, diff) -->
- **인정된 리스크 (Accepted Risks):** <!-- 알고 감수하는 리스크 — review에서 재평가하지 않음 -->
- **명시적 제외 (Explicit Exclusions):** <!-- 하지 않는 것 명시 — 범위 확장 방지 -->

## 위험 수준 (Risk Level)
<!-- low | medium | high | critical -->

## 위험 보정 요소 (Risk Modifiers)
<!-- Check all that apply -->
- [ ] Sensitive data
- [ ] External exposure
- [ ] Irreversible operations
- [ ] High scale

## 모호성 점수 (Ambiguity Score)
<!-- Computed from 4-dimension scoring gate (objective, scope, constraints, acceptance). -->
<!-- score ≤ 0.3: proceed. 0.3–0.5: targeted questions. > 0.5: focused blocker questions. max 3 rounds. -->
<!-- See YAML frontmatter `ambiguity` field for dimension scores. -->
- **ambiguity_score**: <!-- 0.0–1.0, computed average of max(10-dim)/10 -->
- **rounds_used**: <!-- N -->
- **status**: <!-- pass | bounded_assumption -->

## 가정 (Assumptions)

- <!-- known assumptions -->

## 가정과 해석 (Assumptions and Interpretation)

- **Selected interpretation**:
- **Assumptions**:
- **Open ambiguity**:
- **Why safe to proceed**:

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

## specialist 프로필 (Specialist Profile)
<!-- Specialist determines the review verification perspective, separate from route scope. -->
<!-- Read from YAML frontmatter specialist field. -->
<!-- primary: dominant review lens -->
<!-- secondary: supplementary review perspective -->
<!-- rationale: why this specialist was selected -->

## 작업량 메모 (Budget Note)
<!-- Advisory only: expected size/complexity, e.g. small single-file, medium coordinated files, high multi-component, epic milestone-scale -->

## 추천 다음 스킬 (Suggested Next Skill)
<!-- /forgeflow:execute | /forgeflow:ff-plan | /forgeflow:ff-review | /forgeflow:ship -->

## 검증 게이트 (Verification Gates)
<!-- Auto-detected from tech stack -->
- [ ]

## 최소 검증 (Min Verification)
<!-- small: build|lint|type_check (fastest available) -->
<!-- medium: lint + type_check + test (if exists) -->
<!-- high: build + lint + type_check + test -->
<!-- epic: full suite + milestone integration tests -->

## 자동 모드 (Auto Mode)
<!-- false (default) | true — when true, agent chains through all remaining stages without (y/n) prompts. See skills/_shared/automation.md. -->
- **auto**: <!-- false -->

## 작업 격리 (Task Isolation)
<!-- worktree | none — worktree isolation for parallel task execution (medium/high/epic only) -->
- **isolation**: <!-- worktree | none -->
- **worktree_path**: <!-- .forgeflow/worktrees/<task-id>/ (relative to main repo) -->
- **branch**: <!-- <type>/<YYYYMM>-<korean-description> -->

## 환경 사전 점검 (Environment Preflight)
<!-- git repo status, lockfile/dependency check, etc. -->
