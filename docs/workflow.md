# Workflow

## 목적
새 harness의 실행 흐름을 stage 기준으로 고정한다.
이 문서는 stage 의미와 전환 규칙을 설명한다.
실제 기계 판정은 `policy/canonical/*.yaml`과 `schemas/*.json`이 맡는다.

---

## 1. Stage overview

## Request journey

### Canonical path
`user request -> clarify -> route selection -> optional milestone -> plan/execute -> review -> finalize`

- 정상 진입은 항상 `clarify`부터 시작한다
- `clarify`가 brief를 만들고 route를 정한다
- route가 정해지면 해당 complexity path를 따른다
- `epic` route는 실행 전에 `milestone`으로 큰 작업을 독립 검증 가능한 단위로 나눈다

### Operator fallback path
`operator start/run -> persisted state reuse or auto-route -> same canonical stages`

- direct CLI 진입은 operator convenience surface다
- state가 있으면 그걸 재사용한다
- state가 없을 때만 auto routing을 쓴다
- 이 fallback도 canonical stage semantics를 바꾸지는 못한다

---

### 1) `clarify`
목표:
- 요청을 실행 가능한 단위로 정리한다.
- 성공 조건, 비목표, 제약, 리스크를 명시한다.

입력:
- user request
- project context
- existing constraints

출력:
- `brief`

실패 조건:
- 핵심 요구가 모호한데도 추측으로 넘어가려 할 때

---

### 2) `milestone`
목표:
- `epic` route의 큰 범위를 milestone 단위로 분할한다.
- 각 milestone의 목표, 의존성, 검증 방법, review boundary를 명시한다.

입력:
- `brief` (`route=epic`)
- project context

출력:
- `milestone` artifact
- milestone별 plan/review boundary

규칙:
- `milestone`은 epic route에서만 필수다.
- milestone은 단순 task list가 아니라 독립적으로 검증 가능한 delivery slice여야 한다.
- 각 milestone은 완료 조건과 rollback/recovery note를 가져야 한다.

---

### 3) `plan`
목표:
- 작업을 실행 가능한 순서와 검증 단위로 쪼갠다.

입력:
- `brief`

출력:
- `plan`
- 필요 시 `decision-log` 초기 항목

규칙:
- plan은 서술문이 아니라 executor input이어야 한다.
- 각 단계는 기대 산출물과 검증 방법을 가져야 한다.

---

### 4) `execute`
목표:
- 승인된 brief/plan 기준으로 실제 작업을 수행한다.

입력:
- `brief`
- `plan` (medium 이상)

출력:
- `decision-log`
- `run-state`
- 필요 시 작업 결과물 참조

규칙:
- 실행 중 중요한 변경 판단은 `decision-log`에 남긴다.
- 상태 변화는 `run-state`에 반영한다.
- spec을 묵시적으로 다시 쓰면 안 된다.

---

### 5) `spec-review`
목표:
- 원하는 걸 맞게 만들었는지 본다.
- `review`가 standalone entrypoint로 들어온 경우에도 입력을 먼저 `review-input`으로 정규화한 뒤 같은 기준을 적용한다.

입력:
- `brief`
- `plan`
- `run-state`
- evidence
- standalone `review-input` (`brief + evidence + target_scope`)

출력:
- `review-report` (`review_type=spec`)

규칙:
- worker 자기보고는 증거가 아니다.
- acceptance criteria 기준으로 통과/실패를 판정한다.
- 실패하면 quality-review로 넘어가지 않는다.
- standalone 입력이 URL/repo/diff/파일 묶음뿐이면 reviewer가 추측하지 않고 `review-input.json`의 brief, evidence refs, target scope로 먼저 접는다.

---

### 6) `quality-review`
목표:
- 결과물이 유지보수 가능하고 검증 가능하며 위험이 통제되는지 본다.
- standalone review에서는 spec-review와 함께 기본 review role로 실행된다.
- small route에서는 별도 `spec-review` stage가 없으므로 `brief.json`의 acceptance criteria 검증도 여기서 함께 수행한다.

