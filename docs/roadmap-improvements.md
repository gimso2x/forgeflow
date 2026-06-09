# ForgeFlow Improvement Roadmap Archive

> **기준 버전**: v1.9.1 | **작성일**: 2026-05-29
> **성격**: historical/archive design notes — 런타임 코드 없는 마크다운 배포판 원칙 유지

This document is not the live maintainer queue. Current actionable maintenance items live in [`docs/maintainer-backlog.md`](maintainer-backlog.md). Treat the sections below as historical context unless a current GitHub issue or maintainer backlog item explicitly revives them.

---

## Priority 1: Review Standalone 진입점

> **Status**: ✅ 완료. 현재 계약은 `docs/review-runtime-contract.md`, `skills/ff-review/SKILL.md`, `templates/input-source.md`, `templates/normalized-input.md`, `templates/review-report.md`, `evals/evals.json`를 기준으로 유지합니다. 이 섹션은 구현 전 설계 기록이며, 아래 baseline은 historical context입니다.

### Historical baseline
- review는 execute 후속 검증으로만 설계됨
- 반드시 `implementation-notes.md` + `ledger.md` Execution Tracking section이 선행되어야 실행 가능

### 목표
- URL / repo / diff / 파일 묶음만으로 review가 즉시 실행 가능
- 내부 입력을 **artifact + evidence + scope** 3요소로 표준화

### 설계

#### 입력 유형 매트릭스
| Input Source | Artifact | Evidence | Scope |
|---|---|---|---|
| Post-execute | `implementation-notes.md` | `ledger.md` Execution Tracking section | plan.md scope |
| URL (PR diff) | diff URL | diff hunks | changed files |
| Repo snapshot | 디렉토리 구조 | file listing | 지정 경로 |
| File bundle | 파일 목록 | 파일 내용 | 지정 파일 |
| Git range | commit range | diff output | changed paths |

#### SKILL.md 변경 포인트
```yaml
# skills/ff-review/SKILL.md — dependencies 확장
dependencies:
  - skills/_shared/preflight.md
  - skills/_shared/discipline.md
  - skills/_shared/isolation.md  # worktree 내 review 시
```

- **Input 섹션**에 standalone 모드 추가:
  - `mode: post-execute` (기존)
  - `mode: standalone` (신규)
- standalone 시 `evidence_source` 필드로 입력 출처 명시
- scope는 항상 명시적 (기본값: changed files only)

#### Templates 변경
- `templates/input-source.md`에 standalone 입력 출처/fetch 상태/provenance 기록
- `templates/normalized-input.md`에 artifact/evidence/scope/constraints 정규화와 evidence integrity gate 기록
- `templates/review-report.md`의 Standalone Input Source 요약에 source/freshness/access posture를 echo

### 검증
- `evals/evals.json`에 standalone review eval 추가
  - URL 입력 → scope 자동 추출
  - file bundle 입력 → evidence 수집
  - post-execute와 standalone이 동일 report 스키마 생성

---

## Priority 2: Review 산출물 표준화

### 목표
- stage별 결과물을 고정 포맷으로 표준화
- 후속 stage가 파싱 없이 재사용 가능

### 산출물 스키마

#### `review-report.md` (기존 강화)
```markdown
---
schema: review-report/v2
task_id: <id>
input_mode: post-execute | standalone
scope:
  files_changed: [<list>]
  boundaries: [<list>]
summary: <1-line>
severity_breakdown:
  critical: N
  high: N
  medium: N
  low: N
  advisory: N
---

## Findings
### [CRITICAL|HIGH|MEDIUM|LOW|ADVISORY] <title>
- **File**: path:line
- **Evidence**: <quote>
- **Fix**: <suggestion>
- **Category**: security|perf|ux|correctness|maintainability
```

