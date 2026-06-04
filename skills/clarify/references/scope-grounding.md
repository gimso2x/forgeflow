# Scope Grounding Reference

> Reference for clarify's WHERE calibration and scope boundary rules. Extracted from clarify SKILL.md.

## WHERE grounding

Before routing anything non-trivial, calibrate WHERE so intake is neither too heavy for toys nor too light for dangerous work.

Capture these dimensions in the brief when the user has not already provided them:

- **project_type**: user-facing app, API/service, dev tool/library, or infrastructure
- **situation**: greenfield, brownfield extension, brownfield refactor, or hybrid
- **ambition**: toy/experiment, feature/MVP, or product
- **risk_modifiers**: sensitive data, external exposure, irreversible ops, high scale

Risk escalation rules:

- Sensitive data -> security and data requirements must be deep.
- External exposure -> security and access requirements must be deep.
- Irreversible ops -> risk and compatibility requirements must be deep.
- High scale -> infrastructure and architecture requirements must be deep.

Situation rules:

- Greenfield: ask enough to define behavior and core architecture, but do not invent enterprise ceremony.
- Brownfield extension: inspect existing code and docs before asking factual questions; ask about decisions and tradeoffs, not facts the repo can answer.
- Brownfield refactor: compatibility, callers, migration path, and rollback are first-class requirements.
- Hybrid: separate new-module behavior from integration constraints.

For exact-count, dry-run, or response-only prompts, do not force the WHERE interview. Obey the requested output exactly.

## Scope Boundary Definition

clarify 단계에서 scope boundary를 명시적으로 정의하여 scope creep을 방지합니다.

### scope_files 목록 생성

clarify에서는 예상 수정 파일 목록(`scope_files`)을 명시적으로 생성합니다:

1. 요구사항 분석 후 직접적으로 수정이 필요한 파일 나열
2. 각 파일의 수정 이유를 In Scope 항목과 매핑
3. scope_files 수를 route 임계값과 비교하여 `boundary_status` 산정
4. **medium/high/epic route**: scope_files에 예상 테스트 파일도 포함한다. 프로젝트의 테스트 파일 명명 규칙(`*.test.*`, `*.spec.*`, `test_*` 등)을 감지하여, 수정 대상 소스 파일에 대응하는 테스트 파일 경로를 scope_files에 추가한다. 이는 execute 단계의 test-after 검증에서 scope boundary alert를 방지한다.

### Route 임계값과 boundary alert

| Route | files_limit | boundary_status 기준 |
|-------|-------------|---------------------|
| small | 3 | files_planned ≤ 3 → within, = 3 → at_limit, > 3 → exceeds |
| medium | 8 | files_planned ≤ 8 → within, = 8 → at_limit, > 8 → exceeds |
| high | 20 | files_planned ≤ 20 → within, = 20 → at_limit, > 20 → exceeds |
| epic | unlimited | boundary_status 항상 within |

- `boundary_status = exceeds` 시 brief.md에 경고 기록 및 "scope split 권장" advisory 발행
- `boundary_status = at_limit` 시 주의 표시 (경고는 아님)
- scope_boundary 정보를 brief.md YAML frontmatter에 기록
