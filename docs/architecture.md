# Architecture

## 한 줄 정의
ForgeFlow artifact-first delivery harness.

이 repo는 AI 에이전트의 감정과 세계관을 관리하는 곳이 아니다.
작업을 **stage**, **artifact**, **gate**, **review**로 묶어 실패를 줄이는 쪽에 집중한다.

---

## 1. Design lineage
- **engineering-discipline**: workflow skeleton, complexity routing, worker/validator 분리
- **hoyeon**: artifact contract, schema discipline, monotonic ledger, bounded recovery
- **gstack**: canonical policy, runtime adapter generation, inspectable local memory, eval persistence
- **superpowers**: adversarial review, spec-review → quality-review ordering, anti-rationalization

---

## 2. System thesis
이 harness의 핵심 명제는 세 가지다.

1. **chat는 state가 아니다**
   - state는 artifact와 ledger에 남겨야 한다.
2. **구현과 판정은 분리해야 한다**
   - worker가 자기 자신을 승인하면 검증이 아니라 기분표현이 된다.
3. **runtime 차이는 surface 문제다**
   - workflow semantics는 canonical policy에서만 정의한다.

---

## 3. Primary components

### A. Stage machine
책임:
- 현재 작업이 어느 단계에 있는지 추적
- complexity route 적용
- required artifact가 없으면 진입 차단

코어 stage:
- clarify
- plan
- execute
- spec-review
- quality-review
- finalize
- long-run

### B. Artifact registry
책임:
- 각 stage의 입력/출력 계약 유지
- schema validation 기준 제공
- resume/review를 위한 handoff 단위 제공

### C. Ledger / run-state
책임:
- 현재 stage와 approval flag 유지
- small route에서는 gate/retry/evidence ref 기록
- medium/large route에서는 `plan-ledger`가 stage 완료/gate/retry/current-task truth를 담당
- `advance --execute`는 실행 성공 후에만 다음 stage pointer를 확정
- `step-back`은 되감는 stage에 연결된 review approval/evidence만 제거하고 보존 대상은 남김
- append-only decision 흔적 유지
- finalize 전 상태 판정 근거 제공

### D. Review engine
책임:
- spec correctness와 quality를 분리 판정
- worker 자기보고 대신 artifact/evidence 기준 판단
- anti-rationalization rule 적용

### E. Adapter generator
책임:
- canonical policy를 host-specific 산출물로 변환
- Claude/Codex 차이를 surface에서만 흡수

### F. Eval + memory layer
책임:
- workflow adherence 평가
- 반복 가치가 있는 패턴만 local memory로 남김
- hidden memory가 아니라 inspectable storage 유지

---

## 4. Control plane vs data plane

### Control plane
- `policy/canonical/`
- `schemas/`
- `prompts/canonical/`
- `runtime/`
- `memory/`

여기가 의미론과 scaffold surface를 결정한다.

### Data plane
- task별 artifact
- run-state
- decision-log
- review-report
- eval-record
- `memory/patterns/`, `memory/decisions/`에 남는 inspectable long-run learnings

여기는 실행 흔적과 판정 결과가 쌓이는 영역이다.

### Adapter plane
- `adapters/targets/`
- `adapters/generated/`

여기는 host 차이를 처리한다.

---

## 5. Hard invariants
1. artifact 없이 stage 전환 금지
2. spec-review 실패 시 quality-review 금지
3. review 결과 없는 finalize 금지
4. adapter가 stage/gate/review semantics 변경 금지
5. retry는 bounded budget 안에서만 허용
6. unresolved blocker를 success처럼 포장 금지

---

## 6. P0 scope boundary
P0에서 반드시 들어가는 것:
- workflow, stages, gates, routing
- 6 core artifact schemas
- canonical role prompts
- adapter manifest schema
- claude/codex target placeholders
- eval/readme와 examples

P0에서 일부러 안 넣는 것:
- plugin marketplace
- persona zoo
- giant command taxonomy
- autonomous auto-apply loop
- cross-project magical memory

P0에 들어가는 self-evolution의 정본은 `policy/canonical/evolution.yaml`이다. 의미는 **전역 메타데이터 학습 + 프로젝트 로컬 채택/차단**이다. 전역은 `/forgeflow:clarify`와 `/forgeflow:plan`에 참고 신호를 줄 수 있지만 기본 차단 권한은 없다. raw evidence는 프로젝트 로컬에 남기고, HARD `exit 2`는 프로젝트가 채택한 규칙만 수행한다.

`examples/evolution/`은 이 경계를 깨지 않는 deterministic HARD rule 샘플만 담는다. 예시는 `scope=project`, `lifecycle=adopted_hard`, `enforcement.mode=hard_exit_2`, `global_export.allowed=false`, 그리고 모든 `hard_gate_requires` 증거를 갖춰야 하며 `scripts/validate_policy.py`가 이를 검증한다.

첫 runtime surface는 `scripts/forgeflow_evolution.py inspect`다. 이 명령은 policy와 examples를 읽어서 `global advisory only`, `project HARD examples valid`, `runtime enforcement: not enabled`를 보고할 뿐 rule command를 실행하지 않는다. 자가진화는 읽기 전용 관측면부터 시작하고, 차단기는 프로젝트 채택 이후에만 붙인다.

두 번째 surface는 `scripts/forgeflow_evolution.py dry-run --rule <id>`다. 이것도 아직 command를 실행하지 않는다. rule id, check command, HARD mode, safety checks를 보여주고 `would_execute=false`를 고정한다. 즉 “실행 가능성 검토”와 “실제 실행” 사이에 일부러 벽을 세운다.

세 번째 surface는 gated `scripts/forgeflow_evolution.py execute --rule <id> --i-understand-project-local-hard-rule`다. 이 명시 플래그 없이는 exit 2로 실패한다. 실행 전에도 project scope, adopted HARD, deterministic, global export disabled, raw evidence absent 같은 safety checks가 통과해야 한다. 이 단계도 전역 rule 실행이나 cross-project 차단은 허용하지 않는다.

실행 대상은 `.forgeflow/evolution/rules/*.json`의 project-local registry로 제한한다. `examples/evolution/`은 샘플이며 `list --include-examples`와 `dry-run`에서는 볼 수 있지만, `execute`는 예시 파일을 직접 실행하지 않는다. 샘플을 실제 규칙으로 쓰려면 프로젝트가 명시적으로 `.forgeflow/evolution/rules/`에 복사/채택해야 한다.

채택 surface는 `scripts/forgeflow_evolution.py adopt --example <id>`다. 이 명령은 example rule의 safety checks를 다시 확인하고, 기존 project-local rule이 있으면 덮어쓰지 않는다. adopt 이후에야 `list`에서 `source=project`로 보이고, gated execute 대상이 된다.

---

## 7. What success looks like
설계 완료 기준은 문장이 예쁜 게 아니다.
다음 질문에 답할 수 있어야 한다.

- 지금 task는 어느 stage인가?
- 다음 stage로 넘어갈 artifact가 있는가?
- 누가 구현했고 누가 판정하는가?
- review는 무엇을 근거로 pass/fail 했는가?
- 이 semantics가 Claude/Codex에서 동일하게 유지되는가?
- 실패했을 때 어디서 resume할 수 있는가?
