# ForgeFlow 다이어트 계획안

## 현황
- **런타임**: 89개 Python 파일, 14,986줄
- **테스트**: 131개 파일
- **어댑터**: 44개 파일
- **evolution**: 13개 파일, 1,801줄
- **orchestra**: 5개 파일, 779줄
- **experiment**: 7개 파일, 594줄
- **루트레벨 레거시 facade**: 11개 파일 (각 6줄 re-export)

## 문제 진단

1. **orchestrator.py 2,516줄** — God Object. 전체 런타임의 17%가 한 파일
2. **orchestra/** — executor.py에서 1곳만 참조. 실사용 의문
3. **experiment/** — 외부 참조 0개. 완전 고립
4. **evolution 프로모션 파이프라인** — propose→review→approve→gate→decide→promote 6단계. 실제 돌아가는지 의문
5. **루트레벨 facade 11개** — `evolution_*.py` re-export만 하는 6줄짜리 파일들
6. **harness_profiles.py 568줄, worktree.py 441줄** — 프로필 시스템이 실사용되는지 확인 필요

## 원칙

- **삭제보다 분리**: 죽은 코드는 과감히 자르되, 분리 가능한 건 `experimental/`로
- **코어는 5개 모듈만**: orchestrator, engine, executor, generator, gate_evaluation
- **evolution은 심플하게**: adopt/retire/execute/audit만 남기고 프로모션 파이프라인 축소

## Phase 1: 죽은 코드 정리 (1회 커밋)

### 삭제 — 루트 레거시 facade
```
forgeflow_runtime/evolution_audit.py      (6줄, re-export)
forgeflow_runtime/evolution_cases.py      (6줄, re-export)
forgeflow_runtime/evolution_doctor.py     (6줄, re-export)
forgeflow_runtime/evolution_execution.py  (6줄, re-export)
forgeflow_runtime/evolution_lifecycle.py  (6줄, re-export)
forgeflow_runtime/evolution_observations.py (6줄, re-export)
forgeflow_runtime/evotion_promotion_gates.py (6줄, re-export)
forgeflow_runtime/evolution_promotion_plans.py (6줄, re-export)
forgeflow_runtime/evolution_promotions.py (6줄, re-export)
forgeflow_runtime/evolution_proposals.py  (6줄, re-export)
forgeflow_runtime/evolution_rules.py      (6줄, re-export)
```
→ 총 11개 파일, 66줄 삭제. `from forgeflow_runtime.evolution_X` 쓰는 곳 `from forgeflow_runtime.evolution.X`로 마이그레이션.

### 분리 → `experimental/`
```
forgeflow_runtime/orchestra/     → experimental/orchestra/    (779줄)
forgeflow_runtime/experiment/    → experimental/experiment/   (594줄)
```
executor.py의 orchestra import는 try/except로 lazy load. 실패해도 코어 동작.

### 삭제 후보 (사용 빈도 확인 필요)
```
forgeflow_runtime/harness_profiles.py  (568줄) — 프로필 시스템
forgeflow_runtime/worktree.py          (441줄) — 워크트리 관리
forgeflow_runtime/anti_rationalization.py (160줄)
forgeflow_runtime/adversarial_review.py   (133줄)
forgeflow_runtime/ears_parser.py          (126줄)
```
→ grep으로 실제 사용처 확인 후 판단.

**Phase 1 예상 효과**: 1,373줄 레거시 삭제 + 1,373줄 experimental 분리 = 코어 12,600줄로 축소 (16% 감소)

## Phase 2: orchestrator 분해 (2-3회 커밋)

현재 2,516줄 → 400줄 이하로.

```
orchestrator.py 분해:
  ├── orchestrator.py         (코어: 런타임 상태, 스테이지 전환) ~300줄
  ├── gate_runner.py          (게이트 평가 + 재시도) ~200줄
  ├── route_selector.py       (auto_route, operator_routing 통합) ~200줄
  ├── recovery.py             (stuck_detector, stale_recovery 통합) ~200줄
  └── runtime_policy.py       (policy_loader, enforcement_config 통합) ~200줄
```

의존도 24개인 orchestrator를 4-5개 모듈로 쪼개면 개별 테스트/수정이 훨씬 쉬워짐.

## Phase 3: evolution 경량화 (1회 커밋)

```
현재 (13개 파일, 1,801줄):
  paths.py, rules.py, audit.py, lifecycle.py, execution.py, observations.py,
  doctor.py, proposals.py, promotion_gates.py,
  promotions.py, cases.py, __init__.py

목표 (7개 파일, ~900줄):
  paths.py          (52줄) — 유지
  rules.py          (167줄) — 유지
  audit.py          (86줄) — 유지
  lifecycle.py      (184줄) — adopt/retire/restore만 남기고 프로모션 코드 제거
  execution.py      (159줄) — 유지
  observations.py   (133줄) — 유지
  __init__.py       (60줄) — facade 축소

삭제/흡수:
  promotion_gates.py  (206줄) → lifecycle.py에 간단 promote 1함수로 흡수
  promotion_plans.py  (완료: audit.py로 흡수 후 삭제)
  proposals.py        (175줄) → 간단 proposal만 남기거나 삭제
  promotions.py       (145줄) → lifecycle.py promote 함수로 대체
  doctor.py           (178줄) → 독립 유지하되 크기 확인
  cases.py            (93줄) → audit.py에 흡수
```

**핵심 아이디어**: propose→review→approve→gate→decide→promote 6단계 파이프라인을
`propose(id, content)` + `promote(id, ack)` 2단계로 축소.

## Phase 4: 어댑터 정리

```
adapters/targets/
  claude/  (22파일) — 실제 플러그인 매니페스트 + 에이전트만 유지
  codex/   (22파일) — 동일
```

중복 템플릿/설정 파일 정리. 코어 변경사항만 어댑터에 반영.

## 예상 결과

| | 현재 | Phase 1 후 | Phase 3 후 |
|---|---|---|---|
| 런타임 파일 | 89 | ~75 | ~68 |
| 런타임 줄수 | 14,986 | ~12,600 | ~11,700 |
| evolution 파일 | 13 | 13 | ~8 |
| orchestra/experiment | 12 | 0 (experimental) | 0 |
| 테스트 | 131 | ~115 | ~95 |

## 우선순위

1. **Phase 1** — 리스크 낮고 즉시 효과. 레거시 facade + experiment/orchestra 분리
2. **Phase 3** — evolution 경량화. 방금 작업한 거니 컨텍스트가 살아있음
3. **Phase 2** — orchestrator 분해. 가장 큰 효과지만 가장 리스크 높음
4. **Phase 4** — 어댑터는 나중에

## 주의사항

- 각 Phase는 **별도 브랜치 + PR**로 진행
- 실험적 분리는 `try/except ImportError`로 안전 장치
- 테스트는 매 Phase마다 전체 통과 확인
- 한 번에 하나의 Phase만 진행
