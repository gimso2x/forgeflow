# mixed-task-decision-log

`brief.json`/`run-state.json`는 같은 task를 가리키지만 `decision-log.json`의 `task_id`가 다르다.

기대 동작:
- recovery helper(`retry`)가 append-only decision log를 열 때 mixed-task artifact로 거부되어야 한다.
- 기대 에러 일부: `decision-log.json task_id other-task-log-999 does not match canonical task_id mixed-task-log-001`
