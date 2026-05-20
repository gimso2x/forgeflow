# oh-my-agent → ForgeFlow 흡수안 리뷰 요청

> **목적**: 외부 레포 oh-my-agent(first-fluke/oh-my-agent, v8.4.0)의 아키텍처 패턴을 ForgeFlow에 흡수할지 검토. 아래 분석과 흡수안을 읽고 피드백을 줘.

---

## oh-my-agent 핵심 아키텍처 요약

- **SSOT 프로젝션**: `.agents/` 디렉토리 하나에서 6개 벤더(Claude, Codex, Gemini, Cursor, Qwen, Antigravity) 네이티브 포맷 자동 생성
- **키워드 자동 감지**: 사용자 프롬프트에서 다국어(7개 언어) 키워드를 감지해 워크플로우/스킬 자동 주입 (triggers.json 3K줄)
- **에이전트 스폰**: `oma agent:spawn` CLI로 서브프로세스 실행, native/external 자동 분기
- **per-agent 모델 라우팅**: 에이전트별로 다른 모델/벤더/preset 설정 (oma-config.yaml)
- **세션 쿼터**: 토큰/스폰 수 벤더별 예산 캡 + 초과 시 차단 (session-cost.ts)
- **워크플로우 3단계**: orchestrate(병렬) / work(순차) / ultrawork(고강도 22K자)
- **SKILL.md 포맷**: Scheduling(목표, intent signature, 입출력, 의존성) / Structural Flow / Logical Operations

기술 스택: TypeScript + Bun, commander.js, biome, Serena MCP, release-please
규모: 78K LOC, 423개 .ts 파일, 1,936개 파일, 28개 스킬, 18개 워크플로우

---

## ForgeFlow 현재 상태

- **v1.0.5**, 순수 마크다운 스킬 (런타임/외부 의존성 없음)
- **파이프라인**: clarify → plan → execute → review → ship (+milestone, long-run, benchmark)
- **지원 벤더**: Claude Code, Codex CLI, Gemini CLI, Cursor (플러그인 방식)
- **강점**: artifact-first, gate 중심, evidence 기반 review, 명시적 산출물 템플릿
- **약점**: 라우트별 실행 패턴 차이 없음, 토큰/세션 관리 없음, 키워드 자동 감지 없음

---

## 제안된 흡수안

### P0 — 즉시 적용

**1. SKILL.md 선언형 포맷 도입**
oma의 Scheduling / Structural Flow / Logical Operations 구조를 ForgeFlow 각 스킬에 적용.
특히 intent signature (키워드 기반 라우팅 정보)를 스킬 자체에 내장.

```
현재 ForgeFlow SKILL.md (skills/clarify/SKILL.md 등):
  - YAML frontmatter (name, description)
  - 마크다운 본문 (절차적 지시)

제안 변경:
  - YAML frontmatter에 intent_signature, inputs, outputs, dependencies 추가
  - 본문에 Scheduling / Structural Flow / Logical Operations 섹션 도입
```

**2. 세션 쿼터 캡 개념**
stage 실행 전 토큰 예산 체크를 프롬프트 레벨에서 강제.
`.forgeflow/quota.yaml` 설정 파일로 per-stage 토큰 가이드라인.
런타임이 없으니 실제 차단 대신 "경고 + 권고" 수준.

### P1 — 중기 적용

**3. 라우트별 실행 패턴 차별화**
현재 small/medium/high 라우트가 있지만 실행 패턴이 다르지 않음.
oma의 orchestrate(병렬)/work(순차)/ultrawork(고강도) 패턴 차용.
high 루트에서만 병렬 에이전트 + 리뷰 루프 강화.

**4. 키워드 자동 감지 → 스킬 자동 선택**
oma의 triggers.json 다국어 키워드 → ForgeFlow clarify에서 자동 라우팅 힌트.
"리뷰해줘" → review, "계획 세워" → plan 자동 매핑.
프롬프트 내 키워드 매칭 테이블 수준에서 구현 가능.

### P2 — 장기 검토

**5. Native/External 디스패치 패턴**
벤더별 최적 실행 경로 자동 선택. 당장은 불필요하나 확장 시 참고.

### 버린 것

- TypeScript CLI 런타임 — ForgeFlow는 순수 마크다운이 핵심 차별점
- Serena MCP 의존 — ForgeFlow는 MCP 클라이언트가 아님
- 벤더별 설정 자동 생성 — ForgeFlow 어댑터가 이미 담당
- 서브프로세스 스폰 — 런타임 없는 게 특징

---

## 리뷰 요청 사항

각 항목에 대해 동의/반대/수정 의견을 줘:

1. **P0-1 (SKILL.md 포맷)**: 선언형 포맷 도입이 ForgeFlow의 단순성을 해치지 않는가? 최소 변경안은?
2. **P0-2 (세션 쿼터)**: 런타임 없는 마크다운 환경에서 토큰 가이드라인을 어떻게 실제로 강제할 수 있나?
3. **P1-3 (라우트 차별화)**: high 루트에만 병렬/리뷰 루프를 넣는 게 실용적인가? 아니면 모든 루트에 선택적으로?
4. **P1-4 (키워드 감지)**: 프롬프트 내 키워드 테이블로 충분한가? 아니면 더 구조적인 접근이 필요한가?
5. **버린 것 중 재검토할 게 있나?** 특히 TypeScript 런타임이나 MCP 통합을 나중에라도 고려해야 하나?
6. **빠뜨린 흡수 포인트가 있나?** oma에서 ForgeFlow에 맞는 패턴을 더 찾아줘.
