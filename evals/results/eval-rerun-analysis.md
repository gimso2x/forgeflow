# Eval 재실행 분석 (정적 계약 대조)

**Generated:** 2026-05-20  
**Status:** AI 재실행 SKIP — iteration-2 optional  
**Baseline:** iteration-1 (with_skill 12/12)  
**Contract (v1.0.3):** 3/3 eval cases align with skills/templates

---

## 재실행 불가 사유

`evals/evals.json` 3 cases는 ForgeFlow 스킬을 로드한 AI agent가 prompt에 응답하고, assertion을 수동/반자동 채점해야 합니다.

- `forgeflow-eval-workspace/`는 `.gitignore` L21
- `grade_iteration.py`는 로컬 eval workspace에만 존재
- CI 미연동

---

## 정적 계약 대조 (현재 v1.0.2 vs eval assertions)

### Eval 0: active-rule-clarify

**Prompt 요구:** medium clarify, active evolution rule → brief with Applied Evolution Rules, `.forgeflow/tasks/` path

**현재 계약:**

| Source | Align |
|--------|-------|
| `skills/clarify/SKILL.md` | Applied Evolution Rules 섹션, active rule 적용 지시 |
| `templates/brief.md` | task path, evolution rules 필드 |
| `evals/evals.json` assertions L11–14 | 4개 assertion 모두 스킬/템플릿과 일치 |

**iteration-1:** with_skill 4/4, without_skill 3/4 (baseline: concrete task path 누락)

**회귀 위험:** LOW — 계약 변경 없음

---

### Eval 1: propose-rule-long-run

**Prompt 요구:** ship-summary/implementation-notes 미갱신 패턴 → eval-record + proposed evolution-rule

**현재 계약:**

| Source | Align |
|--------|-------|
| `skills/long-run/SKILL.md` L78, L112 | `.forgeflow/evolution/proposed/<rule-name>.md` |
| `templates/evolution-rule.md` | Rule ID, Scope, Lifecycle, Trigger, Expected Behavior, Application Stage, Enforcement Mode, Evidence, False Positive Guard, Rollback/Retirement, Review Status |
| `evals/evals.json` assertions L24–27 | template 필드와 일치 |

**Gap (v1.0.2):** Prompt referenced `ship-summary.md` but template was missing.

**v1.0.3:** `templates/ship-summary.md` added — contract align **OK**, regression risk **LOW**.

---

### Eval 2: review-rule-boundary

**Prompt 요구:** invalid global-advisory + required_project_rule + vague evidence → changes_requested/rejected

**현재 계약:**

| Source | Align |
|--------|-------|
| `skills/review/SKILL.md` | Evolution Rule Review 섹션, scope/enforcement boundary |
| `README.md` L127–128 | global advisory only, no hard block |
| `templates/evolution-rule.md` L11–12, L32–33 | Scope, Enforcement Mode 필드 |

**iteration-1:** with_skill 4/4, without_skill 4/4 (both caught boundary)

**회귀 위험:** LOW

---

## iteration-1 vs 현재 감사 비교

| Metric | iteration-1 | 현재 감사 |
|--------|-------------|-----------|
| with_skill pass rate | 100% (12/12) | 재실행 없음 |
| without_skill pass rate | 75% (9/12) | — |
| Static contract align | — | 3/3 eval cases 스킬/템플릿과 align |
| New gap since iteration-1 | — | ship-summary template gap 명시적 확인 |

---

## 재실행 권장 절차 (후속)

1. `forgeflow-eval-workspace/` bootstrap (skill-creator 패턴)
2. `evals/evals.json` 3 cases × with_skill / without_skill
3. `grade_iteration.py` 또는 assertion 수동 채점
4. 결과를 `evals/results/iteration-2.md`로 기록
5. (선택) CI nightly job — AI API 필요

---

## 결론

정적 대조상 eval assertions는 v1.0.3 스킬/템플릿과 align. ship-summary template gap은 v1.0.3에서 해소됨.
