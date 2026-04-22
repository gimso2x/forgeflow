# Workflow Adherence Evals

이 디렉토리는 하네스가 자기 규칙을 실제로 지키는지 확인한다.

실행 명령:
```bash
python3 scripts/run_adherence_evals.py
# 또는
make adherence-evals
```

현재 executable 체크:
- `examples/runtime-fixtures/small-doc-task` small route happy path
- `examples/runtime-fixtures/resume-small-task` validated checkpoint에서 small route resume
- `examples/runtime-fixtures/medium-refactor-task` medium route happy path
- `examples/runtime-fixtures/large-migration-task` large/high-risk happy path
- `negative/missing-quality-approval`에서 non-approved quality review 거부
- `negative/invalid-review-report`에서 schema-invalid review artifact 거부
- `negative/missing-run-state-before-spec-review`에서 spec-review 진입 거부
- `negative/missing-eval-record-before-long-run`에서 long-run gate 거부
- `negative/checkpoint-gate-drift`에서 prefix가 깨진 checkpoint resume 거부
- `negative/future-gate-checkpoint-drift`에서 미래 gate가 미리 찍힌 checkpoint resume 거부
- `negative/completed-checkpoint-drift`에서 terminal stage에 있지 않은 completed checkpoint 거부

핵심 규칙:
- artifact 없이 stage 전환 금지
- spec-review 선행 없이 quality-review가 필요한 route를 우회하지 못해야 함
- high-risk task가 long-run 없이 종료되지 않는지 확인
- approval flag 없이 finalize 금지
- checkpoint가 이미 입증한 stage는 재생하지 않고 다음 미완료 stage부터 이어가야 함
