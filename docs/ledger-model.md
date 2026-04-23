# Ledger Model

## 목적
`plan`은 사람이 읽는 실행 문서다. `plan-ledger`는 runtime이 믿는 상태다.
이 둘을 분리해서, 문서 설명과 기계 판정이 서로 다른 책임을 갖게 만든다.

---

## 왜 필요한가

`plan` 하나로 intent와 runtime state를 같이 처리하면 꼭 이런 일이 생긴다.
- task 상태가 markdown 문장에 묻힘
- retry/blocker/evidence가 chat에만 남음
- review가 현재 상태를 재구성하느라 헛고생함
- resume 시 무엇이 끝났는지 확신을 못 함

그래서 V1에서는 `plan-ledger`를 추가한다.

---

## 책임 분리

### `plan`
사람용 문서.
- 무엇을 하려는가
- 왜 그 순서인가
- 어떤 verification을 붙일 것인가
- 어떤 fallback이 있는가

### `plan-ledger`
기계용 상태.
- 지금 어떤 task가 pending/running/done/blocked 인가
- 어떤 verification gate가 붙었는가
- evidence ref가 무엇인가
- retry 횟수는 얼마인가
- 현재 blocker가 무엇인가

핵심은 단순하다.
**plan은 의도, ledger는 실행 truth.**

---

## 권장 위치

### canonical sample
- `examples/artifacts/plan-ledger.sample.json`

### runtime usage
- `<task-dir>/plan-ledger.json`

---

## 최소 필드

- `schema_version`
- `task_id`
- `route`
- `current_task_id`
- `contracts_ref`
- `tasks[]`
  - `id`
  - `title`
  - `depends_on[]`
  - `files[]`
  - `parallel_safe`
  - `status`
  - `required_gates[]`
  - `evidence_refs[]`
  - `attempt_count`
  - `blocked_reason`
- `last_review_verdict`

---

## task 상태값

권장 enum:
- `pending`
- `in_progress`
- `done`
- `blocked`
- `cancelled`

`done`는 required gate와 evidence가 충족될 때만 의미가 있다.
그냥 작업자가 끝났다고 우기는 건 상태값이 아니다.

---

## gate 타입

권장 enum:
- `machine`
- `validator`
- `scenario`
- `human`

각 task는 필요한 gate만 가진다.
모든 task에 full-course 검증을 강제하지 않는다.

---

## contracts_ref

병렬 작업이나 interface churn이 없으면 비어 있어도 된다.
있다면 `docs/contracts/<slug>.md` 같은 명시적 경로를 가리킨다.

---

## runtime 규칙

1. multi-step route에서는 ledger가 runtime truth다.
2. `current_task_id`는 `tasks[]` 안의 실제 id를 가리켜야 한다.
3. `done` task는 근거 없는 빈 `evidence_refs`로 끝나면 안 된다.
4. `blocked` task는 `blocked_reason`이 필요하다.
5. retry는 `attempt_count`로 남긴다.
6. review는 markdown plan만 보지 말고 ledger도 같이 본다.

---

## review와의 관계

### spec-review가 보는 것
- plan intent
- current task completion 여부
- acceptance criteria와 evidence 정합성

### quality-review가 보는 것
- verification quality
- blocker 처리 상태
- retry/recovery의 건전성

ledger가 없으면 이 두 리뷰가 다 chat archaeology가 된다.
그건 하네스가 아니라 발굴입니다.

---

## anti-drift 규칙

- markdown `plan`은 runtime state를 담지 않는다.
- `plan-ledger`는 prose 설명의 긴 서술을 담지 않는다.
- 같은 사실을 두 파일에 중복 기록하지 않는다.
- state 변화는 ledger와 decision-log에만 남긴다.

---

## V1 적용 원칙

- `small` route에서는 ledger를 생략하거나 아주 얇게 둘 수 있다.
- `medium` 이상은 ledger를 기본값으로 본다.
- `large_high_risk`는 ledger 없이 운영하지 않는다.
