# Checkpoint Model

## 목적
checkpoint는 "대충 여기까지 했음" 메모가 아니다.
재개 시 다시 읽을 수 있는 **전술적 state pointer**다.

---

## 왜 필요한가

long-run 작업이나 context compaction이 걸리는 작업은 대화만 믿으면 무조건 꼬인다.
resume 시 필요한 건 감상문이 아니라 아래다.
- 지금 어느 stage인가
- 현재 어떤 task를 붙잡고 있었는가
- 어떤 artifact가 최신 기준인가
- 다음 액션이 무엇인가

이걸 checkpoint가 제공한다.

---

## checkpoint와 다른 artifact의 차이

### `run-state`
현재 route/stage/gate/retry 상태를 기록하는 canonical runtime ledger.

### `plan-ledger`
task 단위 실행 truth.

### `checkpoint`
재개용 tactical pointer.
- 현재 시점의 핵심 참조를 요약한다.
- resume entry를 빠르게 만든다.
- 하지만 canonical truth를 대체하지는 않는다.

즉:
- `run-state` / `plan-ledger` = 진실원천
- `checkpoint` = 재개용 포인터

---

## 권장 위치

### canonical sample
- `examples/artifacts/checkpoint.sample.json`

### runtime usage
- `<task-dir>/checkpoint.json`
또는
- `<task-dir>/checkpoints/<timestamp>.json`

V1에서는 단일 최신 checkpoint로 시작해도 충분하다.

---

## 최소 필드

- `schema_version`
- `task_id`
- `route`
- `current_stage`
- `current_task_id`
- `plan_ref`
- `plan_ledger_ref`
- `run_state_ref`
- `latest_review_ref`
- `next_action`
- `open_blockers[]`
- `updated_at`

---

## 생성 시점

checkpoint는 최소 아래 시점에 생성 가치가 있다.
1. phase completion 직후
2. retry budget 소진 직전
3. user handoff 전
4. context compaction 또는 종료 직전
5. long-run route 진입 시

모든 툴 호출마다 쓰는 건 미친 짓입니다. 그건 noisy log지 checkpoint가 아닙니다.

---

## resume 규칙

resume 시 절차는 아래 순서여야 한다.
1. checkpoint 읽기
2. `plan_ref`, `plan_ledger_ref`, `run_state_ref` 다시 열기
3. 참조 artifact가 유효한지 검증
4. `current_stage` / `current_task_id` 정합성 확인
5. `next_action`에서 재개

핵심:
**checkpoint만 믿고 바로 진행하면 안 된다. 항상 원본 artifact를 재조회한다.**

---

## blocker 규칙

`open_blockers`는 비어 있을 수 있다.
하지만 blocker가 있으면 success처럼 포장하면 안 된다.
checkpoint는 unresolved blocker를 숨기지 말고 드러내야 한다.

---

## V1 원칙

- checkpoint는 tactical resume 도우미다.
- canonical truth는 아니다.
- 요약이 아니라 pointer여야 한다.
- next action은 한 줄로 구체적이어야 한다.
- broken reference를 가진 checkpoint는 실패로 본다.
