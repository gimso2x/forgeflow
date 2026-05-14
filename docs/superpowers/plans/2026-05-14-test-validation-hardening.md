# 테스트 및 검증 강화 (Hardening) 구현 계획

> **에이전트 작업자 필독:** 본 계획을 작업 단위로 실행하려면 superpowers:subagent-driven-development (권장) 또는 superpowers:executing-plans 서브 스킬을 사용하세요. 각 단계는 추적을 위해 체크박스(`- [ ]`) 구문을 사용합니다.

**목표:** 테스트 아티팩트 생성을 위한 팩토리 패턴을 도입하여 테스트 중복을 제거하고, `docs/contract-map.md`의 내용을 자동으로 검증하는 도구를 추가하여 프로젝트의 무결성을 보장합니다.

**아키텍처:**
1.  **Artifact Factory**: `tests/runtime/conftest.py`에 `artifact_factory` 픽스처를 추가하여 모든 주요 아티팩트(brief, plan 등)의 기본값 및 오버라이드 생성을 중앙 집중화합니다.
2.  **Contract Map Validator**: 마크다운 표를 파싱하여 명시된 경로와 명령의 유효성을 검사하는 독립 실행형 Python 스크립트(`scripts/validate_contract_map.py`)를 구현하고 CI(`make validate`)에 통합합니다.

**기술 스택:** Python 3.11+, pytest, jsonschema

---

### Task 1: `artifact_factory` 픽스처 구현

**파일:**
- 수정: `tests/runtime/conftest.py`
- 생성: `tests/runtime/test_artifact_factory.py`

- [ ] **Step 1: 실패하는 테스트 작성**
  `tests/runtime/test_artifact_factory.py`를 생성하고 팩토리가 아티팩트를 올바르게 생성하고 스키마를 통과하는지 확인하는 테스트를 작성합니다.

```python
import pytest

def test_artifact_factory_brief(artifact_factory, assert_schema_valid):
    brief = artifact_factory("brief", task_id="test-task")
    assert brief["task_id"] == "test-task"
    assert brief["schema_version"] == "0.2"
    assert_schema_valid("brief", brief)

def test_artifact_factory_invalid_type(artifact_factory):
    with pytest.raises(ValueError, match="Unknown artifact type"):
        artifact_factory("non-existent")
```

- [ ] **Step 2: 테스트 실행 및 실패 확인**
  Run: `pytest tests/runtime/test_artifact_factory.py -v`
  Expected: FAIL (fixture 'artifact_factory' not found)

- [ ] **Step 3: `artifact_factory` 구현**
  `tests/runtime/conftest.py`에 기본 데이터셋과 팩토리 함수를 구현합니다.

```python
DEFAULT_ARTIFACTS = {
    "brief": {
        "schema_version": "0.2",
        "task_id": "task-001",
        "objective": "Default objective",
        "in_scope": [], "out_of_scope": [], "constraints": [],
        "acceptance_criteria": [], "risk_level": "low"
    },
    "plan": {
        "schema_version": "0.2", "task_id": "task-001",
        "steps": [], "verify_plan": []
    },
    "run-state": {
        "schema_version": "0.2", "task_id": "task-001",
        "current_stage": "clarify", "status": "in_progress",
        "completed_gates": [], "failed_gates": [], "retries": {}
    }
}

@pytest.fixture
def artifact_factory():
    def _factory(artifact_type: str, **overrides):
        if artifact_type not in DEFAULT_ARTIFACTS:
            raise ValueError(f"Unknown artifact type: {artifact_type}")
        base = DEFAULT_ARTIFACTS[artifact_type].copy()
        base.update(overrides)
        return base
    return _factory
```

- [ ] **Step 4: 테스트 실행 및 통과 확인**
  Run: `pytest tests/runtime/test_artifact_factory.py -v`
  Expected: PASS

- [ ] **Step 5: 커밋**
  ```bash
  git add tests/runtime/conftest.py tests/runtime/test_artifact_factory.py
  git commit -m "feat: add artifact_factory fixture for testing"
  ```

---

### Task 2: 기존 테스트 리팩터링 (Sample)

**파일:**
- 수정: `tests/runtime/test_gate_evaluation.py` (또는 다른 아티팩트 사용 테스트)

- [ ] **Step 1: 팩토리 사용하도록 테스트 수정**
  JSON 딕셔너리를 직접 정의하는 부분을 `artifact_factory`로 교체합니다.

- [ ] **Step 2: 테스트 실행 및 확인**
  Run: `pytest tests/runtime/test_gate_evaluation.py -v`
  Expected: PASS

- [ ] **Step 3: 커밋**
  ```bash
  git add tests/runtime/test_gate_evaluation.py
  git commit -m "refactor: use artifact_factory in gate evaluation tests"
  ```

---

### Task 3: `scripts/validate_contract_map.py` 구현

**파일:**
- 생성: `scripts/validate_contract_map.py`
- 생성: `tests/test_validate_contract_map.py`

- [ ] **Step 1: 실패하는 테스트 작성**
  가상의 잘못된 마크다운을 제공했을 때 검증기가 실패하는지 테스트합니다.

- [ ] **Step 2: 검증 스크립트 구현**
  마크다운 표 파싱 및 파일/명령 존재 여부 확인 로직을 작성합니다.

- [ ] **Step 3: 테스트 및 실행 확인**
  Run: `python3 scripts/validate_contract_map.py`
  Expected: PASS (현재 문서가 정확하다면)

- [ ] **Step 4: 커밋**
  ```bash
  git add scripts/validate_contract_map.py tests/test_validate_contract_map.py
  git commit -m "feat: add contract map validator script"
  ```

---

### Task 4: `Makefile` 통합 및 최종 검증

**파일:**
- 수정: `Makefile`

- [ ] **Step 1: `Makefile`에 검증 단계 추가**
  `validate` 타겟에 새 스크립트를 포함합니다.

- [ ] **Step 2: 전체 검증 실행**
  Run: `make validate`
  Expected: PASS

- [ ] **Step 3: 커밋**
  ```bash
  git add Makefile
  git commit -m "chore: integrate contract map validation into make validate"
  ```
