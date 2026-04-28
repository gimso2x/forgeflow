# Review Model

## 목적
ForgeFlow에서 review는 형식적인 승인 버튼이 아니다.
실행자가 자기 일 잘했다고 말하는 걸 믿지 않고, **독립된 근거로 다음 stage 진입 가능 여부를 판단하는 장치**다.

실제 기계 판정은 `policy/canonical/*.yaml`, `schemas/review-report.schema.json`, `run-state` gate, checkpoint/session-state 동기화가 맡는다. 이 문서는 그 의미를 사람말로 설명한다.

---

## 왜 review가 필요한가

AI 에이전트 workflow에서 제일 흔한 실패는 이거다.

1. 실행자가 spec을 살짝 바꿔 놓고도 성공했다고 주장함
2. 로그나 자기 요약만 보고 승인해버림
3. 구현은 됐는데 유지보수성/검증가능성/잔존 리스크를 안 봄
4. 결국 finalize가 그냥 자기합리화가 됨

ForgeFlow는 이걸 막으려고 review를 stage로 분리한다.

---

## 기본 원칙

### 1. worker self-report는 증거가 아니다
- "됐다"
- "테스트 통과했다"
- "문제 없어 보인다"
- "요약하면 이런 변경이다"

이런 건 참고 메모일 수는 있어도 승인 근거는 아니다.

### 2. review는 stage 의미가 다르다
- `spec-review`는 **원한 걸 맞게 만들었는지** 본다
- `quality-review`는 **지속 가능하고 안전하게 남길 수 있는지** 본다

둘을 섞으면 안 된다.

### 3. review는 artifact와 evidence를 본다
review는 대화 분위기가 아니라 아래를 본다.
- `brief`
- `plan` (해당 route일 때)
- `run-state`
- `review-report`
- `decision-log`
- evidence refs
- checkpoint/session-state가 가리키는 최신 상태

### 4. review failure는 그냥 불쾌한 코멘트가 아니다
review가 실패하면 다음 stage로 못 간다.
특히 `spec-review` 실패를 품질 코멘트로 얼버무리고 `quality-review`로 넘기는 건 금지다.

---

## `spec-review`가 보는 것

`spec-review`의 질문은 단순하다.

> 이 결과물이 brief/plan/acceptance criteria 기준으로, 원하는 걸 맞게 만들었나?

### 주요 확인 항목
- acceptance criteria 충족 여부
- in-scope / out-of-scope 경계 준수
- spec drift 여부
- 필수 evidence 존재 여부
- 다음 stage로 넘어가도 되는지

### 주로 믿는 것
- `brief`의 목표/범위/성공조건
- `plan`의 단계/기대 산출물/검증 방법
- 실제 결과 artifact
- 명시적 evidence refs
- `review_type=spec`에 맞는 검토 결과

### 믿으면 안 되는 것
- worker의 구두 요약
- 실행 로그만 보고 내린 낙관적 해석
- "대충 의도는 맞음" 같은 분위기 판정
- quality 관점의 장점으로 spec 미충족을 덮는 행위

### 결과
`spec-review`는 `review-report`를 남긴다.
이 문서는 최소한 아래를 담는다.
- `review_type=spec`
- `verdict`
- `findings`
- 필요 시 `missing_evidence`
- `next_action`
- `safe_for_next_stage`
- `open_blockers`
- `evidence_refs`

---

## `quality-review`가 보는 것

`quality-review`의 질문은 이거다.

> 이 결과물을 지금 상태로 남겨도 유지보수 가능하고, 검증 가능하고, 리스크가 통제되는가?

### 주요 확인 항목
- 구조 단순성
- 테스트/검증 품질
- evidence 품질
- 잔존 리스크 공개 여부
- 다음 운영 단계로 넘겨도 되는지

### 주로 믿는 것
- spec review 통과 사실
- `run-state`의 현재 상태와 gate
- review artifacts
- evidence refs
- unresolved risk / open blockers 기록

### 믿으면 안 되는 것
- "동작은 하니까 됐다" 식의 승인
- spec 미충족을 품질 문제처럼 포장하는 것
- 숨겨진 리스크를 무시한 채 finalize로 넘기는 것

### 결과
`quality-review`도 `review-report`를 남긴다.
핵심은 `review_type=quality`로 남는다는 점이다. ForgeFlow는 review 의미를 파일명 감성으로 추측하지 않고, report 타입과 gate로 본다.

---

