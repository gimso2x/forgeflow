# Regression Evals

하네스 변경 이후 아래가 깨지지 않는지 확인한다.
- stage order
- artifact contracts
- review order
- adapter generation assumptions

## 실행

```bash
make setup
make check-env
make evals
```

현재 regression suite는 `make evals`에 포함되지 않은 **문서 전용** 상태다.
runner(`scripts/run_regression_evals.py`)가 구현되면 `scripts/run_evals.py`의 suites 목록에 추가한다.

## 커버하는 회귀 시나리오

### Stage order
- small → spec-review → quality-review → finalize 순서 불변
- medium/high route에서 스킵 불가한 stage 임의 우회 금지
- checkpoint resume 시 완료된 stage 재실행 금지

### Artifact contracts
- `schema_version` 필드는 항상 현재 버전과 일치
- required 필드 누락 시 스키마 검증 실패
- artifact 간 참조 무결성 (review-report → spec-review → plan-ledger)

### Review order
- spec-review 없이 quality-review 진입 금지
- approval flag 없이 finalize 금지
- 다른 task의 review artifact 혼용 금지

### Adapter generation assumptions
- Claude/Codex adapter 생성 시 canonical prompt에서 필드 누락 없음
- skill 예제의 schema_version이 현재 버전과 일치
- plugin manifest 버전이 pyproject.toml과 동기화

## 새 회귀 테스트 추가

1. `evals/regression/fixtures/`에 테스트 케이스 추가
2. `scripts/run_regression_evals.py`에 runner 구현
3. `scripts/run_evals.py` suites 목록에 `("regression", ...)` 추가
4. 이 README에 시나리오 설명 추가
