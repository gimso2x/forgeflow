# Invalid Checkpoint Fixture

이 디렉터리는 `run-state.json` 체크포인트가 route prefix와 어긋날 때 orchestrator가 거부해야 하는 케이스다.

## 문제 상태
- `current_stage`는 `execute`
- 하지만 `clarification_complete` 없이 `execution_evidenced`만 기록되어 있음
- orchestrator는 prefix drift를 감지하고 resume을 거부해야 함
