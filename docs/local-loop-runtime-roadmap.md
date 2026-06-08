# Local Loop Runtime Roadmap

> **Status**: implemented in 2.0.0; retained as the completed roadmap and historical product rationale  
> **Scope**: ForgeFlow markdown-only distribution에 "로컬 루프 실행" 개념을 얹는 단계별 제품 로드맵  
> **Principle**: 기존 `small` / `medium` / `high` / `epic` route 모델은 유지한다. route는 작업 복잡도와 위험도를 분류하고, loop runtime은 각 route 안에서 반복 실행·검증·리뷰·병합을 자동화한다.

## 1. 핵심 판단

ForgeFlow가 가야 할 방향은 "프롬프트 더 잘 쓰기"가 아니라 **루프를 설계하고 돌리는 도구**다.

Claude Code식 작업의 진짜 변화는 한 번의 거대한 프롬프트가 아니다. 작은 목표를 만들고, 실행하고, 검증하고, 실패를 다시 큐에 넣고, 통과한 변경만 합치는 반복 루프다. ForgeFlow는 이미 route와 artifact 계약을 갖고 있으니, 다음 단계는 이 계약을 로컬에서 계속 굴러가는 runtime loop로 만드는 것이다.

## 2. 유지할 것과 바꿀 것

### 유지

- Route vocabulary: `small`, `medium`, `high`, `epic`
- Stage contract: `clarify`, `plan`, `execute`, `review`, `ship`, `long-run`
- Artifact-first 원칙: 말이 아니라 `brief.md`, `plan.md`, `ledger.md`, `implementation-notes.md`, `review-report.md`, `ship-summary.md`로 상태를 남긴다.
- Markdown-only distribution 원칙: public package는 계속 얇게 유지한다.
- 사용자 승인 경계: push, release, external side effect는 명시적 승인 없이는 하지 않는다.

### 바꿀 것

- 현재 ForgeFlow는 에이전트가 따라야 하는 절차서에 가깝다.
- 목표 상태는 **로컬 작업 큐 + route classifier + loop runner + verification gate + merge ledger**다.
- 즉, "명령을 잘 설명하는 skill"에서 "작업을 반복적으로 끝까지 밀어붙이는 local supervisor"로 간다.

## 3. Route별 loop 의미

### `small`

- 목적: 폰에서도 바로 보낼 수 있는 작은 수정 루프.
- 흐름: `clarify -> execute -> self-verify -> ship`
- 특징:
  - 별도 review는 기본 생략.
  - 단, self-verify가 Goal Contract evidence를 못 채우면 `medium`으로 승격한다.
  - 단일 worktree 또는 현재 브랜치에서 수행 가능.
- 예시:
  - 문서 한두 곳 수정
  - 단일 파일 버그픽스
  - 명확한 테스트 하나 고치기

### `medium`

- 목적: 일반적인 기능/버그 작업을 안전하게 닫는 루프.
- 흐름: `clarify -> plan -> execute -> review -> ship`
- 특징:
  - plan에서 작업을 쪼갠다.
  - execute가 실제 변경과 검증 로그를 남긴다.
  - review가 독립적으로 blocker를 판정한다.
- 예시:
  - 여러 파일에 걸친 기능 추가
  - shared state 수정
  - 테스트 표면이 두세 영역으로 나뉘는 작업

### `high`

- 목적: 위험한 변경을 spec review와 quality review로 분리해 통과시키는 루프.
- 흐름: `clarify -> plan -> execute -> spec-review -> quality-review -> ship -> long-run`
- 특징:
  - 보안, 인증, 데이터 마이그레이션, 인프라, irreversible change는 기본 `high`다.
  - worktree isolation을 기본값으로 본다.
  - merge 전 verification floor가 높다.
- 예시:
  - auth/session 변경
  - DB migration
  - 배포/CI/CD 변경
  - 데이터 손실 가능성이 있는 리팩터링

### `epic`

- 목적: 여러 milestone을 가진 큰 작업을 작은 루프 여러 개로 분해한다.
- 흐름: `clarify -> roadmap -> milestone loops -> integration review -> ship -> long-run`
- 특징:
  - `roadmap.md`가 필수다.
  - 각 milestone은 다시 `small`/`medium`/`high` route로 분류된다.
  - epic 자체는 직접 구현 단위가 아니라 loop orchestration 단위다.
