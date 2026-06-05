# gajae-code → ForgeFlow 흡수 분석

> **분석 대상**: [Yeachan-Heo/gajae-code](https://github.com/Yeachan-Heo/gajae-code) — Turborepo 기반 TypeScript+Rust+Python 코딩 에이전트 런타임  
> **흡수 대상**: [gimso2x/forgeflow](https://github.com/gimso2x/forgeflow) — artifact-first 마크다운 워크플로우 (v1.13.0)

## 1. 두 프로젝트 개요 비교

| 차원 | gajae-code | forgeflow |
|------|-----------|-----------|
| **형태** | 풀스택 런타임 (CLI `gjc`, TUI, 툴 시스템, tmux 오케스트레이션) | 순수 마크다운 스킬/템플릿 (런타임 없음) |
| **언어** | TypeScript + Rust (네이티브) + Python (평가) | 마크다운 + Makefile + Python (검증 스크립트) |
| **런타임** | Bun | 없음 (에이전트 플랫폼 의존) |
| **워크플로우** | deep-interview → ralplan → ultragoal/team/executor | clarify → plan → execute → review → ship |
| **상태 관리** | `.gjc/` 디렉토리 + CLI 명령어 (`gjc state/ralplan/ultragoal`) | `~/.forgeflow/` 디렉토리 + 마크다운 아티팩트 |
| **롤 분리** | 4개 롤 에이전트 (architect, planner, critic, executor) | 스테이지별 역할 (planning/implementation/review/learning) |
| **검증** | 컨센서스 루프 + 강제 품질 게이트 | Self-Critique 루프 (max 3) + 독립 review |

## 2. gajae-code 핵심 아키텍처 요약

### 2.1 워크플로우 스킬 (4개)

- **deep-interview**: 소크라테스식 질문 엔진. 모호도(ambiguity) 수학적 스코어링, 위상(topology) 열거 게이트, 온톨로지 수렴 추적. Phase 0(블로킹) → Round 0(위상 락) → Phase 2(루프 질문+스코어링) → Phase 3(도전 에이전트 @4/6/8 라운드) → Phase 4(결정화) → Phase 5(실행 브리지).
- **ralplan**: 컨센서스 기획 루프. Planner → Architect → Critic 순차 루프 (max 5회). receipt-only 반환으로 컨텍스트 폭력 방지. 사전 실행 게이트(≤15 유효 단어 차단).
- **ultragoal**: 내구성 다중 목표 기획+순차 실행. 강제 완료 품질 게이트 (architect 3-lane + executor red-team + 전체 재검증). ledger.jsonl 감사 추적.
- **team**: tmux 기반 다중 워커 오케스트레이션. JSONL 사서함, 파일 기반 조정, 워크트리 격리.

### 2.2 롤 에이전트 (4개)

- **architect**: 읽기 전용, CRITICAL/HIGH/MEDIUM/LOW 심각도 등급, CLEAR/WATCH/BLOCK + APPROVE/COMMENT/REQUEST CHANGES
- **planner**: 읽기 전용, 작업 분류(simple/refactor/feature/broad), 적응적 계획
- **critic**: 읽기 전용, OKAY/ITERATE/REJECT + 증거 기반 평가
- **executor**: 자율 구현, compact file-level plan, scope broadening 금지

### 2.3 핵심 크로스커팅 패턴

- **상태 CLI**: 모든 스킬이 `gjc state write/read` CLI로 상태 관리. 직접 `.gjc/` 편집 금지
- **핸드오프 프로토콜**: `gjc state <caller> write --input '{"current_phase":"handoff"}' → 원자적 demote/promote`
- **Receipt-only 반환**: 롤 에이전트가 검증 결과만 반환 (전체 마크다운 중복 방지)
- **수학적 스코어링**: 가중 모호도 공식, per-component 스코어링, 온톨로지 안정성 비율
- **언어 보존**: `language.instruction`이 전체 라이프사이클 유지
- **Prompt 예산**: 오버사이징 컨텍스트는 스코어링/질문 전에 요약 필수

## 3. 흡수 방안 — 3티어 우선순위

### Tier 1: 즉시 적용 가능 (스킬 프롬프트 개선)

#### 3.1 ambiguity 스코어링 → clarify 스테이지

**현재 forgeflow**: clarify는 주관적 판단으로 route 선택 (small/medium/high/epic)  
**gajae-code에서 가져올 것**: 모호도 임계값 기반 진행 제어

**구체안**:
- `brief.md`에 `ambiguity_threshold` 필드 추가 (기본값 0.3)
- clarify 종료 조건: "충분히 명확한가?"를 4개 차원(목표, 범위, 제약, 수용 기준)별 1-10 스코어링
- 스코어가 임계값 이하면 진행, 초과면 추가 질문 라운드 (max 3)
- gajae-code의 수학적 공식은 과도하니 단순화: `max(10-dim_score)/10` per dimension, 평균이 threshold 이하면 통과

**변경 범위**: `skills/clarify/SKILL.md`, `templates/brief.md`

#### 3.2 receipt-only verdict → ff-plan Self-Critique

**현재 forgeflow**: Self-Critique 루프가 전체 plan을 재평가 (컨텍스트 낭비)  
**gajae-code에서 가져올 것**: receipt-only 반환 + structured verdict

**구체안**:
- Self-Critique 결과를 plan.md에 전체 기록 대신, 구조화된 verdict만 기록:
  ```
  ## Self-Critique Verdict
  Status: APPROVE | ITERATE | REJECT
  Findings: [HIGH|LOW] 1-line-per-finding
  Required Changes: numbered list (if ITERATE/REJECT)
  ```
- ITERATE/REJECT 시에만 상세 내용을 plan.md에 추가
- max 3회 iteration 유지

**변경 범위**: `skills/ff-plan/SKILL.md` (Self-Critique 섹션)

#### 3.3 사전 실행 게이트 → plan→execute 경계

**현재 forgeflow**: auto-chain이 단순히 다음 스테이지 호출  
**gajae-code에서 가져올 것**: 실행 요청의 구체성 검증

**구체안**:
- plan→execute 전환 시 (auto-chain 포함), brief.md/plan.md의 구체성 자동 검증:
  - ✅ 통과 신호: 파일 경로, 이슈 번호, camelCase/snake_case 심볼, 테스트 러너, 번호화 단계, 수용 기준, 에러 참조, 코드 블록
  - ❌ 차단: ≤15 유효 단어 + 위 신호 없음
- `force:` 접두어로 강제 우회 가능
- 차단 시 clarify로 되돌리지 않고, 사용자에게 구체화 요청 (in-place)

**변경 범위**: `skills/_shared/automation.md` (auto-chain 섹션)

### Tier 2: 중기 적용 (구조적 개선)

#### 3.4 3-lane review → ff-review 고급화

**현재 forgeflow**: review는 단일 패스 (PASS/FAIL + blockers)  
**gajae-code에서 가져올 것**: multi-lane mandatory quality gate

**구체안**:
- high/epic route에서 review를 3-lane으로 확장:
  - **Architecture lane**: 구조 적합성, 경계, 결합도
  - **Product lane**: brief.md Goal Contract 대비 기능 완결성
  - **Code lane**: 코드 품질, 보안, 성능
- 모든 lane이 APPROVE여야 최종 PASS. 하나라도 BLOCK/REQUEST CHANGES면 전체 ITERATE
- medium route에서는 선택적 (architecture + code만)
- small route에서는 단일 패스 유지

**변경 범위**: `skills/ff-review/SKILL.md`, `templates/review-report.md` (3-lane 섹션 추가)

#### 3.5 위상 열거 게이트 → clarify 스코프 락

**현재 forgeflow**: clarify가 바로 세부 requirement로 진입  
**gajae-code에서 가져올 것**: Round 0 topology enumeration

**구체안**:
- clarify의 초기 단계에 "스코프 위상 락" 추가:
  1. 전체 변경 대상을 1-6개 최상위 컴포넌트로 열거
  2. 사용자가 이 위상을 확인 (1회 질문)
  3. 확인 후에만 세부 요구사항 심화 질문 시작
  - 중간에 컴포넌트 추가/변경 시 위상 재확인 필요

**변경 범위**: `skills/clarify/SKILL.md` (새 섹션)

#### 3.6 명시적 핸드오프 상태 → run-state.json

**현재 forgeflow**: 스테이지 전환은 checkpoint.md + run-state.json에 암묵적으로 기록  
**gajae-code에서 가져올 것**: 명시적 handoff phase 상태

**구체안**:
- `run-state.json`에 `handoff` 상태 추가:
  ```json
  {
    "current_stage": "plan",
    "handoff": {
      "from_stage": "clarify",
      "to_stage": "plan",
      "handed_off_at": "2026-06-05T10:00:00Z",
      "caller_demoted": true,
      "callee_promoted": true
    }
  }
  ```
- auto-chain에서 handoff 상태를 원자적으로 업데이트
- context-resume에서 handoff 상태를 먼저 읽어 적절한 복구 경로 선택

**변경 범위**: `templates/run-state.json`, `skills/_shared/context-resume.md`, `scripts/forgeflow_storage.py`

### Tier 3: 장기 검토 (아키텍처 영감)

#### 3.7 롤 에이전트 프롬프트 템플릿화

**구체안**:
- `skills/_shared/`에 롤 에이전트 프롬프트 템플릿 추가:
  - `role-architect.md`: 읽기 전용, 심각도 등급, CLEAR/WATCH/BLOCK + APPROVE/COMMENT/REQUEST CHANGES
  - `role-critic.md`: 읽기 전용, OKAY/ITERATE/REJECT
  - `role-implementer.md`: 자율 구현, scope broadening 금지, compact plan
- ff-review에서 architect/critic 롤을 참조
- execute에서 implementer 롤을 참조
- Hermes delegate_task에서도 이 롤 프롬프트를 활용 가능

**변경 범위**: `skills/_shared/role-*.md` (신규), `skills/ff-review/SKILL.md`, `skills/execute/SKILL.md`

#### 3.8 온톨로지 수렴 추적 (참고)

- gajae-code의 온톨로지 스냅샷+안정성 비율은 복잡도가 높음
- forgeflow의 long-run/evolution rule이 유사 개념 (패턴 학습)
- 장기적으로 clarify에서 도메인 모델 용어 정의를 brief.md에 "Domain Ontology" 섹션으로 간소화吸收 가능
- **당장 적용 불필요** — Tier 3 참고 아이디어로만 유지

## 4. 흡수하지 않을 것 (의도적 배제)

| gajae-code 요소 | 배제 사유 |
|----------------|----------|
| tmux team 오케스트레이션 | forgeflow의 마크다운 전용 범위 초과. Hermes가 이미 delegate_task로 유사 기능 제공 |
| CLI 명령어 시스템 (`gjc`) | forgeflow에 런타임 없음 |
| JSONL 세션 스토리지 | forgeflow는 마크다운 아티팩트 사용 |
| TUI 컴포넌트 시스템 | 완전히 다른 관심사 |
| 플러그인/확장 시스템 | forgeflow는 플랫폼 네이티브 플러그인 사용 |
| Capability 레지스트리 | 과도한 복잡도 (12+ discovery provider) |
| Rust 네이티브 헬퍼 | forgeflow 범위 초과 |
| GPT-5 Harmony leak 감지 | forgeflow와 무관 |

## 5. 구현 로드맵 제안

### Phase 1 (v1.14) — clarify 개선
- [ ] ambiguity 스코어링 + 임계값 게이트
- [ ] 위상 열거 게이트 (Round 0)
- [ ] brief.md 템플릿에 ambiguity/ontology 필드 추가

### Phase 2 (v1.15) — plan/review 강화
- [ ] receipt-only verdict (Self-Critique)
- [ ] 사전 실행 게이트
- [ ] 3-lane review (high/epic)

### Phase 3 (v1.16) — 핸드오프 + 롤
- [ ] 명시적 handoff 상태
- [ ] 롤 에이전트 프롬프트 템플릿
- [ ] run-state.json 스키마 확장

## 6. 참고 출처

- gajae-code 레포: https://github.com/Yeachan-Heo/gajae-code
- forgeflow 레포: https://github.com/gimso2x/forgeflow
- gajae-code 스킬 원문 위치: `packages/coding-agent/src/defaults/gjc/skills/`
- gajae-code 롤 프롬프트 위치: `packages/coding-agent/src/defaults/gjc/agents/`
- forgeflow 스킬 위치: `skills/`
- forgeflow 공유 모듈: `skills/_shared/`