## reviewer가 신뢰할 수 있는 것 / 없는 것

### 신뢰할 수 있는 것
- canonical artifact
- schema-valid review report
- `task_id`가 맞는 artifact
- evidence refs가 실제로 가리키는 파일/결과
- checkpoint/session-state가 가리키는 최신 review ref

### 신뢰하면 안 되는 것
- task와 안 맞는 artifact
- schema는 맞지만 내용상 근거 없는 낙관
- stale review ref
- worker 자기보고
- transcript vibes

---

## evidence는 뭐가 되어야 하나

좋은 evidence는 reviewer가 **다시 읽고 다시 판단할 수 있는 것**이다.

예시:
- 검증 결과가 남은 artifact
- review report의 `evidence_refs`
- checkpoint/session-state에 기록된 최신 review 참조
- run-state gate와 일치하는 산출물

나쁜 evidence 예시:
- "방금 테스트 돌려봤음"
- "문제 없어 보였음"
- "로그상 괜찮았음"

---

## Claude adapter의 subagent/team 사용 경계

Claude Code처럼 subagent나 agent team을 지원하는 runtime에서는 review를 더 잘 분리할 수 있다. 다만 이건 ForgeFlow workflow primitive가 아니라 adapter 실행 방식이다.

허용되는 사용:
- `producer-reviewer`: worker와 reviewer context를 분리해 self-approval을 줄인다.
- `fan-out-fan-in`: large/high-risk 작업에서 repo surface, test/CI, risk surface를 병렬 조사한 뒤 coordinator가 artifact로 병합한다.
- `expert-pool`: security/docs/frontend/test 같은 전문 reviewer를 상황별로 고른다.

경계 규칙:
- subagent output은 evidence 후보일 뿐이고, canonical truth는 `plan-ledger.json`, `run-state.json`, `review-report.json`, `eval-record.json` 같은 artifact다.
- subagent나 agent team은 artifact gate, review 순서, schema validation을 우회할 수 없다.
- worker 자기보고만 reviewer에게 넘기면 안 된다. reviewer는 diff, artifacts, evidence refs를 직접 확인해야 한다.

---

## Git safety and diff-scope policy

Git safety is adapter-neutral policy. It applies the same way to Claude, Codex, and any future ForgeFlow adapter; a tool may add guardrails, but the workflow rule lives here.

- Broad staging is forbidden unless explicitly justified. Prefer path-limited staging of the files that belong to the approved task.
- Destructive git actions require explicit user approval: reset, checkout/restore of user changes, clean, rebase that rewrites local work, force push, or deleting branches/tags.
- Dirty user work is preserved by default. If unrelated modifications exist, do not sweep them into the task commit and do not "clean up" unless the user asked for that exact cleanup.
- Reviews must name the exact diff scope and verification evidence. A review should say which files/commits it inspected and which commands or artifacts back the verdict.
- If broad staging or a destructive action is unavoidable, record the reason and the user's approval in the task artifact or decision log.

This is policy, not a new command surface. ForgeFlow does not need a dedicated commit-safety stage to enforce basic git hygiene; review and ship gates should reject sloppy diff ownership.

---

## finalize와 review의 관계

`finalize`는 review를 대체하지 않는다.
오히려 반대다.

- spec-review 승인 전 finalize 금지
- quality-review 승인 전 high-risk finalize 금지
- `run-state.spec_review_approved`, `run-state.quality_review_approved` 같은 승인 flag가 안 섰으면 필요한 finalize gate를 통과할 수 없다
- `verdict=approved`인 review-report는 `open_blockers=[]`이고, `safe_for_next_stage`가 있으면 반드시 `true`여야 한다. blocker가 있거나 `safe_for_next_stage=false`면 schema/runtime 양쪽에서 승인으로 취급하지 않는다.
- unresolved risk가 있으면 숨기지 않고 남겨야 함
- finalize는 종료 처리이지, 면죄부가 아니다

---

## long-run과 review의 관계

large/high-risk route에서는 review가 끝이라고 보면 안 된다.
`long-run`은 반복 가치가 있는 패턴, 실패 규칙, 평가 결과를 남기는 단계다.
즉 review는 현재 작업 승인이고, long-run은 재사용 가능한 학습 축적이다.

---

## 한 줄 규칙

> 실행자가 자기 일 잘했다고 말하는 건 로그다. 승인 근거는 아니다.

ForgeFlow의 review 모델은 바로 그 선을 지키기 위해 존재한다.