- 예시:
  - 에이전트 runtime 도입
  - adapter 전면 개편
  - 다중 리포 마이그레이션

## 4. 목표 아키텍처

```text
User request / issue / backlog item
        |
        v
[Clarify + route classifier]
        |
        v
[Task directory]
  brief.md
  plan.md
  ledger.md
  checkpoint.md
  implementation-notes.md
  review-report.md
  ship-summary.md
        |
        v
[Loop runner]
  - pick next actionable item
  - run assigned agent/adapter
  - collect diff + command evidence
  - update ledger/checkpoint
  - classify pass/fail/blocker
        |
        v
[Verification gate]
  - real command output only
  - no invented evidence
  - route-specific review floor
        |
        v
[Merge / ship boundary]
  - local merge when safe
  - push/release only with user approval
```

## 5. Phase 로드맵

## Phase 0 — 계약 정리

**목표**: runtime을 만들기 전에 지금 markdown 계약을 loop-friendly하게 정리한다.

**작업**:
- `skills/forgeflow/SKILL.md`의 route model을 canonical source로 유지한다.
- `templates/ledger.md`에 loop item 상태를 명확히 한다: `pending`, `in_progress`, `blocked`, `done`, `discarded`.
- `templates/checkpoint.md`에 다음 실행 포인터를 명확히 한다.
- `templates/implementation-notes.md`에 command evidence 형식을 고정한다.

**완료 기준**:
- agent가 context compression 이후에도 `checkpoint.md`만 보고 다음 행동을 재개할 수 있다.
- `make validate` 통과.

## Phase 1 — Local loop spec

**목표**: 실제 코드를 만들기 전, local loop의 상태 머신을 문서로 고정한다.

**작업**:
- `docs/local-loop-runtime-contract.md` 작성.
- route별 loop transition 정의.
- 실패 유형 정의:
  - `verification_failed`
  - `review_blocked`
  - `scope_drift`
  - `needs_user_decision`
  - `agent_error`
- retry budget 정의:
  - `small`: 1~2회
  - `medium`: 3회
  - `high`: 명시적 blocker triage 후 재시도
  - `epic`: milestone 단위 재계획

**완료 기준**:
- runtime 없이도 agent가 동일한 loop semantics를 따를 수 있다.
- route 승격/강등 조건이 문서에 박힌다.

## Phase 2 — Minimal local runner

**목표**: Markdown artifact를 읽고 다음 행동을 계산하는 작은 로컬 CLI를 만든다.

**형태**:

```bash
forgeflow-loop status --task-dir <task-dir>
forgeflow-loop next --task-dir <task-dir>
forgeflow-loop record --task-dir <task-dir> --status done --evidence <file>
```

**범위**:
- 외부 의존성 추가 금지.
- Python stdlib 또는 shell script 수준.
- 코딩 에이전트 호출은 아직 하지 않는다.
- artifact parser도 느슨하게 시작한다. Markdown frontmatter + heading 기반이면 충분하다.

**완료 기준**:
- `ledger.md`와 `checkpoint.md`를 읽어 다음 actionable item을 출력한다.
- 완료/차단 상태를 기록한다.
- `make validate`에 CLI smoke를 추가한다.

## Phase 3 — Agent execution adapter

**목표**: local runner가 Claude/Codex/Gemini 같은 adapter를 호출할 수 있게 한다.

**작업**:
- adapter별 command template 정의.
- route별 model tier 매핑은 기존 adapter config를 따른다.
- 작업 지시는 항상 task artifact를 입력으로 준다.
- agent output은 `implementation-notes.md`와 `ledger.md`에 append한다.

**중요 원칙**:
- runtime이 agent의 말을 믿으면 안 된다.
- diff, command output, file existence 같은 검증 가능한 증거만 통과시킨다.
- adapter smoke는 disposable repo/worktree에서만 돌리고, real repo를 직접 건드리지 않는 단일 파일 변경 + verification diff/stat만 evidence로 남긴다.

**완료 기준**:
- disposable repo에서 `small` task 하나를 runner가 agent에 넘기고, 검증 커맨드 결과까지 기록한다.
- 실패 시 같은 item을 다시 큐에 넣거나 blocker로 전환한다.

## Phase 4 — Worktree fan-out/fan-in

**목표**: 복수 작업을 격리된 worktree에서 병렬 실행하고 안전하게 합친다.

