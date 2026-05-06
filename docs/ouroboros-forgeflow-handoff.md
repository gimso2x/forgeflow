# Ouroboros → ForgeFlow 흡수안

대상: `Q00/ouroboros` 레포의 핵심 개념을 ForgeFlow에 흡수하기 위한 개발 핸드오프 문서

## 결론

Ouroboros는 ForgeFlow에 별도 기능으로 추가하지 않고, ForgeFlow의 `clarify → plan → run → review → ship` 흐름을 더 엄격하게 만드는 재료로 흡수한다.

핵심은 다음 세 가지다.

- 명세를 먼저 고정한다.
- 실행과 검증을 분리한다.
- runtime/backend 차이를 adapter로 분리한다.

## 반영 상태

- P0-1 완료: `skills/clarify`에 ambiguity/open questions/non-goals/Socratic clarification 규칙을 강화했다.
- P0-2 완료: `skills/review`에 observed evidence only, blocker-first verdict, self-report 분리 규칙을 강화했다.
- P0-3 완료: `skills/plan`에 requirement traceability, contracts/journeys, orphan work 금지 규칙을 강화했다.
- P1-4 완료: `docs/runtime-adapters.md`에 backend capability matrix와 adapter boundary를 추가했다.
- P1-5 완료: `skills/review`는 `large_high_risk`에서 spec review와 quality review를 분리하도록 명시한다.
- P1-6 완료: `skills/run`과 `skills/review`는 evidence/decision artifacts를 남기고 review 결과를 재사용 가능한 artifact로 환원하도록 유지한다.

## 가져온 것

### 1) Socratic clarification

- 모호한 요구를 질문으로 분해
- hidden assumptions 노출
- constraints / non-goals / acceptance criteria 명시
- ambiguity를 artifact에 기록

ForgeFlow 적용 위치:

- `skills/clarify`
- `brief.json`

### 2) Spec-first workflow

- 실행 전에 brief/plan을 명세로 고정
- scope boundary를 먼저 확정
- 계획은 실행 가능한 계약 문서가 되어야 함

ForgeFlow 적용 위치:

- `skills/clarify`
- `skills/plan`

### 3) 독립 검증 gate

- worker self-report를 신뢰하지 않음
- review는 실제 코드/출력/evidence를 기준으로 판단
- blocker-first verdict 유지

ForgeFlow 적용 위치:

- `skills/review`
- `review-report.json`

### 4) Runtime adapter 사고

- Claude / Codex / Hermes / OpenCode 같은 backend 차이를 workflow와 분리
- stage별로 적절한 backend를 쓸 수 있게 문서화

ForgeFlow 적용 위치:

- `docs/runtime-adapters.md`
- backend capability matrix

### 5) Evolve 루프

- 작업 후 개선점을 문서/스킬/스키마로 환원
- 반복 자체보다 재사용 가능한 개선물을 남김

ForgeFlow 적용 위치:

- skill update
- docs update

## 버린 것

- 과도한 철학적 서사
- phase 이름의 추가만 늘리는 구조
- ontology 자체가 목적이 되는 복잡성
- 운영 복잡도만 늘리는 거대 오케스트레이터화

## 한 줄 요약

Ouroboros는 ForgeFlow에 별도 제품으로 붙이는 것이 아니라, `clarify / plan / run / review`의 artifact-first gate를 더 엄격하게 만드는 재료로 흡수했다.
