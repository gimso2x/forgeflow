# Harness V1 Principles

## 한 줄
ForgeFlow V1은 `engineering-discipline`의 workflow shape를 유지하되, 실제 진실원천은 prose가 아니라 artifact + ledger + schema로 둔다.

---

## 핵심 입장

1. **chat는 state가 아니다**
   - 대화는 설명일 뿐이다.
   - stage 판정, review 근거, resume 기준은 artifact와 ledger에 남아야 한다.

2. **형태는 유지하고 엔진은 교체한다**
   - `clarify -> plan -> execute -> spec-review -> quality-review -> finalize -> long-run`
   - 이 visible skeleton은 유지한다.
   - 대신 내부는 machine-readable contract로 강화한다.

3. **plan과 runtime truth는 분리한다**
   - `plan`은 사람용 실행 의도 문서다.
   - `plan-ledger`는 기계가 믿는 실행 상태다.
   - 둘을 섞으면 결국 둘 다 못 믿게 된다.

4. **review는 두 단계로 나눈다**
   - `spec-review`: 요청한 걸 맞게 만들었는가
   - `quality-review`: 유지보수 가능하고 검증 가능한가
   - 이 순서는 바꾸지 않는다.

5. **adapter는 surface만 바꾼다**
   - host별 파일명, 설치 위치, 표현 방식은 달라도 된다.
   - stage/gate/review semantics는 canonical policy가 유일한 기준이다.

6. **resume은 요약 복원 놀이가 아니다**
   - 재개 시에는 checkpoint/session-state/run-state/ledger를 다시 읽는다.
   - compact summary는 길 안내 정도만 하고, 판정 근거가 되면 안 된다.

7. **작은 작업엔 작은 ceremony**
   - 작은 작업까지 문서 놀이를 강제하면 harness가 아니라 발목잡이다.
   - `plan-ledger`, `contracts`, `checkpoint`는 route/complexity에 맞게 조건부 적용한다.

---

## 흡수한 레퍼런스의 역할

### engineering-discipline
- 채택: workflow skeleton, complexity routing, worker/validator/reviewer separation
- 비채택: prose-heavy SSOT, branded path religion

### hoyeon
- 채택: machine-readable ledger, typed gates, bounded recovery
- 비채택: 모든 작업에 무거운 계약 ceremony

### gstack
- 채택: canonical policy -> generated adapters, local memory/eval substrate, artifact restore
- 비채택: adapter/framework expansion 욕심

### superpowers
- 채택: spec-review before quality-review, anti-rationalization, skeptical review
- 비채택: repo-specific voice/tone/ritual

---

## V1 hard invariants

1. artifact 없이 stage 전환 금지
2. `plan-ledger` 없이 multi-step runtime truth 판정 금지
3. spec-review 실패 시 quality-review 금지
4. review 결과 없는 finalize 금지
5. adapter가 semantics 변경 금지
6. unresolved blocker를 success처럼 포장 금지
7. retry는 bounded budget 안에서만 허용
8. resume은 artifact reload 기준으로만 수행

---

## V1 산출물 우선순위

### 반드시 있어야 하는 것
- `docs/harness-v1-principles.md`
- `docs/ledger-model.md`
- `docs/checkpoint-model.md`
- `schemas/plan-ledger.schema.json`
- `schemas/checkpoint.schema.json`
- positive/negative sample fixtures
- sample validator coverage

### 그 다음
- orchestrator의 ledger-aware runtime
- checkpoint/session-state resume wiring
- methodology evals

---

## 하지 말아야 할 것
- 레퍼런스 repo 이름/폴더를 그대로 베끼기
- plugin ecosystem을 코어 구조로 올리기
- 숨은 magical memory 추가하기
- review를 스타일 잔소리 대회로 만들기
- tiny task에 large-risk ceremony 강제하기
