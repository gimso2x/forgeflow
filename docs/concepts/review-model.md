# Review Model

## 핵심 개념

ForgeFlow에서 review는 형식적인 승인 버튼이 아닙니다. **실행자가 자기 일 잘했다고 말하는 걸 믿지 않고, 독립된 근거로 다음 stage 진입 가능 여부를 판단하는 장치**입니다.

## Review의 위치

```text
clarify → plan → execute → review → ship
                             ↑
                        여기서 검증
```

`review`는 `execute` 다음에 옵니다. 실행 결과를 artifact와 evidence 기준으로 독립 검토합니다.

## Review가 확인하는 것

1. **Artifact 완성도** — `run-state.json`이 모든 task를 완료로 표시했는가
2. **Evidence 추적** — 각 결과에 evidence 참조가 있는가
3. **brief 대비 충족** — `brief.json`의 성공 조건이 실제로 충족되었는가
4. **부작용 확인** — 요청 범위 밖의 변경이 발생했는가

## Gate 평가

`review`에서 다음 stage(`ship`)로 넘어가려면 gate를 통과해야 합니다:

- `gate_evaluation.enforce_stage_gate()`가 artifact 존재와 schema valid를 확인
- `review-report.json`의 판정이 pass여야 함
- checkpoint/session-state가 동기화되어 있어야 함

## Review 실패 시

review가 fail이면:
1. 실패 이유가 `review-report.json`에 기록됨
2. `execute` stage로 되돌아감
3. 실행자가 실패 지점을 수정하고 다시 제출

## 읽기 전용 강제

`review` stage에서는 코드 수정이 금지됩니다. agent가 review 중에 파일을 고치는 걸 방지하는 안전 장치입니다.

## Route별 Review

- **small**: review 생략 가능. 작은 수정은 execute → ship으로 직행
- **medium**: review 권장. `review-report.json` 권장
- **high**: review 필수. gate 강제
- **epic**: review 필수. checkpoint/session/evidence 동기화까지 강제

---

정본은 [docs/review-model.md](../review-model.md)을 참고하세요.
