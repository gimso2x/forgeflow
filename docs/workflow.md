# Workflow

## 목적
새 harness의 실행 흐름을 stage 기준으로 고정한다.
이 문서는 stage 의미와 전환 규칙을 설명한다.
실제 기계 판정은 `policy/canonical/*.yaml`과 `schemas/*.json`이 맡는다.

---

## 1. Stage overview

### 1) `clarify`
목표:
- 요청을 실행 가능한 단위로 정리한다.
- 성공 조건, 비목표, 제약, 리스크를 명시한다.

입력:
- user request
- project context
- existing constraints

출력:
- `brief`

실패 조건:
- 핵심 요구가 모호한데도 추측으로 넘어가려 할 때

---

### 2) `plan`
목표:
- 작업을 실행 가능한 순서와 검증 단위로 쪼갠다.

입력:
- `brief`

출력:
- `plan`
- 필요 시 `decision-log` 초기 항목

규칙:
- plan은 서술문이 아니라 executor input이어야 한다.
- 각 단계는 기대 산출물과 검증 방법을 가져야 한다.

---

### 3) `execute`
목표:
- 승인된 brief/plan 기준으로 실제 작업을 수행한다.

입력:
- `brief`
- `plan` (medium 이상)

출력:
- `decision-log`
- `run-state`
- 필요 시 작업 결과물 참조

규칙:
- 실행 중 중요한 변경 판단은 `decision-log`에 남긴다.
- 상태 변화는 `run-state`에 반영한다.
- spec을 묵시적으로 다시 쓰면 안 된다.

---

### 4) `spec-review`
목표:
- 원하는 걸 맞게 만들었는지 본다.

입력:
- `brief`
- `plan`
- `run-state`
- evidence

출력:
- `review-report` (`review_type=spec`)

규칙:
- worker 자기보고는 증거가 아니다.
- acceptance criteria 기준으로 통과/실패를 판정한다.
- 실패하면 quality-review로 넘어가지 않는다.

---

### 5) `quality-review`
목표:
- 결과물이 유지보수 가능하고 검증 가능하며 위험이 통제되는지 본다.

입력:
- spec review 통과 결과
- `run-state`
- evidence

출력:
- `review-report` (`review_type=quality`)

규칙:
- 구조, 단순성, 테스트/검증 품질, 잔존 리스크를 본다.
- spec 미충족을 품질 문제로 얼버무리면 안 된다.

---

### 6) `finalize`
목표:
- 현재 작업을 종료 가능한 상태로 마감한다.

입력:
- `run-state`
- review 결과

출력:
- finalized `run-state`
- 필요 시 handoff note

규칙:
- 모든 필수 gate를 통과해야 한다.
- unresolved risk는 숨기지 않고 남긴다.

---

### 7) `long-run`
목표:
- 반복 가치가 있는 학습만 축적한다.

입력:
- finalized state
- review 결과

출력:
- `eval-record`
- optional memory note

규칙:
- 세션 잡담을 memory로 던지지 않는다.
- 재사용 가능한 패턴, 실패 규칙, 평가 결과만 남긴다.

---

## 2. Complexity routing

### small
`clarify -> execute -> quality-review -> finalize`

적용 대상:
- 저위험 단건 수정
- 짧은 문서 보정
- 구조 영향이 적은 변경

### medium
`clarify -> plan -> execute -> quality-review -> finalize`

적용 대상:
- 여러 파일에 걸치는 기능/리팩터
- 구현 전에 순서 분해가 필요한 작업

### large/high-risk
`clarify -> plan -> execute -> spec-review -> quality-review -> finalize -> long-run`

적용 대상:
- 아키텍처 영향
- 배포/운영/데이터 손실 위험
- 긴 실행 시간과 재개 가능성이 중요한 작업

---

## 3. Non-negotiable rules
1. artifact 없는 stage 전환 금지
2. worker와 reviewer 분리
3. spec-review 실패 시 quality-review 금지
4. runtime adapter가 workflow semantics를 바꾸면 안 됨
5. bounded recovery만 허용
6. 작은 일까지 무조건 full process 강제 금지