#### `ledger.md` Plan Items section (current replacement for deprecated `plan-ledger.md`)
```markdown
---
schema: ledger/v1
task_id: <id>
route: small|medium|high|epic
total_items: N
---

## Items
### [ ] <item title>
- **Type**: feature|fix|refactor|docs
- **Scope**: <file list>
- **Dependencies**: <item refs>
- **Estimate**: small|medium|large

## Decisions
- <decision>: <rationale>
```

#### `implementation-notes.md` Decisions section (current replacement for deprecated `decision-log.md`)
```markdown
---
schema: implementation-notes/v1
task_id: <id>
---

## Decisions
### D-NNN: <title>
- **Context**: <why needed>
- **Options**: [<list>]
- **Chosen**: <option>
- **Rationale**: <why>
- **Stage**: clarify|plan|execute|review
- **Reversible**: yes|no
```

### 적용
- 각 스킬 SKILL.md의 Output Artifacts 섹션에 스키마 버전 명시
- `templates/`에 신규 템플릿 추가
- 후속 스킬이 `schema: review-report/v2` 등을 읽고 호환성 판단

---

## Priority 3: Specialist Review 분리

### 목표
- clarify에서 "깊이"(route)와 "전문가"(spec)를 분리
- review stage에서 전문가 프로필에 따른 특화 검증 수행

### 설계

#### Clarify 단계
- `route`: small/medium/high/epic (기존)
- `specialist`: none | security | ux | perf | correctness | maintainability (신규)
- route는 스코프 크기, specialist는 검증 관점

```yaml
# brief.md 확장
---
schema: brief/v2
task_id: <id>
route: medium
specialist:
  primary: security
  secondary: correctness
  rationale: "인증 로직 포함"
---
```

#### Specialist별 검증 포인트
| Specialist | Focus | Key Assertions |
|---|---|---|
| security | 인증/권한/입력검증 | no hardcoded secrets, input sanitization, auth boundary |
| ux | UI/문구/접근성 | consistent terminology, a11y, clear error messages |
| perf | 성능/메모리/지연 | no N+1 queries, lazy load, cache strategy |
| correctness | 로직/에러처리 | edge cases, error propagation, idempotency |
| maintainability | 구조/네이밍/중복 | DRY, single responsibility, naming convention |

#### Review 단계
- review SKILL.md에 specialist profile 서브섹션 추가
- 해당 specialist의 assertion을 자동 적용
- `review-report.md`에 `specialist_profile` 필드 추가

### 검증
- eval: specialist=security 시 security assertion 자동 활성화
- eval: specialist=null 시 기본 검증만 수행

---

## Priority 4: Init 아키텍처 초안 생성기

### 현재 상태
- init은 `.forgeflow/` 디렉토리 스캐폴딩 + `defaults.md` 생성

### 목표
- 프로젝트 시작 시 운영에 필요한 초안을 자동 생성:
  - 팀 구조 초안
  - 에이전트 구성 초안
  - 스킬 초안 (프로젝트 특화)
  - 문서 포인터

### 설계

#### Config 메뉴의 full init
```
/forgeflow:ff-config
→ full init (프로젝트 컨텍스트 draft)
```

#### 생성 산출물
```markdown
# <storage-root>/project-draft.md
---
schema: project-draft/v1
generated: <date>
---

## Team Structure
- Roles: <auto-detected from repo structure>
- Review policy: <based on route>

## Agent Configuration
- Recommended adapters: <based on repo type>
- Skill overrides: <based on language/framework>

## Custom Skills (초안)
- <auto-generated from common patterns>

## Documentation Pointers
- README: <path>
- Contributing: <path>
- API docs: <path>
```

#### 자동 감지 로직 (프롬프트 기반)
- `package.json` → Node.js 프로젝트
- `pyproject.toml` → Python 프로젝트
- `Cargo.toml` → Rust 프로젝트
- 감지 결과에 따라 추천 specialist, adapter, 스킬 프리셋 생성

### Templates
- `templates/project-draft.md` (신규)
- `templates/team-structure.md` (신규)

---

