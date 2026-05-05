# evidence_refs 구조화 — 온톨로지 관계 명시화

## 배경

현재 `plan-ledger`의 `evidence_refs`는 평면 문자열 배열이다:
```json
"evidence_refs": [
  "run-state.json#gate:plan_executable",
  "review-report.json#verdict:approved"
]
```

이 형식은 `#gate:`, `#verdict:` 같은 내재 규약이 있지만:
- 기계가 relation type을 파싱하려면 문자열 split 필요
- 어떤 relation이 있는지 스키마에 정의되지 않음
- audit/evolution에서 "이 evidence가 무슨 의미인지" 프로그램적 추적 불가

문서 **"데이터 사이언스 분야에서의 온톨로지"**의 핵심 논점을 적용:
> "데이터에 의미(meaning)가 부여되지 않아 기계가 스스로 이해하고 처리할 수 없다"

ForgeFlow는 이미 artifact schema, gate enforcement, stage transition으로 "artifact 온톨로지"를 운영 중.
`evidence_refs`만 구조화하면 evidence trail이 진정한 **의미 인프라**가 된다.

---

## 변경 범위

### 1. `schemas/plan-ledger.schema.json` — evidence_refs 스키마 변경

**Before:**
```json
"evidence_refs": {
  "type": "array",
  "items": {
    "type": "string",
    "minLength": 1
  },
  "uniqueItems": true
}
```

**After:**
```json
"evidence_refs": {
  "type": "array",
  "items": {
    "type": "object",
    "required": ["type", "target", "relation"],
    "additionalProperties": false,
    "properties": {
      "type": {
        "type": "string",
        "enum": ["gate", "review", "artifact", "checkpoint", "external"]
      },
      "target": {
        "type": "string",
        "minLength": 1,
        "description": "artifact filename or URI"
      },
      "relation": {
        "type": "string",
        "enum": [
          "validated_by",
          "approved_by",
          "changes_requested_by",
          "blocked_by",
          "produced_by",
          "referenced_by",
          "snapshot_of",
          "custom"
        ]
      },
      "label": {
        "type": "string",
        "minLength": 1,
        "description": "optional human-readable annotation"
      }
    },
    "allOf": [
      {
        "if": { "properties": { "relation": { "const": "custom" } }, "required": ["relation"] },
        "then": { "required": ["label"] }
      }
    ]
  },
  "uniqueItems": true
}
```

**uniqueItems**: JSON 객체 배열이라 `"additionalProperties": false` + 조합으로 중복 방지. 실제 dedup은 `plan_ledger.py`에서.

### 2. `forgeflow_runtime/plan_ledger.py` — append_evidence_ref() 변경

**Before (현재):**
```python
def append_evidence_ref(task: dict[str, Any], evidence_ref: str) -> None:
    evidence_refs = task.setdefault("evidence_refs", [])
    if evidence_ref not in evidence_refs:
        evidence_refs.append(evidence_ref)
```

**After:**
```python
EvidenceRef = dict[str, str]  # {"type", "target", "relation", "label"?}


def _make_evidence_ref(
    *,
    type: str,
    target: str,
    relation: str,
    label: str = "",
) -> EvidenceRef:
    ref: EvidenceRef = {"type": type, "target": target, "relation": relation}
    if label:
        ref["label"] = label
    return ref


def append_evidence_ref(task: dict[str, Any], evidence_ref: EvidenceRef) -> None:
    evidence_refs = task.setdefault("evidence_refs", [])
    # dedup by (type, target, relation) tuple
    key = (evidence_ref["type"], evidence_ref["target"], evidence_ref["relation"])
    if not any(
        (r.get("type"), r.get("target"), r.get("relation")) == key
        for r in evidence_refs
    ):
        evidence_refs.append(evidence_ref)
```

### 3. `forgeflow_runtime/gate_evaluation.py` — gate_evidence_ref() 변경

현재 문자열을 반환하는 함수를 구조화:

**Before:**
```python
def gate_evidence_ref(stage_name: str, gate_name: str) -> str:
    return f"run-state.json#gate:{gate_name}"
```

**After:**
```python
def gate_evidence_ref(stage_name: str, gate_name: str) -> dict[str, str]:
    return {
        "type": "gate",
        "target": f"run-state.json#gate:{gate_name}",
        "relation": "validated_by",
        "label": f"{stage_name}/{gate_name}",
    }
```

### 4. `plan_ledger.py` — sync_plan_ledger_review() 변경

**Before:**
```python
append_evidence_ref(task, f"{review_artifact}#verdict:{verdict}")
```

**After:**
```python
append_evidence_ref(task, {
    "type": "review",
    "target": review_artifact,
    "relation": {"approved": "approved_by", "changes_requested": "changes_requested_by", "blocked": "blocked_by"}.get(verdict, "referenced_by"),
    "label": f"verdict:{verdict}",
})
```

### 5. 샘플/픽스처 업데이트

- `examples/artifacts/plan-ledger.sample.json` — evidence_refs를 객체 배열로
- `examples/runtime-fixtures/` 하위 plan-ledger.json들 — 동일하게 변경
- `examples/artifacts/invalid/plan-ledger-done-without-evidence.sample.json` — 확인

### 6. 테스트 업데이트

- `tests/runtime/test_plan_ledger_helpers.py`
  - `_ledger()`의 evidence_refs를 `[]` 유지 (빈 배열이면 OK)
  - `test_sync_plan_ledger_gate_records_stage_gate_and_evidence_once`:
    assert 대상을 `"run-state.json#gate:plan_executable"` → `{"type": "gate", "target": "run-state.json#gate:plan_executable", "relation": "validated_by", "label": "plan/plan_executable"}`
  - `test_sync_plan_ledger_review_records_latest_verdict_and_evidence`:
    동일하게 객체로 assert
  - `test_rewind_plan_ledger_progress_removes_future_stage_gate_and_review_evidence`:
    evidence_refs 초기화 후 `[]` assert — 변경 없음

---

## 변경하지 않는 것

- `additionalProperties: false` 원칙 유지
- stdlib-only — jsonschema는 이미 사용 중
- evidence_refs에 기존 문자열 backward compat 레이어 불필요 (schema_version 0.1이므로 한 번에 migration)
- `orchestrator.py`의 stage transition 로직 — append_evidence_ref만 호출하므로 인터페이스 변화 없음

---

## 수용 기준 (Acceptance Criteria)

1. `python3 -m pytest tests/runtime/test_plan_ledger_helpers.py -q` 전부 통과
2. `python3 -m pytest tests/runtime/test_plan_ledger.py -q` 전부 통과
3. `python3 -m pytest tests/ -q` 전체 1082개 통과 (회귀 없음)
4. `python3 scripts/validate_structure.py` 통과
5. `python3 -c "import forgeflow_runtime.plan_ledger; import forgeflow_runtime.gate_evaluation"` 임포트 성공
6. `examples/artifacts/plan-ledger.sample.json`이 `schemas/plan-ledger.schema.json` 검증 통과

---

## 향후 확장 (이 PR에서 하지 않음)

- evidence graph 시각화 (dot/graphviz)
- cross-project evidence 추적
- Hermes fact_store 연동
