---
name: ff-loop
description: Full lifecycle loop — one command to run clarify through ship with automatic retry, re-execution, route promotion, and re-plan. Use as /forgeflow:ff-loop or /ff-loop. Also use when the user says 'loop로 해', '한 번에 끝까지', '루프로 돌려', 'loop it', 'run the loop'.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must run the full ForgeFlow lifecycle in one invocation.
  Must retry failed tasks up to route budget before promoting.
  Must record every retry and route change in artifacts.
  Must stop only on irrecoverable blockers or destructive actions.
  Must not ask (y/n) between stages.
dependencies:
  - skills/forgeflow/SKILL.md
  - skills/_shared/automation.md
  - skills/_shared/discipline.md
  - skills/_shared/context-resume.md
  - docs/local-loop-runtime-contract.md
---

# ff-loop

한 번에 끝까지. `/forgeflow:ff-loop "작업 설명"`을 치면 clarify → plan → execute → review → ship까지 알아서 돕습니다. 실패하면 재시도, 범위가 모자라면 route 승격, 리뷰에서 반려되면 수정 후 재실행.

## 언제 쓰나

- `--auto`는 stage를 자동으로 넘어가지만, 실패/반려 시 멈춥니다
- `ff-loop`는 실패/반려 시에도 **재시도하고 계속 진행**합니다
- 간단한 수정부터 복잡한 기능까지 한 번에 끝내고 싶을 때

## 사용법

```text
/forgeflow:ff-loop 로그인 페이지에 소셜 로그인 버튼 추가
/forgeflow:ff-loop auth 모듈 리팩토링
/forgeflow:ff-loop 버그: 로그아웃 시 세션이 안 지워짐
```

Cursor에서는:

```text
/ff-loop 로그인 페이지에 소셜 로그인 버튼 추가
```

## 하는 일

```text
clarify (brief.md 작성, route 자동 선택)
  │
  ▼
plan (medium+, plan.md 작성)
  │
  ▼
execute ─── 실패? ─── classify failure ─── retry/replan/escalate/human/stop
  │                                        │
  │                                        └── stagnation? ──── 자동 전략 전환
  │
  ▼
review ─── 반려? ─── classify failure ─── 수정 후 재실행 ─── 다시 review
  │                                        │
  │ scope 초과? ─── re-plan 후 다시 execute │ converging? ─── 계속
  │                                        │ diverging? ─── replan/escalate
  ▼ (approved)
ship
  │
  ▼
done (high/epic은 long-run까지)
```

## Failure Classification Taxonomy

참조: Ouroboros `resilience/failure_taxonomy.py`의 6-way 분류를 ForgeFlow 루프에 맞게 5-way로 단순화.

모든 실패/반려는 먼저 **분류**한 뒤 분류에 맞는 복구 전략을 실행합니다:

| 분류 | 의미 | 복구 전략 | 예산 소모 |
|---|---|---|---|
| `retry` | 일시적 실패 (lint/test, env, 네트워크) | 동일 조건 재시도 | O |
| `replan` | scope/설계 문제 (plan이 현실과 불일치) | plan 단계로 복귀, 재계획 | O |
| `escalate` | route가 현재 작업에 부족함 | 상위 route 승격 후 계속 | O |
| `human` | 인간 결정 필요 (ambiguous requirement, credential) | 멈추고 질문 | X |
| `irrecoverable` | 복구 불가 (외부 서비스 장애, billing) | 루프 종료 | X |

### 분류 규칙

1. **lint/test/env 실패** → `retry` (최대 route budget)
2. **review 반려 + blocker가 설계 관련** → `replan`
3. **review 반려 + blocker가 scope 관련** → `escalate`
4. **credential/billing/외부 장애** → `irrecoverable`
5. **ambiguous requirement, 여러 해석 가능** → `human`
6. **분류 불확실 시** → `human` (안전 우선)

### 분류 기록

매 실패 시 `implementation-notes.md`에:
```
FAIL classify=<type> reason=<1-line> action=<recovery strategy>
```

## Stagnation Pattern Detection

참조: Ouroboros `resilience/stagnation.py`의 4-pattern 감지를 ff-loop에 적용.

단순히 예산까지 재시도하는 대신, **정체 패턴**을 감지하면 조기에 전략을 바꿉니다:

| 패턴 | 감지 조건 | 조치 |
|---|---|---|
| **Spinning** | 동일한 finding이 3회 연속 재시도에 unchanged | `replan` |
| **Oscillation** | 두 실패 상태를 번갈아 반복 (A→B→A→B) | `escalate` |
| **Diminishing returns** | new findings는 감소하지만 0에 도달 못함 (3회+) | `human` |
| **No-progress** | retry count 증가하지만 blocker 해결 없음 (3회+) | `replan` 또는 `escalate` |

### 감지 방법