## Priority 5: Telemetry / 운영 지표

### 목표
- "느낌상 빠름"이 아니라 실제 병목을 보이게
- 마크다운 기반이므로 JSONL 이벤트 로그로 기록

### 설계

#### 이벤트 스키마
```json
{
  "schema": "forgeflow-telemetry/v1",
  "task_id": "<id>",
  "event": "stage_complete",
  "stage": "clarify|plan|execute|review|ship",
  "timestamp": "<ISO>",
  "duration_seconds": 42,
  "tokens_used": 15000,
  "model": "<model id>",
  "adapter": "claude|codex|cursor",
  "route": "small|medium|high|epic",
  "specialist": "<null or specialist>",
  "outcome": "success|partial|failed",
  "failure_type": "<null or category>"
}
```

#### 수집 포인트
| Stage | Duration | Tokens | Failure Types |
|---|---|---|---|
| clarify | 요구사항 정리 시간 | 입력 파싱 + route 산정 | scope 불명확, 입력 부족 |
| plan | 계획 수립 시간 | decomposition + estimation | epic 분해 실패, 의존성 충돌 |
| execute | 구현 시간 | code gen + file ops | 빌드 실패, 테스트 실패 |
| review | 검증 시간 | evidence 수집 + assertion | 위약 탐지, false positive |
| ship | 마무리 시간 | cleanup + commit | merge 충돌, worktree 오류 |

#### 산출물
- `~/.forgeflow/projects/<project-slug>/telemetry/<task-id>.jsonl` — 태스크별 이벤트 로그
- `~/.forgeflow/projects/<project-slug>/telemetry/summary.md` — 집계 리포트 (cron 또는 long-run에서 생성)

#### Metrics Dashboard (markdown)
```markdown
# ForgeFlow Metrics — <period>

## Stage Duration (p50 / p90)
- clarify: 30s / 120s
- plan: 2m / 8m
- execute: 5m / 25m
- review: 1m / 5m
- ship: 30s / 3m

## Failure Distribution
- execute.build: 12%
- execute.test: 8%
- review.false-positive: 5%

## Token Cost by Adapter
- claude: 150k tokens/session avg
- codex: 80k tokens/session avg

## Worktree Stability
- success rate: 97%
- avg cleanup time: 15s
```

---

## Priority 6: Scope Boundary 명시화

### 현재 상태
- scope는 clarify에서 "route scoring"으로 결정
- boundary 판단이 사람 해석에 의존

### 설계

#### Scope Boundary 체크리스트
```markdown
## In Scope
- 요구사항에 명시된 기능/수정
- 직접적 의존 파일
- 관련 테스트
- 관련 문서 업데이트

## Out of Scope (명시적 거부 필요)
- 요구사항에 없는 리팩토링
- 인접 모듈 "개선"
- 의존성 버전 업그레이드
- 포맷팅/스타일 변경 (별도 태스크가 아닌 경우)

## Boundary Judgment
- 파일 수정 범위가 route 임계값 초과 시 자동 경고
- scope 파일 수: small ≤3, medium ≤8, high ≤20, epic 무제한
- 초과 시 "scope split 권장" advisory 발행
```

### 적용
- `skills/_shared/discipline.md`에 boundary 섹션 추가
- review에서 boundary 위반 탐지
- `review-report.md`에 `scope_boundary_violations` 필드 추가

---

## Priority 7: 릴리즈 노트 사용자 영향 기준 재정렬

### 현재 상태
- Keep a Changelog 형식 (Added/Changed/Fixed/Removed)

### 목표
- 변경 유형이 아닌 **사용자 영향 축**으로 재정렬

### 설계
```markdown
## [x.y.z] - YYYY-MM-DD

### 🔒 자동화 정합성
- route 임계값 변경, eval 스키마 수정 등

### 🔍 검증 정책
- 새로운 assertion, 검증 스크립트 추가 등

### ⚡ 속도 / 안정성
- 성능 개선, 크래시 수정 등

### 👤 사용자 경험
- UI/커맨드 변경, 문서 개선 등
```

