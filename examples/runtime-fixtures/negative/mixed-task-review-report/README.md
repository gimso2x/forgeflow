# mixed-task-review-report

`brief.json`과 `review-report.json`의 `task_id`가 다르다.

기대 동작:
- `small` route 실행 시 quality review gate 검증 과정에서 mixed-task artifact로 거부되어야 한다.
- 기대 에러 일부: `review-report.json task_id other-task-review-999 does not match canonical task_id mixed-task-review-001`