입력:
- spec review 통과 결과
- `run-state`
- evidence

출력:
- `review-report` (`review_type=quality`)
- small route의 경우 `review-report.json`에 `spec_absorbed: true`, acceptance criteria별 verdict/evidence, quality verdict가 함께 있어야 한다.

규칙:
- 구조, 단순성, 테스트/검증 품질, 잔존 리스크를 본다.
- spec 미충족을 품질 문제로 얼버무리면 안 된다.
- small route에서는 spec-review 책임을 흡수한다. 즉 quality-review gate가 spec conformance와 quality를 모두 판정하고 `review-report.json`에 둘 다 기록해야 한다.
- `security-review`, `ux-review`는 별도 stage가 아니라 `review-input.review_roles`로 확장되는 선택 lens이며, 결과는 같은 `review-report.json` 포맷으로 병합한다.

---

### 7) `finalize`
목표:
- 현재 작업을 종료 가능한 상태로 마감한다.

입력:
- `run-state`
- review 결과

출력:
- finalized `run-state`
- 필요 시 handoff note

규칙:
- 모든 필수 gate를 통과해야 한다.
- unresolved risk는 숨기지 않고 남긴다.

---

### 8) `long-run`

#### When does this trigger?

Triggered automatically at the end of high-risk route finalize,
or invoked manually via `/forgeflow:long-run` after any task where
reusable patterns were identified. Not automatically triggered for small/medium routes,
but can be invoked manually.

목표:
- 반복 가치가 있는 학습만 축적한다.

입력:
- finalized state
- review 결과

출력:
- `eval-record`
- optional memory note

규칙:
- 세션 잡담을 memory로 던지지 않는다.
- 재사용 가능한 패턴, 실패 규칙, 평가 결과만 남긴다.

#### Stage name mapping (slash command → canonical stage)

| Slash command | Canonical stage | Description |
|---|---|---|
| /forgeflow:ship | finalize (part 1) | evidence 묶음, final handoff/report 생성 |
| /forgeflow:finish | finalize (part 2) | branch disposition: merge / PR / keep / discard |
| /forgeflow:review | spec-review + quality-review | route에 따라 두 review stage를 순서대로 실행 |
| /forgeflow:long-run | long-run | high-risk finalize 후 학습 기록 또는 수동 reusable learning 기록 |

Note: finalize in workflow.md covers both ship and finish concerns. The slash commands split this into two user-facing steps for explicit control.

---

## 2. Complexity routing

route label canonical values: small, medium, large_high_risk (CHANGELOG 0.3.2 기준)

기본 경로는 `clarify-first`다. 즉, 정상 진입은 항상 `clarify`에서 시작하고 여기서 brief와 route를 정한다.

다만 operator가 아무 state 없이 runtime `start`/`run`에 바로 들어오면 fallback auto routing이 route를 고를 수 있다. 이 경우에도 선택된 route의 첫 stage는 여전히 `clarify`이며, auto routing은 정본 workflow를 대체하지 않는다.

### Role-split execution rule
역할 분리는 새 stage가 아니라 기존 stage를 더 엄격하게 운영하는 방식이다. `clarify`는 요청을 역할 단위로 나눌 필요가 있는지 판단하고, `plan`은 선택된 역할별 task와 handoff를 `plan-ledger`에 남기며, `execute`는 필요한 worker만 on-demand로 호출한다. `review`는 reviewer/QA/security/UX 같은 관점을 필요한 만큼 분리하되, 각 관점의 판단 근거는 `review-report`와 evidence ref로 합쳐야 한다.

#### 2-axis agent selection

ForgeFlow는 **두 개의 독립적인 축**으로 에이전트를 선택한다:

**Axis 1 — Route → Stage 깊이** (기존)
- `small` / `medium` / `large_high_risk` → 각 route가 실행할 stage 시퀀스를 결정
- 예: small = clarify→execute→quality-review→finalize
- 예: large_high_risk = clarify→milestone→plan→execute→spec-review→quality-review→finalize→long-run

