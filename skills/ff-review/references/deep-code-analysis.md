# Deep Code Analysis Guide

quality-reviewer가 diff 수준에서 코드를 분석할 때 사용하는 7-angle 분석 가이드.

## When to use

standalone mode에서 diff/파일 입력이 있거나, pipeline mode에서 코드 변경이 있을 때 quality-reviewer가 이 가이드에 따라 분석한다. metrics 기반 검사와 병행한다.

## Angle 1 — Line-by-line diff scan

diff의 모든 hunk을 줄 단위로 읽는다. 각 hunk의 인코딩 함수도 함께 읽는다 (변경되지 않은 줄도 범위 내). 모든 줄에 대해 질문:

- 이 줄을 틀리게 만드는 입력, 상태, 타이밍, 플랫폼은?
- 조건이 반대/잘못되었는가? (off-by-one, 부정 누락)
- null/undefined 접근 가능?
- `await` 누락?
- falsy-zero를 missing으로 처리?
- 변수 복사-붙여넣기 실수?
- catch 블록에서 에러 삼킴?
- 정규식 메타문자 이스케이프 누락?

## Angle 2 — Removed-behavior auditor

diff가 삭제하거나 교체하는 모든 줄에 대해:
1. 그 줄이 강제하던 불변식(invariant)이나 동작을 명명
2. 새 코드에서 그 불변식이 재확립되는지 검색
3. 찾을 수 없으면 후보: 제거된 가드, 좁혀진 validation, 삭제된 테스트

## Angle 3 — Cross-file tracer

diff가 변경하는 각 함수에 대해:
1. **호출자 검색**: 이 변경이 호출 사이트를 깨는가? (새 전제조건, 변경된 반환 shape, 새 예외, 타이밍/순서 의존성)
2. **호출 대상 검색**: 같은 PR의 병렬 변경이 호출을 안전하지 않게 만드는가?

## Angle 4 — Reuse detection

변경된 코드가 이미 존재하는 것을 재구현하는지 확인:
- 인접 파일/유틸리티 모듈에서 기존 헬퍼 검색
- 공유 유틸리티 이름을 명시하여 대안 제시

## Angle 5 — Simplification

diff가 추가하는 불필요한 복잡성:
- 중복되거나 파생 가능한 상태
- 약간의 변형을 가진 복사-붙여넣기
- 깊은 중첩
- 남겨진 죽은 코드
- 더 단순한 형태 명시

## Angle 6 — Efficiency

diff가 도입하는 불필요한 작업:
- 중복 계산 또는 반복 I/O
- 독립적인 작업을 순차 실행
- 핫 경로에 추가된 블로킹 작업
- 더 저렴한 대안 명시

## Angle 7 — Altitude

각 변경이 적절한 깊이에서 구현되었는지 확인:
- 공유 인프라 위에 특수 케이스를 겹겹이 쌓았는가?
- 근본 메커니즘을 일반화하는 것이 특수 케이스를 추가하는 것보다 나은가?

## Finding verification

각 후보 finding에 대해 한 번의 검증 실행:

- **CONFIRMED**: 코드에서 구성 가능 — 사실적으로 틀림 (인용), 타입/상수/불변식으로 증명 가능 불가능, 이미 이 diff에서 처리됨
- **PLAUSIBLE**: 현실적 상태에서 발생 가능 — 동시성 경쟁, rare-but-reachable 경로의 nil/undefined, falsy-zero, 경계 off-by-one, 재시도 폭풍
- **REFUTED**: 코드에서 반박 가능 — 사실적으로 틀림, 증명 불가능, 순수 스타일 (관찰 가능한 효과 없음)

CONFIRMED와 PLAUSIBLE만 유지. REFUTED는 폐기.

## Output format

각 finding은 다음 형식:

```
- **Category**: correctness | maintainability | efficiency | altitude
- **Severity**: blocker | major | minor
- **File:Line**: path/to/file.ext:123
- **Summary**: 한 줄 설명
- **Failure scenario**: 구체적 입력/상태 → 잘못된 출력/크래시
- **Verification**: CONFIRMED | PLAUSIBLE
```
