# oh-my-agent → ForgeFlow 흡수안 (최종)

> **출처**: [first-fluke/oh-my-agent](https://github.com/first-fluke/oh-my-agent) v8.4.0 분석  
> **대상**: ForgeFlow v1.0.5  
> **리뷰**: Codex / Claude Code / Gemini CLI 3모델 교차 검토 완료  
> **날짜**: 2026-05-21

---

## 한 줄 결론

oh-my-agent에서 가져올 건 **"런타임 자동화"가 아니라 "명시적 구조화와 라우팅 보조 패턴"**이다. ForgeFlow의 `markdown-only`, `no-runtime`, `artifact-first` 원칙은 유지한다.

---

## oh-my-agent 핵심 아키텍처 (참고용)

| 항목 | 내용 |
|------|------|
| SSOT 프로젝션 | `.agents/` 하나에서 6개 벤더 포맷 자동 생성 |
| 키워드 자동 감지 | 7개 언어 키워드 → 워크플로우/스킬 자동 주입 |
| 에이전트 스폰 | `oma agent:spawn` CLI, native/external 자동 분기 |
| per-agent 모델 라우팅 | 에이전트별 모델/벤더/preset 설정 |
| 세션 쿼터 | 토큰/스폰/벤더별 예산 캡 |
| 워크플로우 3단계 | orchestrate(병렬) / work(순차) / ultrawork(고강도) |
| SKILL.md 포맷 | Scheduling / Structural Flow / Logical Operations |
| 규모 | TypeScript 78K LOC, 28개 스킬, 18개 워크플로우 |

---

## 버릴 것 (ForgeFlow와 안 맞는 것)

- TypeScript CLI 런타임 (Bun, commander.js)
- 서브프로세스 기반 agent spawn
- Serena / MCP 의존
- 세션 토큰 하드 차단
- 전역 키워드 자동 주입 엔진 (triggers.json 3K줄)
- 벤더별 설정 자동 생성 시스템
- Native/External dispatch 분기

이유: ForgeFlow는 순수 마크다운, 런타임 없음, 외부 의존성 없음이 핵심 차별점.

---

## 가져갈 것 (최종 수정 포인트)

### P0-1. SKILL.md 선언형 메타 강화

**대상**: `skills/forgeflow/SKILL.md`, `skills/clarify/SKILL.md` (핵심 스킬만)

기존 YAML frontmatter에 다음 필드를 **선택적으로** 추가:

```yaml
---
name: clarify
description: 요구사항 정리 → brief.md
validate_prompt: ...
# ↓ 추가
intent: "사용자 요청을 분석해 route, specialists, verification gates를 결정"
inputs:
  - user_request: string
outputs:
  - brief.md: artifact
dependencies: []
---
```

**주의사항**:
- **모든 스킬에 강제하지 않는다**. 핵심 라우팅/검증 스킬만.
- oma의 `Scheduling / Structural Flow / Logical Operations`를 통째로 이식하지 않는다.
- 기존 `validate_prompt` 체계와 충돌하지 않게, 본문 섹션으로 보강하는 수준.

---

### P0-2. clarify 라우팅 보조 강화

**대상**: `skills/clarify/SKILL.md` 본문

clarify 스킬의 route selection 규칙에 다음을 추가:

1. **specialist hint** — 작업 성격에 따라 필요한 전문가를 판단
   - 예: 인증 관련 → security specialist, UI 관련 → UX specialist
2. **route rationale** — 왜 이 route를 선택했는지 brief에 명시
3. **suggested next skill** — 다음에 실행할 스킬을 추천

키워드 감지는 **별도 엔진이 아니라 clarify의 scoring 문맥 안에서 보조 힌트**로만 사용:

```
"리뷰해줘" → review 우선
"계획 세워" → plan 우선
"버그" → execute → review
```

대형 triggers.json(3K줄)을 가져오지 않고, **소규모 alias 표** 수준에서 시작.

---

### P1-1. high/epic 라우트 실행 패턴 차별화

**대상**: `skills/forgeflow/SKILL.md`, `skills/review/SKILL.md`

현재 small/medium/high/epic 라우트가 있지만 **실행 패턴이 다르지 않다**. 다음을 명시:

| 라우트 | plan | execute | review |
|--------|------|---------|--------|
| small | skip | 직접 구현 | quality-review only |
| medium | plan.md | 단일 worker | quality-review |
| high | plan.md 상세 | 병렬 worker 가능 | spec-review + quality-review 분리 |
| epic | roadmap.md → plan.md | 마일스톤별 병렬 | spec + quality + specialist review |

이건 새 패턴 도입이 아니라 **기존 route model의 실행 전략을 문서화하는 것**.

---

### P1-2. brief.md / plan.md 템플릿 계약 강화

**대상**: `templates/brief.md`, `templates/plan.md`

다음 필드를 템플릿에 추가:

**brief.md**:
- `route_rationale`: route 선택 이유
- `suggested_specialists`: 필요한 전문가 목록
- `budget_note`: 예상 규모/복잡도에 대한 가이드 (강제 아님)
- `suggested_next_skill`: 다음 실행 스킬

**plan.md**:
- `execution_pattern`: 라우트별 실행 전략 참조
- `verification_plan`: 각 단계별 검증 방식
- `dependencies`: 작업 간 의존성

---

### P2. 세션 가이드라인 (advisory)

**대상**: `docs/` 또는 `.forgeflow/` 설정

런타임이 없으므로 **하드 차단이 아니라 가이드라인**으로 제공:

```yaml
# .forgeflow/guidelines.yaml (선택적)
budget:
  small: "단일 파일 변경 수준"
  medium: "2-5일 작업, 1-3개 파일 그룹"
  high: "1-2주 작업, 다중 파일/컴포넌트"
  epic: "스프린트 단위, 마일스톤 분해 필수"
```

강제가 아니라 brief/review 시점의 **체크리스트 항목**으로 활용.

---

## 모델별 리뷰 요약

### Codex
- 구조화는 좋지만 자동 라우팅 엔진으로 가면 과하다
- 핵심 스킬부터 점진 적용이 안전
- 세션 쿼터는 advisory 수준이 현실적

### Claude Code
- ForgeFlow 정체성(명시적 stage workflow) 유지가 우선
- 전면 스키마 확장보다는 `validate_prompt` + 본문 정리 수준
- "자동 라우팅 시스템"이 아니라 "명시적 stage contract 보강"

### Gemini CLI
- 키워드 감지는 clarify의 scoring 문맥에 넣는 게 자연스럽
- 대형 trigger 시스템은 과함
- GEMINI.md에 새 메타스키마를 많이 넣기보다 기존 구조 내 강화

---

## 다음 액션

1. `skills/forgeflow/SKILL.md`에 `intent / inputs / outputs / dependencies` frontmatter 추가
2. `skills/clarify/SKILL.md`에 specialist hint, route rationale, suggested next skill 보강
3. `templates/brief.md`, `templates/plan.md`에 새 필드 추가
4. `skills/forgeflow/SKILL.md`에 라우트별 실행 전략 표 추가
5. `docs/`에 advisory 가이드라인 문서 작성 (`docs/advisory-guidelines.md`, advisory only)

---

## 참고 파일

- 흡수안 리뷰 문서: `docs/oh-my-agent-absorption-review.md`
- oh-my-agent 분석 노트: `Obsidian/notes/oh-my-agent-repo-analysis.md`
- ForgeFlow AGENTS.md: `AGENTS.md`
- 기존 핸드오프 문서: `docs/ouroboros-forgeflow-handoff.md`, `docs/revfactory-harness-forgeflow-handoff.md`
