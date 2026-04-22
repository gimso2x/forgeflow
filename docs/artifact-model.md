# Artifact Model

## 목적
이 harness는 대화 로그가 아니라 artifact를 기준으로 움직인다.
artifact는 stage 간 handoff 계약이며, resume과 review의 최소 단위다.

---

## 공통 원칙
1. 모든 artifact는 `schema_version`을 가진다.
2. 모든 artifact는 `task_id`를 가진다.
3. 사람이 읽는 설명과 기계 판정 필드를 같이 둔다.
4. artifact는 후속 stage의 입력이어야 한다.
5. 없으면 stage를 못 넘긴다.

---

## 1. `brief`
역할:
- clarify 단계의 산출물

담아야 할 것:
- objective
- in_scope
- out_of_scope
- constraints
- acceptance_criteria
- risk_level
- assumptions
- open_questions

없으면 생기는 문제:
- plan이 자기 멋대로 커진다.
- execution이 spec을 추정하게 된다.

---

## 2. `plan`
역할:
- medium 이상 작업의 실행 계약서

담아야 할 것:
- ordered steps
- dependencies
- expected outputs
- verification per step
- rollback or fallback notes

핵심 규칙:
- vague checklist 금지
- 단계별 evidence가 있어야 함

---

## 3. `decision-log`
역할:
- execution 중 나온 중요한 판단의 append-only 기록

담아야 할 것:
- timestamp
- actor
- category
- decision
- rationale
- affected_artifacts

핵심 규칙:
- 이미 끝난 결정을 슬쩍 덮어쓰지 않는다.
- 변경은 새 항목으로 남긴다.

---

## 4. `run-state`
역할:
- 현재 진행 상태와 gate 통과 여부를 추적하는 ledger

담아야 할 것:
- current_stage
- status
- completed_gates
- failed_gates
- retries
- evidence_refs
- spec_review_approved
- quality_review_approved
- final_status

핵심 규칙:
- monotonic progression 우선
- rollback은 기록된 예외로만 허용
- finalize는 spec/quality 승인 플래그 없이 통과할 수 없다

---

## 5. `review-report`
역할:
- spec 또는 quality review의 판정 결과

담아야 할 것:
- review_type
- verdict
- findings
- missing_evidence
- evidence_refs
- approved_by
- next_action

핵심 규칙:
- `review_type`은 spec 또는 quality를 분리하는 기계 판정 필드다
- "looks good" 금지
- 근거 없는 승인 금지

---

## 6. `eval-record`
역할:
- long-run 단계에서 남기는 평가 결과

담아야 할 것:
- outcome
- what_worked
- what_failed
- reusable_rule_candidates
- follow_up_worth

핵심 규칙:
- 단순 작업일지는 eval이 아니다.
- 다음 실행에 도움이 되는 정보만 남긴다.

---

## 선택 artifact
### `handoff-summary`
사람 또는 다음 실행 주체가 빠르게 이어받아야 할 때 사용.

### `memory-note`
반복 가치가 높은 패턴만 저장.

---

## artifact 간 관계
- `brief` 없이 `plan`은 성립하지 않는다.
- `plan` 없이 medium/large execution은 성립하지 않는다.
- `run-state` 없이 finalize는 성립하지 않는다.
- `review-report` 없이 review gate는 통과할 수 없다.
- spec/quality 구분 없는 review는 high-risk finalize 근거가 될 수 없다.
- `eval-record` 없이 long-run capture는 완료가 아니다.
