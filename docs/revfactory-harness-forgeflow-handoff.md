# revfactory/harness → ForgeFlow 흡수안

대상: `revfactory/harness`의 핵심 개념을 ForgeFlow에 흡수하기 위한 개발 핸드오프 문서

## 결론

`revfactory/harness`는 ForgeFlow에 별도 기능으로 복제하지 않고, ForgeFlow의 `init → feature → qa → review` 흐름을 더 강하게 만드는 **초안 생성기**로 흡수한다.

핵심은 다음 세 가지다.

- 도메인 설명을 받으면 먼저 팀 아키텍처를 고른다.
- 에이전트와 스킬을 분리해 초안을 생성한다.
- init 결과가 다음 단계 작업 문서와 자연스럽게 연결되도록 만든다.

## 반영 상태

- P0-1 완료: `skills/clarify`가 있으면 명세 고정 전에 모호성/비범위/가정 분리를 먼저 수행한다.
- P0-2 완료: `skills/plan`은 실행 전에 task breakdown, dependency, verification strategy를 남긴다.
- P0-3 완료: `skills/review`는 실제 evidence 기반 판정을 유지한다.
- P1-4 완료: `docs/`에 runtime/adapter 경계와 workflow 분리를 문서화한다.
- P1-5 완료: `skills/qa`와 `skills/review`는 QA/리뷰를 분리해 독립 검증을 유지한다.

## 가져온 것

### 1) 에이전트 / 스킬 분리

`harness`의 핵심은 다음이다.

- **에이전트** = 누가 수행하는가
- **스킬** = 어떻게 수행하는가

ForgeFlow 적용 위치:

- `.claude/agents/`
- `.claude/skills/`
- `CLAUDE.md`의 트리거 포인터

### 2) 팀 아키텍처 선행 선택

`init`은 단순 파일 생성이 아니라, 작업 유형에 맞는 구조를 먼저 고른다.

흡수할 패턴:

- pipeline
- fan-out / fan-in
- expert pool
- producer-reviewer
- supervisor
- hierarchical delegation

ForgeFlow 적용 위치:

- `skills/init` 또는 `flow-init`
- `docs/ARCHITECTURE.md`
- `docs/PRD.md`

### 3) init은 빈 껍데기가 아니라 초안을 만든다

`harness`의 유효한 점은 init이 실제로 쓸 수 있는 초안을 만드는 것이다.

흡수 원칙:

- 빈 폴더만 만들지 않는다.
- 역할/책임/트리거/검증 규칙이 들어간 초안을 만든다.
- 다음 단계 명령이 이어질 수 있어야 한다.

ForgeFlow 적용 위치:

- `docs/PRD.md`
- `docs/ARCHITECTURE.md`
- `docs/QA.md`
- `tasks/init-summary.md`
- `.claude/agents/*`
- `.claude/skills/*`

### 4) evolve 루프

실행 후 개선점을 다시 구조에 반영하는 점은 유용하다.

ForgeFlow 적용 위치:

- skill update
- doc update
- 리뷰 결과를 다음 init 초안에 반영

## 버릴 것

- Claude Code 전용 강결합 서술
- 지나치게 큰 메타팩토리 철학
- init을 한 번에 모든 걸 끝내는 과도한 오케스트레이터화
- 팀 아키텍처 이름만 늘리고 실제 산출물이 없는 구조

## 구현 범위

### 1) `init` 동작 변경

기존 init이 단순 스캐폴딩이라면 아래 순서로 확장한다.

1. 프로젝트 브리프 수집
2. 도메인/작업 성격 분석
3. 팀 아키텍처 선택
4. 역할별 agent 초안 생성
5. 역할별 skill 초안 생성
6. 문서 초안 생성
7. 포인터 문서 또는 `CLAUDE.md`에 트리거 등록
8. `feature`, `qa`, `review`로 이어질 기본 흐름 연결

### 2) 생성할 기본 산출물

#### 공통 문서

- `docs/PRD.md`
- `docs/ARCHITECTURE.md`
- `docs/QA.md`
- `docs/ADR.md` 또는 `docs/DECISIONS.md`

#### 작업 문서

- `tasks/init-summary.md`
- `tasks/feature/`
- `tasks/qa/`

#### 에이전트 / 스킬

- `.claude/agents/planner.md`
- `.claude/agents/implementer.md`
- `.claude/agents/reviewer.md`
- `.claude/agents/qa.md`

- `.claude/skills/plan/SKILL.md`
- `.claude/skills/build/SKILL.md`
- `.claude/skills/review/SKILL.md`
- `.claude/skills/qa-fix/SKILL.md`

#### 포인터 / 트리거

