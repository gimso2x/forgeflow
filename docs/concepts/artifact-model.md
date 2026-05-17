# Artifact Model

## 핵심 원칙

ForgeFlow는 대화 로그가 아니라 **artifact**를 기준으로 움직입니다. artifact는 stage 간 handoff 계약이며, resume과 review의 최소 단위입니다.

1. 모든 artifact는 `schema_version`을 가진다
2. 모든 artifact는 `task_id`를 가진다
3. 사람이 읽을 수 있어야 한다
4. agent가 다음 stage로 넘어갈 때 반드시 필요한 artifact가 있어야 한다

## 주요 Artifact

### brief.json
`clarify` 단계에서 생성. 요구사항, 제약, 성공 조건, risk 등급, route를 담습니다.

### plan-ledger.json
`plan` 단계에서 생성. 실행 가능한 task 목록, 순서, 의존성을 추적합니다.

### run-state.json
`execute` 단계에서 갱신. 현재 실행 상태, 완료된 task, 남은 task를 기록합니다.

### review-report.json
`review` 단계에서 생성. 독립 검토 결과, evidence 참조, pass/fail 판정을 담습니다.

### checkpoint.json / session-state.json
실행 중단/재개를 위한 상태 추적. 세션 경계를 넘어서도 작업을 이어갈 수 있게 합니다.

## Artifact 경로

기본 위치는 `.forgeflow/tasks/<task-id>/`입니다.

```text
.forgeflow/tasks/my-task-001/
  brief.json
  plan-ledger.json
  run-state.json
  review-report.json
  checkpoint.json
  session-state.json
  docs/          # PRD, ARCHITECTURE, QA, DECISIONS
  tasks/         # init-summary, feature, qa
```

`--task-dir`로 다른 위치를 지정할 수 있습니다.

## Schema 검증

모든 artifact는 JSON schema로 검증됩니다. `schemas/` 디렉터리에 schema 정의가 있고, `write_validated_artifact()`로 쓰기 시 자동 검증됩니다.

## 읽기 전용 규칙

`review` stage에서는 artifact 수정이 금지됩니다. 읽기만 허용. 실행자가 자기 결과를 검토 중에 몰래 수정하는 걸 방지합니다.

---

자세한 규약은 [docs/artifact-model.md](../artifact-model.md)의 정본을 참고하세요.
