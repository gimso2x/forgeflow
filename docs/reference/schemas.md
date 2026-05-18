# Schema Reference

ForgeFlow의 모든 artifact는 JSON schema로 검증됩니다.

## Schema 위치

```text
schemas/
  brief.schema.json
  plan-ledger.schema.json
  run-state.schema.json
  review-report.schema.json
  checkpoint.schema.json
  session-state.schema.json
```

## 공통 필드

모든 artifact에 포함되는 필드:

```json
{
  "schema_version": "0.2",
  "task_id": "my-task-001"
}
```

## brief.json

`clarify` stage에서 생성.

```json
{
  "schema_version": "0.2",
  "task_id": "...",
  "objective": "...",
  "in_scope": ["..."],
  "out_of_scope": ["..."],
  "constraints": ["..."],
  "acceptance_criteria": ["..."],
  "risk_level": "low|medium|high|critical",
  "route": "small|medium|high|epic"
}
```

## plan-ledger.json

`plan` stage에서 생성. task 목록과 의존성 추적.

```json
{
  "schema_version": "0.2",
  "task_id": "...",
  "route": "small|medium|high|epic",
  "tasks": [
    {
      "id": "...",
      "title": "...",
      "status": "pending|in_progress|done|blocked",
      "depends_on": [],
      "files": ["src/example.py"],
      "parallel_safe": true,
      "required_gates": ["machine"],
      "evidence_refs": [],
      "attempt_count": 0
    }
  ]
}
```

## run-state.json

`execute` stage에서 갱신.

```json
{
  "schema_version": "0.2",
  "task_id": "...",
  "current_stage": "execute",
  "status": "in_progress",
  "completed_gates": ["clarify", "plan"],
  "failed_gates": [],
  "retries": {"execute": 0},
  "spec_review_approved": false,
  "quality_review_approved": false,
  "evidence_refs": ["..."]
}
```

## review-report.json

`review` stage에서 생성.

```json
{
  "schema_version": "0.2",
  "task_id": "...",
  "review_type": "spec|quality|security|ux",
  "verdict": "approved|changes_requested|blocked",
  "findings": ["..."],
  "approved_by": "reviewer-id",
  "next_action": "advance to next stage",
  "safe_for_next_stage": true,
  "open_blockers": [],
  "evidence_refs": ["..."]
}
```

## 검증 방법

### 코드에서

```python
from forgeflow_runtime.artifact_validation import assert_supported_artifact_schema_version

assert_supported_artifact_schema_version(artifact, "brief")
```

쓰기 시 자동 검증:

```python
from forgeflow_runtime.artifact_validation import write_validated_artifact

write_validated_artifact(path, artifact)
```

### CLI에서

```bash
python3 scripts/validate_policy.py
```

## Schema 버전

현재 artifact schema version은 `0.2`입니다. `0.1`은 런타임 로드 시 migration 대상이며, 새 artifact는 `forgeflow_runtime.schema_versions.CURRENT_SCHEMA_VERSION`을 사용해야 합니다. 스키마 버전은 릴리스 버전과 별개로 `schemas/*.schema.json` 및 `schema_versions.py`에서 관리됩니다.
