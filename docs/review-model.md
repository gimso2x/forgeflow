# ForgeFlow Review Model

ForgeFlow review는 automated review와 human review를 분리합니다. Automated review는 반복 가능한 evidence gate이고, human review는 변경 위험도가 사람 판단을 요구할 때 실행하는 decision-partner loop입니다.

## 리뷰 계층 (Review Layers)

### 1. 자동 리뷰 (Automated Review)

Automated review는 기본 `/forgeflow:review` 동작입니다.

- `spec-reviewer`: 구현이 `brief.md`, `plan.md`, scope boundary, acceptance criteria를 만족하는지 확인합니다.
- `quality-reviewer`: 유지보수성, 검증 품질, 잔여 위험, 불필요한 복잡도를 확인합니다.
- 선택 specialist role(`security-reviewer`, `ux-reviewer`, `perf-reviewer`)은 scope나 명시 focus가 트리거할 때 실행합니다.
- Automated review는 읽기 전용이며 `review-report.md`를 작성합니다.
- Automated review findings는 evidence이며, 최종 사람 판단을 대체하지 않습니다.

### 2. 사람 리뷰 (Human Review)

Human review는 instruction dump가 아니라 discussion gate입니다.

Reviewer는 decision partner로 다룹니다. Review input에는 다음을 보여줘야 합니다.

- design intent와 선택한 tradeoffs
- known risks와 rollback constraints
- automated review verdict와 open findings
- verification evidence와 missing evidence
- human decision이 필요한 질문

Human review 결과는 다음 중 하나입니다.

- `accepted`: unresolved human concern 없이 ship 진행
- `changes_requested`: 구체 변경을 가지고 execute로 복귀
- `risk_accepted`: residual risk를 명시 기록하고 진행
- `deferred`: ship하지 않고 branch/worktree 유지

## 복잡도 기반 사람 리뷰 게이트 (Complexity-Based Human Review Gate)

Human review는 아래 조건이 모두 참일 때만 skip할 수 있습니다.

- change scope가 작고 localized입니다.
- implementation이 established pattern을 반복합니다.
- low risk이고 쉽게 revert할 수 있습니다.
- automated verification이 충분하고 최신입니다.
- 유사 prior work가 반복적으로 논의 없이 LGTM을 받았습니다.
- cross-role automated review conflict가 없습니다.

아래 조건 중 하나라도 참이면 human review가 필요합니다.

- public API, CLI surface, workflow contract, artifact schema 변경
- state, data persistence, deletion, migration, branch-disposition behavior 변경
- security, permissions, authentication, secrets, error-recovery behavior 변경
- broad impact, difficult rollback, ambiguous ownership boundary
- 반복된 design disagreement 또는 cross-role reviewer conflict
- automated review가 blocked, weakly evidenced, 또는 required artifact 누락 상태

## 리뷰 입력 묶음 (Review Input Bundle)

Human review가 필요한 변경은 사람이 context를 재구성하지 않도록 compact bundle을 준비합니다.

Minimum bundle:

- `brief.md`: objective, constraints, route, specialist profile
- `plan.md`: task decomposition과 acceptance mapping, 있으면 포함
- `implementation-notes.md`: implementation summary, deviations, metrics, verification
- `run-ledger.md`: command와 gate evidence, 있으면 포함
- `review-report.md`: automated findings, blocker state, evidence classification
- diff summary: changed files와 notable risk areas
- discussion prompts: reviewer에게 물을 specific questions/tradeoffs

## 리뷰 이후 하네스 개선 티켓 (Post-Review Harness Improvement Tickets)

Human review 이후 별도 improvement-ticket pass가 review conversation과 artifacts를 읽고 harness improvement tickets를 만들 수 있습니다. 이 pass는 product code를 직접 수정하면 안 됩니다.

Ticket extraction은 다음 신호를 찾습니다.

- plan 또는 execute guidance 누락을 보여주는 반복 reviewer questions
- human reviewer가 intent를 추론하게 만든 unclear artifacts
- automated review misses 또는 noisy findings
- policy, template, prompt update가 필요한 recurring risk patterns

각 ticket은 다음을 포함해야 합니다.

- title
- problem observed
- review conversation 또는 artifacts의 evidence
- proposed harness/documentation change
- affected stage: `clarify`, `plan`, `execute`, `review`, `ship`, 또는 `long-run`
- suggested priority

## 비목표 (Non-Goals)

- Automated review와 human review를 하나의 role로 합치지 않습니다.
- 모든 small repetitive change에 human review를 강제하지 않습니다.
- Review discussion을 follow-up execute step 없이 바로 code changes로 변환하지 않습니다.
- 결정이 `review-report.md` 또는 `ship-summary.md`에 기록되지 않은 chat-only approval을 완료로 보지 않습니다.