**Axis 2 — Spec → 전문 에이전트** (신규)
- `brief.required_specialists` → clarify 단계에서 작업 성격에 따라 판단
- 사용 가능 전문 에이전트:
  - **review**: security-reviewer, ux-reviewer, perf-reviewer
  - **execute**: frontend-worker, backend-worker, infra-worker
- 판단 기준:
  - 인증/권한/암호화/외부입력 → `security-review`
  - UI/접근성/사용자흐름 → `ux-review`
  - 응답시간/메모리/대규모데이터 → `perf-review`
  - 프론트엔드 중심 작업 → `frontend-execute`
  - 백엔드/API/DB 작업 → `backend-execute`
  - 인프라/배포/IaC → `infra-execute`

**핵심 원칙:**
- 두 축은 독립적이다. route가 small이어도 security-review가 필요할 수 있고, route가 high/epic이어도 specialist가 없을 수 있다.
- 전문 에이전트는 항상 활성화가 아니라 clarify에서 **on-demand**로만 판단한다.
- skip한 전문가는 `brief.skipped_specialists` + `brief.skip_rationale`에 반드시 사유를 남긴다. 새 brief가 `required_specialists` 또는 `skipped_specialists`를 쓰기 시작하면 `clarification_complete` gate는 모든 canonical specialist가 `required_specialists` 또는 `skipped_specialists` 중 하나에 명시되지 않으면 실패한다. legacy brief처럼 두 필드가 모두 없으면 migration compatibility를 위해 통과한다.
- `required_specialists`가 비어 있으면 기본 worker/reviewer만 사용한다.

플랜 우선 원칙은 모든 route에 적용된다. 작은 작업도 최소 brief와 실행 근거를 남기고, medium/large_high_risk 작업은 구현 전에 plan-ledger task, expected output, verification, role owner를 먼저 확정한다. 구현자는 이 ledger 밖의 일을 선반영하지 않는다.

사람 최종판단 원칙은 review gate를 약화하지 않는다. AI reviewer의 코멘트는 자동 정답이 아니라 evidence-backed finding 후보이며, ship/finalize 전에는 실제 영향도와 프로젝트 맥락을 사람이 판단할 수 있게 근거를 남겨야 한다.

### Parallel work safety

Parallel implementation is allowed only after `plan` has made task boundaries machine-readable. Each parallel task must have a distinct `plan-ledger.tasks[].id`, an explicit `files` list, and a correct `parallel_safe` value. Shared documents and release/version surfaces follow a single-writer rule; they may be read by many workers but edited by only one active task. Mutating workers should use separate git worktrees or clearly isolated terminal sessions, and final merge/ship remains serialized through review evidence. See [Parallel Work Safety](parallel-work.md) for the full operator checklist.

### small
`clarify -> execute -> quality-review -> finalize`

Note: `spec-review` is intentionally omitted for small routes to avoid forcing the full process onto low-risk single-scope tasks. Acceptance criteria from `brief.json` are verified inline during `quality-review`. The small-route `quality-review` gate MUST check both spec conformance and quality, and `review-report.json` MUST document both, including `spec_absorbed: true` and evidence for each acceptance criterion.

Small-route `review-report.json` shape:

```json
{
  "review_type": "quality",
  "spec_absorbed": true,
  "acceptance_criteria": [
    {"criterion": "...", "verdict": "pass|fail|blocked", "evidence_refs": ["..."]}
  ],
  "quality_verdict": "approved|changes_requested|blocked",
  "findings": [],
  "blockers": []
}
```

적용 대상:
- 저위험 단건 수정
- 짧은 문서 보정
- 구조 영향이 적은 변경

### medium
`clarify -> plan -> execute -> quality-review -> finalize`

적용 대상:
- 여러 파일에 걸치는 기능/리팩터
- 구현 전에 순서 분해가 필요한 작업

### large_high_risk
`clarify -> plan -> execute -> spec-review -> quality-review -> finalize -> long-run`

적용 대상:
- 아키텍처 영향
- 배포/운영/데이터 손실 위험
- 긴 실행 시간과 재개 가능성이 중요한 작업

