---
schema: research-handoff/v1
created: 2026-06-03
author: 02. Hermes 탐색
status: ready
audience: ForgeFlow developer
---

# Thin Harness 비교 분석 및 ForgeFlow 적용 핸드오프

## 배경

"모델이 좋아지면 무거운 하네스의 수명은 짧아지고, 얇게 직접 깎은 하네스의 가치는 올라간다"는 전제 아래, 한국 AI 코딩 커뮤니티에서 등장한 세 프로젝트를 실제 레포 기준으로 분석하고 ForgeFlow에 적용할 수 있는 패턴을 도출한다.

---

## 1. 세 프로젝트 요약

### 1.1 LazyCodex (code-yeongyu/lazycodex)

**기반:** OmO(oh-my-openagent) 기반, 현재 OpenCode용 배포판
**핵심:** ULW (Ultrawork Loop) — 4역할 팀 구조

| 항목 | 내용 |
|---|---|
| 스타 | [60.8k](https://github.com/code-yeongyu/oh-my-openagent) (OmO 코어) |
| 커밋 | 11 (alpha 단계) |
| 명령 | `$ulw-plan` → `plans/` 산출, `$start-work` → 체크리스트 실행, `$ulw-loop` → 최대 500회 자동 반복 |
| 역할 | Sisyphus(지휘), Hephaestus(구현), Oracle(검증), Librarian(맥락 관리) |
| 철학 | 한 번 훅 입력하면 목표만 주면 알아서 돌아가는 "게으른" 자동화 |

**피드 vs 실제:** 피드 설명은 구조적으로 정확. 다만 현재 Codex가 아닌 OpenCode 기반으로 전환된 점, alpha(11커밋)임을 고려해야 함.

---

### 1.2 Gajae-Code (Yeachan-Heo/gajae-code)

**기반:** 자체 런타임 (tmux 오케스트레이션, Dockerfile 포함)
**핵심:** 4스킬 수렴 구조 — "기본 스킬 동물원을 만들지 않는다"

| 항목 | 내용 |
|---|---|
| 커밋 | 294 (PoC 이상으로 성숙) |
| 언어 | Rust + TypeScript + Python |
| 명령 | `deep-interview` → `ralplan` → `ultragoal` (기본), `team` (병렬 시) |
| 역할 | executor, architect, planner, critic |
| 핵심 루프 | ralplan이 자기 비판(critic)까지 수행 — plan + self-critique를 하나로 |

**피드 vs 실제:** 피드가 "PoC"라고 표현했으나 실제는 294커밋의 성숙 프로젝트. Rust+TS+Python 다중 언어, Dockerfile까지 갖춘 엔지니어링. 그러나 철학은 정확히 맞음 — 스킬 수를 최소화하고 "하나의 쓸모 있는 루프"로 수렴.

---

### 1.3 Roach-Pi (tmdgusya/roach-pi)

**기반:** pi 코딩 에이전트 위에 확장 (런타임은 pi 그대로)
**핵심:** Goal Contract — "모호한 요청이 모호한 코드가 되면 안 된다"

| 항목 | 내용 |
|---|---|
| 커밋 | 452 |
| 릴리즈 | 67 |
| 언어 | TypeScript |
| 명령 | `/setup` → `/clarify` → `/goal` → `/review` |
| 확장 | 8개 (FFF Extension, pi-lsp-client, MCP Adapter, Workspace Memory 등) |
| 워크플로우 | /clarify → Goal Contract(목표, 범위, 성공기준, 증거, 리스크) → /goal → verifier PASS까지 자동 |

**피드 vs 실제:** 피드가 가장 크게 과소평가. 452커밋·67릴리즈·8확장의 성숙한 플랫폼. "pi 위에 얹기"가 단순한 선택이 아니라 의도적인 아키텍처 결정 — 런타임 재작성 비용을 피하고 확장에 집중.

---

## 2. 공통 패턴 비교

| 차원 | LazyCodex | Gajae-Code | Roach-Pi | ForgeFlow(현재) |
|---|---|---|---|---|
| **런타임** | OmO 기반 | 자체(Rust+tmux) | pi 기반 | 런타임 없음(Markdown만) |
| **진입점** | `$ulw-*` 훅 | 스킬 명령 | `/slash` 명령 | `/forgeflow:*` |
| **모호성 해소** | Librarian이 맥락 관리 | deep-interview | /clarify → Goal Contract | clarify 스킬 |
| **계획** | $ulw-plan (plans/) | ralplan(+자기비판) | Goal Contract | ff-plan 스킬 |
| **실행** | Hephaestus + loop | ultragoal | /goal (PASS까지) | execute 스킬 |
| **검증** | Oracle | critic(ralplan 내장) | verifier(PASS) | ff-review 스킬 |
| **루프** | 최대 500회 ULW | ultragoal 추적 | /goal 자동 반복 | 단방향 파이프라인 |
| **역할 분리** | 4역할 명시 | 4역할 명시 | 1 역할 + 확장 | 4역할(stage 기반) |
| **복잡도 라우팅** | 없음 | 없음 | 없음 | small/medium/high/epic |
| **학습/진화** | 없음 | 없음 | 없음 | evolution rules + long-run |
| **스킬 수** | ULW 3개 | 4개 | 명령 4개 + 확장 8개 | 7 스테이지 + 공유 4개 |

### 핵심 차이점

**ForgeFlow가 갖고 있고 셋 다 없는 것:**
- 복잡도 라우팅 (small/medium/high/epic)
- 학습/진화 시스템 (evolution rules)
- 멀티 어댑터 지원 (Claude/Codex/Gemini/Cursor)

**셋 다 갖고 있고 ForgeFlow가 약한 것:**
- 자동 루프 (ForgeFlow는 단방향 파이프라인)
- 모호성 → 명확한 Goal Contract 강제 변환 (ForgeFlow는 있으나 roach-pi만큼 엄격하지 않음)
- plan 단계에서 self-critique 내장 (ForgeFlow는 plan과 review가 분리)

---

## 3. ForgeFlow 적용 포인트

### P0 — 거의 무료, 즉시 적용

#### 3.1 brief.md에 Goal Contract 강화

roach-pi의 Goal Contract 패턴을 현재 brief.md에 통합.

**변경 대상:** `templates/brief.md`

**추가 필드 (인수 기준 섹션 확장):**

```markdown
## Goal Contract
- **성공 기준 (Success Criteria):** <!-- 작업 완료의 객관적 조건 -->
- **필수 증거 (Evidence Required):** <!-- PASS 판정에 필요한 관찰 가능 결과 -->
- **인정된 리스크 (Accepted Risks):** <!-- 알고 감수하는 리스크 목록 -->
- **명시적 제외 (Explicit Exclusions):** <!-- 하지 않는 것 명시 -->
```

**이유:** 현재 Acceptance Criteria는 체크리스트지만, "어떤 증거로 PASS인지"가 명시되지 않으면 review가 주관적으로 흔들림. roach-pi의 verifier가 엄격하게 작동하는 이유가 Goal Contract에 있음.

**검증:** 기존 brief.md와 호환 — 새 섹션이 비어 있어도 기존 파이프라인이 깨지지 않아야 함.

---

#### 3.2 review-report.md에 blockers 강제 PASS 규칙

**변경 대상:** `skills/ff-review/SKILL.md` 판정 섹션

**추가 규칙:**

```markdown
## 판정 강제 규칙
- `approved` 판정은 Open Blockers 배열이 비어 있을 때만 허용
- blockers가 하나라도 있으면 `changes_requested` 또는 `blocked`로 강제
- "minor" blocker라는 카테고리 없음 — blocker는 blocker
```

**이유:** roach-pi는 verifier가 PASS를 주지 않으면 루프가 멈춤. ForgeFlow는 reviewer가 "대부분 괜찮으니 approved"를 줄 여지가 있음. 강제 규칙으로 이를 막음.

---

### P1 — 구조 변경 없이 스킬 수정

#### 3.3 plan 단계에 critic 루프 추가

gajae-code의 ralplan 패턴 참고. plan 산출 후 내장 critic이 한 번 더 비판.

**변경 대상:** `skills/ff-plan/SKILL.md`

**추가 단계:**

```markdown
## Self-Critique Loop (plan 산출 후)

plan.md 초안 완성 후, 다음 질문에 답하는 Critic 섹션을 plan.md에 추가:
1. 이 계획으로 인수 기준을 모두 만족할 수 있는가?
2. 의존성 누락이나 순서 오류가 있는가?
3. 검증 단계가 관찰 가능한 증거를 산출하는가?

Critic이 PASS를 주지 않으면 plan을 수정 후 재검토 (최대 3회).
Critic 섹션은 plan.md에 기록하여 review 단계에서 투명하게 노출.
```

**이유:** 현재 ForgeFlow는 plan과 review가 분리되어 있어, plan 자체의 논리적 오류가 execute 단계까지 전파됨. gajae-code는 이를 ralplan 안에서 해결.

---

#### 3.4 small 라우트 3-stage 축소

**변경 대상:** `skills/forgeflow/SKILL.md` Route model

**현재:** small = clarify → execute → review → ship
**제안:** small = clarify → execute → ship (review 생략, execute 마지막에 self-check만)

**조건:** brief.md의 Goal Contract 증거 기준을 execute 마지막에 self-verify하고, 문제가 있으면 사용자에게 수동 review를 권장.

**이유:** 1-2파일 변경에 4스테이지는 과한 오버헤드. 세 프로젝트 모두 작은 작업에는 가벼운 루프를 사용.

---

### P2 — 아키텍처 확장

#### 3.5 모델 라우팅 레이어

현재 ForgeFlow는 "Model binding"을 heuristic으로만 언급 (forgeflow SKILL.md L197-201). 이를 manifest 레벨에서 선언적으로 만듦.

**변경 대상:** 새 파일 또는 `skills/forgeflow/SKILL.md` 확장

**설계 초안:**

```yaml
# model_routing.yaml (또는 manifest.yaml 섹션)
stage_model_tiers:
  clarify: reasoning    # 강한 추론 모델
  ff-plan: reasoning   # 계획 수립
  execute: coding      # 코딩 전용
  ff-review: reasoning # 독립 검증
  ship: fast           # 기계적 정리
```

**이유:** gajae-code와 lazyodex는 각 역할에 다른 모델을 사용하는 패턴을 보여줌. ForgeFlow는 이미 prompt에 이를 언급하지만 실행 수단이 없음.

---

#### 3.6 evolution → workspace memory 단순화

현재 ForgeFlow의 long-run/evolution은 관찰→추출→활성→은퇴의 4단계 파이프라인. 이를 단순화.

**제안:**
- ship 단계에서 `eval-record.md`에 핵심 학습 1-2줄만 기록
- clarify/plan 단계에서 관련 eval-record를 읽어 맥락에 반영
- evolution rules는 P2에서 도입, 초기에는 eval-record만 사용

**이유:** 세 프로젝트 모두 학습 시스템이 없음. ForgeFlow의 evolution은 잘 설계되어 있으나 실제 사용 빈도에 비해 무거움. MVP로 workspace memory만 유지.

---

### P3 — 장기

#### 3.7 worktree 격리 + 병렬 실행

roach-pi의 확장 구조와 lazyodex의 fan-out 패턴 참고.

**제안:**
- `/flow-feature` 진입 시 자동 worktree 생성
- task_dir를 worktree에 매핑
- 병렬 worker는 각각 다른 worktree에서 실행

**이유:** 현재 ForgeFlow의 fan-out/fan-in 패턴은 스펙에만 있고 구현 수단이 없음. worktree 격리는 안전한 병렬 실행의 전제 조건.

---

## 4. 우선순위 요약

| 우선순위 | 항목 | 변경 대상 | 난이도 | ForgeFlow와의 호환성 |
|---|---|---|---|---|
| P0 | Goal Contract 강화 | templates/brief.md | 낮음 | 완전 호환 (추가 섹션) |
| P0 | blockers 강제 PASS | ff-review SKILL.md | 낮음 | 완전 호환 (규칙 추가) |
| P1 | plan critic 루프 | ff-plan SKILL.md | 중간 | 호환 (plan.md에 섹션 추가) |
| P1 | small 3-stage 축소 | forgeflow SKILL.md | 중간 | 기존 라우트에 추가 |
| P2 | 모델 라우팅 | manifest/skill 확장 | 높음 | 새 개념 도입 |
| P2 | evolution 단순화 | long-run/ship SKILL.md | 중간 | 기존 축소 |
| P3 | worktree 격리 | 새 인프라 | 높음 | 아키텍처 확장 |

---

## 5. 출처

- [LazyCodex](https://github.com/code-yeongyu/lazycodex) — 11 commits, OmO 기반, ULW 루프
- [OmO (oh-my-openagent)](https://github.com/code-yeongyu/oh-my-openagent) — 60.8k stars, 코어 엔진
- [Gajae-Code](https://github.com/Yeachan-Heo/gajae-code) — 294 commits, Rust+TS+Python, ralplan/ultragoal
- [Roach-Pi](https://github.com/tmdgusya/roach-pi) — 452 commits, 67 releases, 8 확장, pi 기반
