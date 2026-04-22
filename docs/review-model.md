# Review Model

## 목적
검증을 worker의 자기설명에서 떼어낸다.
이 harness의 review는 기분 좋은 마무리 멘트가 아니라 통과/실패 판정이다.

---

## 1. 왜 review를 둘로 나누나
리뷰를 한 덩어리로 두면 두 가지가 섞인다.

1. 원하는 걸 맞게 만들었는가
2. 잘 만들었는가

이 둘은 다르다.
잘 만든 오답도 있고, 개판이지만 요구사항은 맞춘 코드도 있다.
그래서 review를 두 단계로 강제한다.

---

## 2. Spec review
질문:
- 요청한 문제를 맞게 풀었는가?
- `brief`의 acceptance criteria를 충족했는가?
- 범위를 넘거나 덜 구현하지 않았는가?

입력:
- `brief`
- `plan`
- `run-state`
- evidence

출력:
- `review-report` with `review_type=spec`

판정:
- `approved`
- `changes_requested`
- `blocked`

실패 예시:
- 기능은 그럴싸하지만 acceptance criteria 일부 누락
- 구현자가 임의로 scope 확장
- 검증 증거 없이 "완료" 선언

---

## 3. Quality review
질문:
- 결과물이 유지보수 가능한가?
- 검증 품질이 충분한가?
- 위험이 통제되는가?

입력:
- spec review 통과 결과
- `run-state`
- evidence

출력:
- `review-report` with `review_type=quality`

판정:
- `approved`
- `changes_requested`
- `blocked`

검토 항목:
- 단순성
- 명확성
- 과한 설계 여부
- 테스트/검증 품질
- 잔존 리스크
- adapter/rules drift 위험

---

## 4. reviewer operating rules
1. worker 자기보고를 신뢰하지 않는다.
2. evidence 없는 주장은 승인하지 않는다.
3. spec failure를 quality commentary로 덮지 않는다.
4. 범위 밖 리팩터를 미덕처럼 칭찬하지 않는다.
5. 불확실하면 `blocked` 또는 `changes_requested`를 낸다.

---

## 5. Anti-rationalization rules
다음 문장은 사실상 실패 신호다.
- "아마 이 정도면 될 것 같다"
- "테스트는 못 돌렸지만 논리상 맞다"
- "요구사항이 애매해서 더 좋은 방향으로 바꿨다"
- "리뷰에서 알아서 잡히면 된다"

이런 말이 나오면 review는 더 빡세져야 한다.

---

## 6. Finalization rule
- spec-review 승인 전 finalize 금지
- quality-review 승인 전 high-risk finalize 금지
- `run-state.spec_review_approved`와 `run-state.quality_review_approved`가 finalize gate 근거가 된다
- unresolved blocker가 있으면 long-run capture 이전에 먼저 남겨야 함
