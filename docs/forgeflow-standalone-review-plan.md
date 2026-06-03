# ForgeFlow standalone review 확장 실행계획

> **Status**: ✅ 완료 (v1.2.0 기준). 모든 완료 기준이 충족되었습니다.
> - `skills/ff-review/SKILL.md`에 standalone mode, input type detection, input normalization, reviewer role 분리, Human Final Judgment Gate가 구현되어 있습니다.
> - `templates/review-report.md`에 Standalone Input Source, Reviewer Role Summary, Override Log, Standalone Mode Metadata 섹션이 있습니다.
> - `evals/evals.json`에 canonical standalone review eval inventory가 있습니다. 초기 6개 baseline(id 39-44)에 더해 ambiguous input, URL/file evidence, patch scope, advisory boundary, provenance, role-packet handoff cases가 추가되어 현재 계약을 검증합니다.
> - 이 문서는 참조용으로 보존합니다.

대상: ForgeFlow 개발봇

## 목표

기존 `clarify → plan → execute → review → ship` 구조는 유지하되, `review`를 `execute` 이후 전용 후속 단계가 아니라 **독립 진입점**으로도 실행 가능하게 확장한다.

핵심은 다음 3가지다.
- 입력이 `URL / repo / diff / 파일 묶음`이어도 바로 리뷰 가능해야 함
- 내부 처리 입력은 `artifact + evidence + scope`로 정규화할 것
- AI 리뷰는 참고 자료이며, 최종 승인/판단은 사람에게 남길 것

## 배경

현재 ForgeFlow는 작업 실행 후 검증하는 흐름에 강하지만, 다음 같은 사용 사례를 더 잘 지원할 필요가 있다.
- PR/코드 리뷰만 따로 돌리고 싶다
- 외부 레포/문서/패치만 주고 검토를 받고 싶다
- 실행 단계 없이도 리뷰 템플릿과 evidence 기반 판단을 생성하고 싶다

즉, `review`를 하나의 **독립 검사 게이트**로 확대하는 것이 이번 작업의 목적이다.

## 실행 원칙

- 기존 stage 구조는 유지한다.
- 최소 변경으로 entrypoint만 늘린다.
- 리뷰는 evidence 기반이어야 한다. 느낌/인상/추측으로 끝내지 않는다.
- 리뷰 결과는 공통 산출물로 남겨 후속 stage가 재사용할 수 있어야 한다.
- 사람 최종판단은 유지한다. AI의 코멘트는 자동 반영하지 않는다.

## 작업 항목

### 1) standalone review entrypoint 추가

`review`를 다음 두 경로로 실행 가능하게 만든다.
- `execute` 이후 후속 review
- 입력만 주는 standalone review

standalone mode는 다음 입력 타입을 허용한다.
- URL
- repo 경로
- diff/patch
- 파일 묶음
- 특정 artifact 경로

### 2) review 입력 정규화

외부 입력이 무엇이든 내부 처리에서는 다음 구조로 변환한다.
- `brief`: 무엇을 리뷰하는지
- `evidence`: 무엇을 근거로 판단하는지
- `scope`: 어떤 범위를 보는지
- `constraints`: 어떤 기준/금지사항이 있는지

이 정규화 결과를 review 하위 단계들이 공통으로 사용하게 한다.

### 3) reviewer 역할 분리

review는 단일 범용 reviewer 1개로 끝내지 말고, 최소 다음 역할로 분리한다.
- `spec-review`
- `quality-review`

필요 시 확장 가능한 역할:
- `security-review`
- `ux-review`
- `perf-review`

역할별 reviewer는 같은 입력을 보되, 서로 다른 체크리스트와 관점을 가진다.

### 4) 공통 review output 포맷 고정

> **구현 메모**: 초기 설계는 JSON 예시를 사용했지만, v1.x slim distribution에서는 모든 산출물을 Markdown으로 유지합니다. 현재 canonical 결과물은 `review-report.md`이며 adapter별 JSON/report 분기는 만들지 않습니다.

모든 review 결과는 단일 공통 포맷으로 합친다.
예: `review-report.md`

최소 포함 필드:
- `verdict`
- `findings`
- `evidence_refs`
- `next_action`
- `blockers`

가능하면 stage별로 재사용 가능한 형태로 유지한다.

### 5) 사람 최종판단 규칙 고정

AI 리뷰 결과는 자동 승인 기준이 아니다.
- evidence 없는 코멘트는 낮은 우선순위로 취급
- 상충하는 코멘트는 사람 판단으로 정리
- ship gate에서는 사람이 최종 결정을 내리도록 유지

## 예상 수정 범위

구체 파일명은 레포 구조에 맞게 조정하되, 보통 아래 영역을 본다.
- `skills/ff-review/`
- `templates/`
- `docs/`
- 어댑터별 review 연결부
- review 결과 스키마/템플릿

## 권장 구현 순서

1. standalone review 진입점 설계
2. 입력 정규화 레이어 추가
3. reviewer 역할 분리
4. 공통 review-report 포맷 고정
5. 사람 최종판단 게이트 명시
6. 테스트/검증

## 완료 기준

다음이 확인되면 완료로 본다.
- URL/repo/diff만으로 review를 실행할 수 있다.
- review 입력이 내부에서 표준 artifact 형태로 정리된다.
- role-based review가 분리되어 나온다.
- 결과물이 공통 포맷으로 저장된다.
- AI 리뷰가 자동 승인되지 않는다.

## 개발봇에게 주는 한줄 지시

`review`를 execute 이후 후속 단계에서만 동작하게 두지 말고, standalone entrypoint로도 실행되도록 확장해줘. 입력은 정규화해서 `artifact + evidence + scope`로 처리하고, reviewer role을 분리한 뒤 공통 `review-report` 포맷으로 결과를 내며, 최종판단은 사람에게 남겨줘.
