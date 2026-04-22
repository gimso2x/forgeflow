# Recovery Policy

## 목적
실패했을 때 무한 self-healing loop에 빠지지 않고, bounded recovery만 허용한다.

---

## 핵심 원칙
1. 같은 실패를 무한 반복하지 않는다.
2. retry는 이유가 기록될 때만 허용한다.
3. recovery도 stage machine 안에서 관리한다.
4. 막히면 stop 또는 human escalation이 정상이다.

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
모든 recovery는 `decision-log`와 `run-state`에 남긴다.
남겨야 할 것:
- failure category
- retry reason
- chosen recovery action
- next gate expectation

---

## 금지
- 원인 기록 없는 재시도
- review 실패를 무시한 finalize
- long-run capture를 핑계로 unresolved failure를 덮기
