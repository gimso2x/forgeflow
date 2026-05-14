# Spec: Test and Validation Hardening (Artifact Factory & Contract Map Validator)

- **Date**: 2026-05-14
- **Status**: Draft
- **Topic**: Refactoring test fixtures and automating contract map validation

## 1. 개요 (Overview)

ForgeFlow의 유지보수성(Maintainability)을 높이기 위해 두 가지 핵심 과제를 수행한다.
1. **Artifact Factory 도입**: 테스트 코드의 중복을 줄이고 스키마 변경에 유연하게 대응할 수 있는 중앙 집중식 팩토리 패턴 구현.
2. **Contract Map Validator 구현**: `docs/contract-map.md`에 명시된 프로젝트 규칙이 실제 코드와 일치하는지 자동으로 검증하는 도구 구현.

## 2. 아키텍처 및 상세 설계 (Architecture & Design)

### 2.1 Artifact Factory (`tests/runtime/conftest.py`)

테스트에서 사용되는 JSON 아티팩트의 생성 로직을 팩토리 함수로 추상화한다.

- **컴포넌트**: `artifact_factory` (pytest fixture)
- **지원 타입**: `brief`, `plan`, `plan-ledger`, `run-state`, `review-report`, `review-input`, `eval-record`
- **작동 원리**: 
    - 각 타입별로 최신 스키마(`0.2`)를 준수하는 기본(default) 딕셔너리를 정의한다.
    - 사용자가 인자로 전달한 `overrides`를 기본값에 병합(merge)하여 반환한다.
    - `tests/runtime/helpers.py`에 존재하는 개별 `write_*` 함수들을 이 팩토리를 사용하도록 리팩터링한다.

### 2.2 Contract Map Validator (`scripts/validate_contract_map.py`)

프로젝트의 "Source of Truth"를 정의하는 문서를 코드로 검증한다.

- **컴포넌트**: `scripts/validate_contract_map.py` (CLI tool)
- **검증 항목**:
    - **파일 존재 여부**: 표의 `Surface` 또는 `Source of truth` 컬럼에 명시된 파일/디렉터리 경로가 실제 파일 시스템에 존재하는지 확인.
    - **명령어 유효성**: `Validation command` 컬럼에 적힌 스크립트 파일이나 테스트 경로가 존재하는지 확인.
    - **Script-thinness**: `scripts/*.py` 파일들이 복잡한 정책 로직을 직접 포함하지 않고 `forgeflow_runtime/`으로 위임하는지 정적 분석 (import 여부 등).
- **출력**: 위반 사항 발견 시 구체적인 행 번호와 오류 메시지 출력 후 non-zero exit code 반환.

## 3. 데이터 흐름 (Data Flow)

1. **테스트 실행 시**: `test_function` -> `artifact_factory` 호출 -> 기본값 + override 병합 -> 유효한 dict 반환 -> 테스트 수행.
2. **검증 실행 시**: `make validate` -> `validate_contract_map.py` 호출 -> `contract-map.md` 파싱 -> 파일 시스템 및 정적 분석 수행 -> 결과 보고.

## 4. 테스트 전략 (Testing Strategy)

- **Factory 테스트**: `tests/runtime/test_artifact_factory.py`를 신설하여 팩토리가 생성한 결과물이 실제 JSON 스키마를 통과하는지 검증.
- **Validator 테스트**: `tests/test_validate_contract_map.py`를 신설하여 의도적으로 잘못된 문서를 제공했을 때 검증기가 오류를 정확히 잡아내는지 검증.

## 5. 성공 기준 (Success Criteria)

- `tests/runtime/` 내의 모든 아티팩트 생성 로직이 `artifact_factory`를 사용하도록 변경됨.
- `make validate` 실행 시 `scripts/validate_contract_map.py`가 포함되어 통과함.
- `docs/contract-map.md`의 내용을 임의로 수정(존재하지 않는 파일 기재 등)했을 때 검증기가 이를 잡아냄.