**작업**:
- `medium` 이상에서 worktree isolation 옵션을 지원한다.
- `epic` milestone 또는 `medium/high` plan item을 worker 단위로 나눈다.
- path ownership을 ledger에 기록한다.
- 같은 파일 또는 보호 경로 충돌 시 병렬 금지.
- merge 전 verification gate를 통과해야 한다.

**완료 기준**:
- 독립 파일을 수정하는 두 worker가 병렬 실행된다.
- 한 worker 실패가 전체 loop를 즉시 망치지 않는다.
- merge 후 전체 검증이 다시 실행된다.

## Phase 5 — Phone-friendly queue

**목표**: 사용자가 폰에서 짧게 던진 지시를 backlog/issue/PR 루프로 연결한다.

**작업**:
- 자연어 요청을 task queue item으로 저장한다.
- route classifier가 `small`/`medium`/`high`/`epic`을 추천한다.
- 사용자는 route override만 할 수 있으면 된다.
- 완료 보고는 Telegram에서 5줄 이내 evidence packet으로 낸다. 고정 순서는 changed files → verification → diff summary → rollback note → next action이다.

**완료 기준**:
- 사용자가 "이거 고쳐" 수준으로 말해도 runner가 brief 초안을 만들고 route를 제안한다.
- 실행 결과는 PR 번호보다 먼저 증거와 상태를 보여준다.

## Phase 6 — Learning loop

**목표**: 반복 실패와 좋은 해결 패턴을 다음 loop에 반영한다.

**작업**:
- `long-run` stage에서 eval-record를 남긴다.
- 반복 blocker를 rule candidate로 축적한다.
- 좋은 command/evidence pattern은 shared discipline에 반영 후보로 남긴다.
- 자동 승격은 금지. 사람이 승인한 rule만 canonical로 올린다.

**완료 기준**:
- 같은 유형의 실패가 다음 작업에서 preflight warning으로 뜬다.
- skill/template 수정은 `make validate`를 통과해야만 반영된다.

## 6. Route classifier 계약

기존 점수 모델은 유지한다.

```text
raw_score = file_count*1.0 + estimated_lines*0.1 + requirement_count*2.0 + dependency_count*1.5 + risk_keywords*3.0
```

- `< 10`: `small`
- `10-16.9`: `medium-light`
- `17-24.9`: `medium-full`
- `25-49.9`: `high`
- `>= 50`: `epic`

다만 loop runtime에서는 이 점수를 시작점으로만 쓴다. 아래 조건은 점수보다 우선한다.

- auth/security/credential/payment/data-loss 가능성: 최소 `high`
- irreversible migration: 최소 `high`
- milestone이 3개 이상이거나 다중 주차 작업: `epic`
- self-verify가 실패한 `small`: `medium`으로 승격
- review blocker가 2회 반복된 `medium`: `high`로 승격

## 7. MVP 정의

MVP는 거창하면 망한다. 첫 버전은 이 정도면 된다.

- `docs/local-loop-runtime-contract.md`
- `templates/ledger.md` loop 상태 강화
- `templates/checkpoint.md` resume pointer 강화
- `forgeflow-loop status/next/record` 최소 CLI
- disposable repo에서 `small` route 1개 end-to-end smoke
- `make validate` 통과

여기까지 되면 ForgeFlow는 "문서형 하네스"에서 "작게 굴러가는 로컬 루프"로 넘어간다. 이게 핵심이다.

## 8. 하지 말 것

- 처음부터 150 PR 자동 merge를 목표로 잡지 말 것. 그건 결과지 출발점이 아니다.
- SaaS dashboard부터 만들지 말 것. 로컬 artifact와 CLI가 먼저다.
- route vocabulary를 새로 만들지 말 것. `small`/`medium`/`high`/`epic`이면 충분하다.
- agent output을 성공 증거로 취급하지 말 것. 성공 증거는 command output, diff, 파일, 리뷰 artifact다.
- markdown-only 배포 원칙을 깨지 말 것. runtime은 optional/local layer로 시작한다.

## 9. 한 줄 결론

ForgeFlow의 다음 진화는 **prompt framework가 아니라 route-aware local loop supervisor**다. `small`/`medium`/`high`/`epic`으로 복잡도를 나누고, 각 route 안에서 실행·검증·리뷰·재시도·병합을 반복시키면 된다.