### 적용
- `CHANGELOG.md`의 향후 버전부터 새 분류 적용
- 기존 버전은 유지 (retroactive 변경 불필요)
- release 스킬에 분류 가이드라인 추가

---

## 실행 계획

| Phase | Items | 의존성 | 상태 |
|---|---|---|---|
| **Phase 1** | Priority 1 (review standalone) + Priority 2 (산출물 표준화) | 없음 | ✅ 완료 |
| **Phase 2** | Priority 3 (specialist review) | Phase 1 | ✅ 완료 (v1.5.2) |
| **Phase 3** | Priority 4 (init 초안 생성) | 없음 | ✅ 완료 (v1.6.0) |
| **Phase 4** | Priority 5 (telemetry) | Priority 2 (이벤트 스키마) | ✅ 완료 (v1.6.0) |
| **Phase 5** | Priority 6 (scope boundary) | Priority 2 (boundary 필드) | ✅ 완료 (v1.6.0) |
| **Phase 6** | Priority 7 (릴리즈 노트) | 없음 | ✅ 완료 (Unreleased) |

Phase 1~6 모두 완료. Phase 6은 [Unreleased] 섹션을 영향 축(🔒 자동화·정합성 / 🔍 검증·정책 / ⚡ 속도·안정성 / 👤 사용자·경험)으로 재분류하고, `validate_changelog_links.py`와 release 스킬에 분류 가이드라인을 추가했다.

---

## v1.11.7 이후 개선점 (Phase 7)

> **기준 버전**: v1.11.7 | **작성일**: 2026-06-03
> v1.11.7 기준 전체 코드베이스 분석에서 도출. P1~P7 완료 후 남은 gap 18개.

### ✅ 완료 (Phase 7)

| # | 카테고리 | 개선점 | 상태 |
|---|---------|--------|------|
| F6 | skill-quality | Small-route auto-chain 모순 수정 (`automation.md` clarify→execute→ship) | ✅ |
| F7 | skill-quality | clarify Output Artifacts에 Goal Contract 명시 추가 | ✅ |
| F9+F1 | adapter+validation | `.claude-plugin/plugin.json`에 `interface.defaultPrompt` 추가 + validator 포함 | ✅ |
| F2 | validation | `validate_template_refs.py`가 `_shared/*.md` template 참조도 검증 | ✅ |
| F4+F5+F17 | validation | `validate_workflow_vocab.py`가 `.claude/skills/` 포함 | ✅ |
| F8 | template | `plan.md` Architecture Notes 섹션 — 이미 존재 확인 (가짜 긍정) | ✅ |
| F10 | adapter | Gemini agents/skills를 `adapter-config.md`에 문서화 | ✅ |
| F11 | eval | ForgeFlow 라우터 스테이지 분기 eval 추가 (id 121) | ✅ |
| F12 | eval | Changelog impact-axis 분류 eval 추가 (id 120) | ✅ |
| F13 | eval | Small-route auto-chain skip-review eval 추가 (id 122) | ✅ |
| F14 | docs | Standalone review 설계문서에 historical 명시 추가 | ✅ |
| F15 | docs | `adapter-layout.md` migration deferred 표시 추가 | ✅ |

### 📋 예정 (medium effort)

| # | 카테고리 | 개선점 | 노력 |
|---|---------|--------|------|
| ~~F3~~ | ~~validation~~ | ~~Template 필드명 ↔ Skill 기대값 교차검증~~ | ~~medium~~ |
| ~~F18~~ | ~~shared~~ | ~~Verification gate 공유 catalog~~ | ~~medium~~ |
| ~~F13-ext~~ | ~~eval~~ | ~~End-to-end auto-chain eval~~ | ~~high~~ |

Phase 7 완료. 18개 전체 개선항목 모두 완료.