1. 매 retry 후 `review-report.md` Open Blockers를 이전 시도와 비교
2. blocker 목록이 동일하면 spinning 카운터 증가
3. blocker가 A→B→A→B 패턴이면 oscillation 플래그
4. blocker가 감소 추세이면 converging, 증가 추세이면 diverging
5. checkpoint.md에 `stagnation: <pattern or none>` 기록

## Convergence Tracking

참조: Ouroboros `evolution/convergence.py`의 수렴/발산 감지를 ff-loop에 적용.

재시도가 수렴하고 있는지 발산하고 있는지 추적합니다:

### 추적 지표 (매 retry 후)

| 지표 | 측정 방법 | 수렴 신호 | 발산 신호 |
|---|---|---|---|
| `open_blockers` | review-report.md Open Blockers 수 | 감소 추세 | 증가 추세 |
| `new_findings` | 이전 retry에 없던 새 finding 수 | 0에 수렴 | 증가 |
| `evidence_completeness` | ship-summary Evidence 항목 완료율 | 100%에 수렴 | 정체 |

### 판정 규칙

- **Converging**: 2회 연속 open_blockers 감소 + new_findings 0
- **Diverging**: 2회 연속 new_findings 증가 또는 open_blockers 동일/증가
- **Converging 시**: 현재 전략 유지, 계속 재시도
- **Diverging 시**: 자동으로 `replan` 또는 `escalate` 전환
- **Stagnation 감지 시**: convergence tracking 정지, stagnation 규칙 우선

### 기록

checkpoint.md에 매 retry 후:
```
convergence: converging|diverging|stagnant
open_blockers: <N> (trend: ↓|↑|→)
new_findings: <N>
evidence_completeness: <%>
```

## 재시도 예산

| Route | 태스크별 최대 재시도 | 전체 루프 최대 횟수 |
|---|---|---|
| small | 1 | 2 |
| medium | 2 | 4 |
| high | 2 | 5 |
| epic | 3 (milestone별) | 6 |

재시도는 **조건이 바뀐 경우에만** 카운트합니다. 코드 수정, plan 수정, 새 증거, blocker 해결, scope 변경 없이 그대로 다시 돌리는 건 노이즈 — 예산에 포함하지 않습니다.

## Route 승격

재시도 예산을 소진해도 여전히 실패하면:

1. `implementation-notes.md`에 기록:
   ```
   D-<!-- N --> route_change from=small to=medium reason=verify 실패 2회, scope 확대 필요
   ```
2. `ledger.md` frontmatter `route:` 업데이트
3. 승격된 route의 검증 기준으로 계속 진행

승격 경로: `small → medium → high`. high가 한계.

## 멈추는 조건

다음 경우에만 멈추고 사용자에게 묻습니다:

- **복구 불가 blocker**: credential, billing, 외부 서비스 장애, 사용자 결정 필요
- **이미 high/epic인데 재시도 소진**: 더 이상 승격 불가
- **파괴적 작업**: discard, force-push — 항상 인간 승인
- **동일 조건으로 3회 연속 실패**: 근본적인 문제가 있다는 신호

## Artifact 규칙

루프 중에는 artifact가 상태 머신입니다. 반드시:

1. 매 시도 후 `ledger.md` 태스크 상태 업데이트 (`pending → in_progress → done/blocked`)
2. 매 시도 후 `checkpoint.md` 업데이트 (현재 retry count, route)
3. `implementation-notes.md` Evidence에 retry 기록
4. route 변경은 Decisions에 기록
5. 조용히 재시도 금지 — 매 retry마다 무엇이 바뀌었는지 기록

## Procedure

1. 사용자 요청을 읽습니다
2. `checkpoint.md`가 있으면 → 재개 모드 (아래 참고)
3. `checkpoint.md`가 없으면 → **clarify**부터 시작
4. 각 stage를 `--auto` 규칙에 따라 자동 진행 (`_shared/automation.md` 참고)
5. 실패/반려 시 위의 재시도/승격 규칙 적용
6. ship 완료 또는 irrecoverable blocker까지 계속

### 재개 모드

기존 태스크 디렉토리가 있으면 처음부터 시작하지 않고 이어서 합니다:

1. `checkpoint.md` → `ledger.md` → `implementation-notes.md` Reader Summary 읽기
2. `Status: blocked`이면 blocker 해결 가능한지 판단
3. 해결 가능하면 해결하고 `Next Action`부터 계속
4. 불가능하면 사용자에게 보고

## Exit Condition

- `/forgeflow:ship` 완료 → 루프 성공 종료
- Irrecoverable blocker → 루프 실패 종료, blocker를 `checkpoint.md`에 기록
- Context limit → checkpoint 쓰고 다음 턴에서 자동 재개

## Strict response constraints

→ `_shared/discipline.md`.

루프 중에는 stage 사이에 멈추거나 질문하지 않습니다. 오직 위 멈춤 조건에서만.
