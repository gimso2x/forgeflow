# Future Gate Checkpoint Drift Fixture

이 디렉터리는 `run-state.json` 체크포인트에 현재 stage 이후 gate가 미리 기록된 상태를 orchestrator가 거부해야 하는 케이스다.

## 문제 상태
- `current_stage`는 `execute`
- `clarification_complete`는 있지만 `quality_review_passed`가 이미 완료된 것으로 찍혀 있음
- orchestrator는 미래 gate drift를 감지하고 resume을 거부해야 함