### epic
`clarify -> milestone -> plan -> execute -> spec-review -> quality-review -> finalize -> long-run`

적용 대상:
- 여러 milestone으로 나눠야 하는 massive scope 작업
- 장기 실행, 재개, checkpoint, milestone별 review가 필요한 작업
- 여러 large_high_risk 변경이 의존성으로 묶여 한 번에 관리되어야 하는 작업

---

## 3. Non-negotiable rules
Stage 규칙은 `policy/canonical/stages.yaml`의 `non_negotiables`가 정본이다. 이 섹션은 사람이 읽는 해설이고, `make validate`가 각 stage의 핵심 용어와 최소 개수를 검사한다.

### Stage-level non-negotiables

#### `clarify`
- ambiguity를 해결하거나 명시적으로 bounded 처리하기 전 실행 금지
- `brief`는 objective, scope, constraints, acceptance criteria, risk level을 가져야 함
- route는 agent 자신감이 아니라 evidence 기준으로 선택

#### `plan`
- 다른 agent가 hidden chat context 없이 실행할 수 있어야 함
- 모든 step은 expected output과 verification을 가져야 함
- risky/multi-file 작업은 rollback 또는 recovery note를 포함

#### `execute`
- approved brief/plan 범위를 벗어나면 안 됨
- 중요한 판단과 deviation은 `decision-log`에 기록
- `run-state`는 current stage, gates, retries, review approval flags를 반영

#### `spec-review`
- reviewer는 acceptance criteria를 artifact/evidence와 대조해야 함
- worker self-report는 evidence가 아님
- rejected/blocked spec-review면 quality-review와 finalize 금지

#### `quality-review`
- maintainability, verification quality, residual risk를 판단
- spec miss를 quality issue로 세탁 금지
- small route에서는 acceptance criteria 검증을 함께 수행하고 `review-report.json`에 `spec_absorbed: true`와 criterion별 evidence를 기록
- finalize 전 `run-state.quality_review_approved`가 필요

#### `finalize`
- required review approvals와 evidence 없이 finalize 금지
- unresolved risk는 숨기지 않고 기록
- final state는 chat history가 아니라 artifacts로 재현 가능해야 함

#### `long-run`
- reusable learning, evaluation, durable failure pattern만 축적
- session chatter나 one-off task progress를 memory로 저장 금지
- `eval-record.json`는 왜 보존 가치가 있는지 설명해야 함

### Global rules
1. artifact 없는 stage 전환 금지
2. worker와 reviewer 분리
3. spec-review 실패 시 quality-review 금지
4. runtime adapter가 workflow semantics를 바꾸면 안 됨
5. bounded recovery만 허용
6. 작은 일까지 무조건 full process 강제 금지


## Related operator docs

- [Parallel Work Safety](parallel-work.md) — worktree/terminal isolation, single-writer shared docs, and `parallel_safe` rules.
- [Developer Handoff Template](developer-handoff-template.md) — executable handoff format for developers and AI coding agents.
- [Role / Model Routing](role-model-routing.md) — canonical planning/implementation/review/qa responsibilities and model binding guidance.

## Evolution graduation contract

Proposal → promotion → crystallization은 블랙박스가 아니다. 기본 졸업 조건:

1. 입력 신호: `eval-record.json`, review finding, repeated tool failure, manual operator note 중 하나 이상.
2. Evidence: 재현 가능한 artifact ref와 실패/개선 전후 설명.
3. Audit: `evolution_audit`가 scope, confidence, source_count를 기록.
4. Promotion: hard rule은 테스트 또는 policy 검증이 붙을 때만, soft rule은 제한된 scope와 rollback note가 있을 때만.
5. Crystallization: promoted rule이 반복 task에서 재사용 가능하고 기존 canonical stage/gate semantics를 약화하지 않는 경우만 문서/skill로 승격한다.

`eval-record.json`는 기록으로 끝나지 않는다. evolution pipeline의 signal source이며 routing threshold나 specialist 선택을 바꾸려면 proposal/audit/promotion artifact를 통해 변경 근거를 남겨야 한다.
