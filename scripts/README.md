# Scripts

## 목적
P0에서 필요한 최소 자동화를 둔다.

## 포함 스크립트
- `validate_structure.py` : 필수 디렉토리/파일 존재 검증
- `validate_policy.py` : workflow/stages/routes/schema 핵심 규칙 검증
- `generate_adapters.py` : canonical policy와 prompt를 target별 generated output으로 변환
- `validate_generated.py` : generated 산출물이 최소 규칙을 지키는지 검증

## 권장 실행 순서
1. `python3 scripts/validate_structure.py`
2. `python3 scripts/validate_policy.py`
3. `python3 scripts/generate_adapters.py`
4. `python3 scripts/validate_generated.py`
