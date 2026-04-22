# Completed Checkpoint Drift Fixture

이 디렉터리는 `run-state.json`가 `completed` 상태인데도 terminal stage에 도달하지 못한 checkpoint를 orchestrator가 거부해야 하는 케이스다.

## 문제 상태
- `current_stage`는 아직 `execute`
- `status`는 `completed`로 잘못 기록됨
- orchestrator는 completed checkpoint가 terminal stage `finalize`에 있지 않으면 resume을 거부해야 함
