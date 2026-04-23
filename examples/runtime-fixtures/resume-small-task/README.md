# Resume Small Runtime Fixture

이 디렉터리는 orchestrator가 기존 `run-state.json` 체크포인트에서 `small` route를 재개하는 샘플이다.

## 시작 상태
- `current_stage`는 `execute`
- `clarification_complete`, `execution_evidenced` gate는 이미 완료됨
- orchestrator는 `clarify`/`execute`를 다시 재생하지 않고 `quality-review`부터 이어서 실행해야 함