- `CLAUDE.md` 또는 글로벌 포인터 문서
- init / feature / qa / review 트리거 규칙

### 3) 팀 아키텍처 선택 규칙

ForgeFlow v0에서는 너무 많은 추상화를 넣지 말고 아래처럼 시작한다.

- 기본 패턴: **producer-reviewer + pipeline 혼합**
- 이유:
  - init에서 초안 생성이 중요하다
  - 생성 이후 review로 검증하고 feature/qa로 이어지기 쉽다

### 4) 에이전트 / 스킬 분리 규칙

에이전트 파일에는 다음을 넣는다.

- 역할
- 책임
- 입력 / 출력
- 협업 규칙
- 리뷰 / 에러 처리 규칙

스킬 파일에는 다음을 넣는다.

- 언제 트리거되는지
- 무엇을 해야 하는지
- 참조 문서
- 반복 가능한 실행 절차

### 5) `CLAUDE.md` 포인터 규칙

`CLAUDE.md`에는 전체 규칙을 복붙하지 말고 포인터만 둔다.

- forgeFlow가 존재한다는 포인터
- 트리거 명령
- 상태 / 변경 이력
- 어디를 읽어야 하는지

상세 규칙은 파일로 분리한다.

## 파일별 수정 가이드

### `flow-init`

- 프로젝트 브리프 입력 받기
- 도메인 분석
- 패턴 선택
- 문서 / agent / skill 생성
- 포인터 등록

### `flow-feature`

- 기능 task doc 생성
- planner가 task 구조화
- implementer가 그 문서를 source of truth로 실행

### `flow-qa`

- 버그 / QA task doc 생성
- 재현 / 원인 / 최소 수정 / 회귀 체크리스트 포함

### `flow-review`

- 스펙 갭
- 구조 리스크
- 테스트 부족
- QA watchpoint 점검

## 비범위

이번 작업에서 하지 말아야 할 것.

- heavy한 범용 에이전트 플랫폼화
- DB 기반 워크플로우 엔진화
- Claude Code 전용 과도한 결합
- init에서 모든 기능을 한 번에 완결하려는 과도한 오케스트레이션
- 실제 구현보다 추상 설명만 늘리는 것

## 테스트 요구사항

최소 아래는 확인해야 한다.

1. **init 실행 시**
   - 문서가 실제로 생성되는가
   - agent / skill 초안이 생성되는가
   - 포인터 문서가 갱신되는가

2. **feature 흐름**
   - init 이후 feature task doc가 생성되는가
   - planner → implementer 흐름이 이어지는가

3. **qa 흐름**
   - bug description에서 qa task doc가 만들어지는가
   - 재현 / 수정 / 회귀 체크리스트가 들어가는가

4. **review 흐름**
   - 설계 / 테스트 갭을 실제로 뽑아내는가

5. **문서 품질**
   - 빈 템플릿만 생성되지 않는가
   - 초안 내용이 충분히 들어가는가

## Done 정의

다음이 모두 만족되면 완료로 본다.

- `forgeFlow init`가 harness식 초안을 생성한다.
- agent / skill / doc 구조가 생성된다.
- init 결과가 다음 단계 명령과 연결된다.
- 포인터 문서 또는 `CLAUDE.md`에 트리거가 남는다.
- 테스트로 생성 결과를 검증했다.
- 빈 껍데기 생성이 아니라 실제 초안 생성임이 확인된다.

## 개발자에게 전달할 문구

> `forgeFlow init`를 `revfactory/harness` 스타일로 흡수해줘.
> 단순 스캐폴딩이 아니라, 도메인 분석 → 팀 아키텍처 선택 → agent/skill 초안 생성 → 문서 초안 생성 → 포인터 등록까지 한 번에 되게 해줘.
> `init`, `feature`, `qa`, `review` 흐름이 자연스럽게 이어지도록 만들고, 빈 템플릿만 생성하지 말고 실제로 쓸 수 있는 초안을 생성해줘.
> 구현 후에는 생성 파일 목록, 테스트 결과, 그리고 init이 어떤 아키텍처를 선택했는지 보고해줘.

## 추천 구현 순서

1. `init` 출력 구조 설계
2. 문서 템플릿 추가
3. agent / skill 템플릿 추가
4. 포인터 규칙 추가
5. `feature`, `qa`, `review` 연결
6. 테스트 / 검증
7. 필요 시 `evolve` 개념 추가

## 한 줄 요약

`revfactory/harness`의 핵심은 forgeFlow에 별도 제품으로 붙이는 것이 아니라, `init`이 도메인 설명을 받아 **팀 아키텍처와 초안을 실제로 생성하는 입구**가 되도록 만드는 것이다.
