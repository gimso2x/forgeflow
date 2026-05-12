# AI 팀 운영 영상 → ForgeFlow 적용 핸드오프

대상: YouTube 영상 *프론트엔드 개발자는 AI를 어떻게 활용할까? | AI슬쩍 EP.01* 의 운영 방식 중 ForgeFlow에 흡수할 요소를 정리한 개발 핸드오프 문서

## 결론

이 영상은 ForgeFlow의 본체를 바꾸는 제안이 아니라, 기존 `clarify → plan → execute → review → ship` 흐름을 더 잘 쓰게 만드는 운영 방식의 참고 사례다.

핵심은 다음 세 가지다.

- 역할별 에이전트를 분리한다.
- 플랜과 회의록을 먼저 쌓고 구현은 그 다음에 간다.
- AI 결과를 그대로 믿지 않고 사람이 최종 판단한다.

## 흡수할 것

### 1) 역할 분리된 AI 팀

영상에서는 Planner, Reviewer, QA, UX, Security 같은 역할을 분리해서 운영한다. ForgeFlow에도 같은 원리를 적용할 수 있다.

ForgeFlow 적용 위치:

- `clarify` 단계: 요청을 역할 단위로 나눌지 결정
- `plan` 단계: 역할별 task 분해
- `execute` 단계: task별 worker 라우팅
- `review` 단계: reviewer / QA / security 관점 분리

### 2) 역할별 전용 문맥 파일

영상의 핵심 패턴은 각 에이전트가 자기 역할에 맞는 마크다운 지식 파일을 읽는 방식이다.

ForgeFlow 적용 위치:

- `adapters/targets/codex/agents/*.md`
- `adapters/targets/claude/agents/*.md`
- project-local preset / skill 문서

추천 파일 예시:

- `forgeflow-planner.md`
- `forgeflow-worker.md`
- `forgeflow-spec-reviewer.md`
- `forgeflow-qa.md`
- `forgeflow-security.md`
- `forgeflow-ux.md`

### 3) 플랜 우선, 구현 후행

영상에서는 바로 코딩하지 않고 먼저 플랜, 회의록, 쟁점 정리를 한다. ForgeFlow의 artifact-first 철학과 정확히 맞는다.

ForgeFlow 적용 위치:

- `brief.json`
- `plan-ledger.json`
- `review-report.json`
- stage별 artifact 기록

### 4) AI 1차 검토 + 사람 최종 판단

영상에서는 AI가 리뷰 코멘트를 내더라도, 사람이 실제 맥락을 보고 코멘트 여부를 다시 판단한다.

ForgeFlow 적용 위치:

- `review` 단계
- `review-report.json`
- evidence 기반 gate

이 규칙을 강화하면 좋다.

- AI가 지적한 항목은 자동 반영하지 않는다.
- 실제 영향도와 프로젝트 맥락을 다시 확인한다.
- 중요도가 낮으면 코멘트를 버릴 수 있어야 한다.

### 5) 필요한 에이전트만 켠다

영상에서는 모든 에이전트를 항상 돌리지 않고, 작업에 필요한 역할만 띄운다. ForgeFlow도 같은 원리로 토큰과 복잡도를 줄일 수 있다.

ForgeFlow 적용 위치:

- route selection
- worker dispatch
- reviewer/QA/security의 on-demand 활성화

## 버릴 것

- AI 팀을 무한정 늘리는 구조
- 모든 역할을 항상 상시 구동하는 구조
- AI 코멘트를 자동 정답으로 취급하는 방식
- 기획/검증 없이 바로 구현에 들어가는 습관

## 파일별 반영 포인트

### `docs/workflow.md`

- 역할 분리 원칙
- 플랜 우선 원칙
- 사람 최종판단 원칙

### `docs/review-model.md`

- AI 1차 리뷰 후 사람 재판단
- evidence 없는 코멘트는 약한 신호로 취급
- reviewer 역할 정의 강화

### `docs/architecture.md`

- 멀티 에이전트 팀 구조
- CEO / Planner / Worker / Reviewer / QA / UX / Security 개념 정리
- 필요한 에이전트만 활성화하는 라우팅

### `adapters/targets/*/agents/*.md`

- 역할별 지식 파일
- 각 역할의 금지 사항과 판단 기준
- 프로젝트 문맥이 들어가는 자리

### `memory/README.md` 또는 versioned memory

- 전문화가 품질을 올린다는 운영 규칙
- 에이전트 수는 on-demand로 제한한다는 규칙
- 사람 최종판단이 필요하다는 규칙

## 구현 방향

1. 역할별 에이전트 문서를 정리한다.
2. planner / reviewer / QA의 책임 경계를 분명히 한다.
3. `plan-ledger`와 `review-report`에 회의록/판단 근거가 남도록 한다.
4. 토큰 절약을 위해 필요한 역할만 호출하도록 라우팅을 정리한다.
5. AI 결과를 반영하기 전에 사람이 한 번 더 판단하는 규칙을 명시한다.

## 한 줄 요약

이 영상은 ForgeFlow에 "AI 팀"을 추가하자는 얘기가 아니라, ForgeFlow의 기존 stage 위에 **역할 분리 + 플랜 우선 + 사람 최종판단**을 더 엄격하게 얹자는 참고 사례다.
