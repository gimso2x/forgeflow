# Recovery Policy

## 목적
실패했을 때 무한 self-healing loop에 빠지지 않고, bounded recovery만 허용한다.

---

## 핵심 원칙
1. 같은 실패를 무한 반복하지 않는다.
2. retry는 이유가 기록될 때만 허용한다.
3. recovery도 stage machine 안에서 관리한다.
4. 막히면 stop 또는 human escalation이 정상이다.
5. resume은 compact summary가 아니라 artifact reload를 기준으로 한다.

---

## 허용 recovery
### 1) retry in place
조건:
- transient failure 가능성이 높음
- missing evidence를 추가로 수집 가능함

### 2) step back
조건:
- plan 또는 clarify가 부실해서 execution이 틀어짐
- reviewer가 spec mismatch를 명확히 지적함

### 3) escalate
조건:
- 외부 의존성 문제
- 권한 문제
- 근본적 요구사항 모호성
- 반복 실패가 임계치 도달

---

## retry budget
기본 권장:
- same-stage retry: 최대 2회
- 같은 원인 반복 시 즉시 escalation

---

## 기록 규칙
모든 recovery는 `decision-log`, `run-state`, 필요 시 `checkpoint`에 남긴다.
남겨야 할 것:
- failure category
- retry reason
- chosen recovery action
- next gate expectation
- resume 시 다시 읽어야 할 artifact ref

---

## resume 규칙
resume 시에는 아래 순서를 따른다.
1. 최신 `checkpoint`가 있으면 먼저 읽는다.
2. `run-state`, `plan-ledger`, 관련 review artifact를 다시 연다.
3. 참조 artifact 정합성을 확인한다.
4. 그 다음에만 다음 action을 이어간다.

요약문은 길 안내일 수는 있어도 진실원천이 아니다.

---

## 금지
- 원인 기록 없는 재시도
- review 실패를 무시한 finalize
- long-run capture를 핑계로 unresolved failure를 덮기
- checkpoint 없이 summary만 믿고 재개하기
