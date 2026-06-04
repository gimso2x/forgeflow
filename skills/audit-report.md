# ForgeFlow Skills Audit Report

Date: 2026-06-04
Release: v1.12.0
Auditor: skill-creator (deep audit)

## Summary

9 skills audited. Deep audit found **1 critical**, **4 moderate** issues. Applied fixes.

### Applied Fixes (this audit)

| Fix | Status |
|-----|--------|
| forgeflow Schema B 통일 — `intent`/`inputs`/`outputs` 제거 | ✅ Done |
| benchmark validate_prompt 보강 (3→6줄) | ✅ Done |
| long-run validate_prompt 보강 (4→7줄) | ✅ Done |
| long-run description 한국어 트리거 추가 | ✅ Done |
| ff-review 본문 → references/ 분리 (standalone-mode.md, human-judgment.md) | ✅ Done |
| ff-review 858→727라인 (131줄 절감) | ✅ Done |

### Already Resolved (prior to this audit)

| Fix | Status |
|-----|--------|
| clarify Schema B 마이그레이션 + validate_prompt 추가 | ✅ Done |
| forgeflow validate_prompt 추가 | ✅ Done |
| ff-plan validate_prompt 보강 (contract traceability, refactor mode, epic roadmap) | ✅ Done |
| ff-review validate_prompt 보강 (role separation, evidence discipline, completeness gate, plan conformance) | ✅ Done |
| 전체 스킬 version 필드 존재 | ✅ Confirmed |
| benchmark 고아 JSON 블록 | ✅ Not found (already clean) |

## 1. Version Consistency

| Skill | Version |
|-------|---------|
| forgeflow | 1.12.0 |
| clarify | 0.6.0 |
| execute | 0.7.0 |
| ff-plan | 0.6.0 |
| ff-review | 0.6.0 |
| ship | 0.4.0 |
| long-run | 0.5.0 |
| benchmark | 0.3.0 |
| ff-config | 0.6.0 |

**Verdict**: All skills have version fields. Skill schema versions are independent from release VERSION. `forgeflow` uses release version (1.12.0); others use skill-level versioning (0.x).

## 2. Frontmatter Schema — ✅ Resolved

All 9 skills now use Schema B:

```yaml
name: ...
description: ...
version: ...
author: ...
validate_prompt: |
  ...
dependencies:
  - ...
```

`forgeflow` was the last holdout with `intent`/`inputs`/`outputs` — removed this audit.

## 3. Dependencies Inconsistency — 🟡 Moderate (advisory)

Dependencies field is advisory (no runtime enforcement). Declarations are mostly complete for skills that declare them. Some gaps remain:

| Skill | Declared | Gap |
|-------|----------|-----|
| ff-review | 5 declared | Matches actual usage |
| execute | 4 declared | Matches actual usage |
| ship | 5 declared | Matches actual usage |

No critical gaps. Skills reference `_shared/` files inline via `→ _shared/xxx.md` pointers as fallback.

## 4. validate_prompt Coverage — ✅ Resolved

All 9 skills have validate_prompt. Key coverage:

- **forgeflow**: 9 lines — routing, defaults, template resolution, stage boundaries
- **clarify**: 6 lines — brief.md, workspace bootstrapping, WHERE grounding, verification gates
- **ff-plan**: 6 lines — artifact-first, contracts, traceability, refactor mode, epic roadmap
- **execute**: 5 lines — scoped tasks, contracts, review requirement, subagent dispatch
- **ff-review**: 10 lines — role separation, blockers, evidence discipline, completeness gate, plan conformance
- **ship**: 7 lines — review confirmation, diff scope, verification, safe outcomes, destructive action guard
- **benchmark**: 6 lines — multi-adapter, CLI resolution, compliance scoring, DNF handling
- **long-run**: 7 lines — evidence-backed rules, SOFT→HARD promotion, scope distinction
- **ff-config**: 3 lines — defaults.md, init, prune

## 5. Description Trigger Quality — ✅ Mostly Resolved

### Strong descriptions (Korean + English triggers):
- **clarify**: "어떻게 접근, 모르겠어, 정리해줘" ✅
- **execute**: "구현 시작, 실행해줘" ✅
- **ship**: "마무리, wrap up, finalize" ✅
- **ff-config**: "forgeflow 설정, 워크트리 정리" ✅
- **forgeflow**: "구현, 리팩토링, 체계적, 단계별, 검증" ✅

### Adequate descriptions:
- **ff-plan**: "plan 만들어, tasks 나눠, 분해" ✅
- **ff-review**: "review 해줘, code review" ✅
- **benchmark**: "adapter 벤치마크, compare adapters" ✅
- **long-run**: "배운 점 정리, 패턴 추출, 회고" ✅ (added this audit)

## 6. Line Count Health

| Skill | Lines | Status |
|-------|-------|--------|
| ff-review | 727 | 🟡 Above 500 target, improved from 858 |
| execute | 639 | 🟡 Above 500, but dense with necessary detail |
| ship | 538 | 🟡 Above 500, but dense with necessary detail |
| ff-plan | 468 | 🟢 OK |
| clarify | 444 | 🟢 OK |
| forgeflow | 420 | 🟢 OK |
| benchmark | 333 | 🟢 OK |
| ff-config | 184 | 🟢 OK |
| long-run | 172 | 🟢 OK |

**ff-review note**: Standalone mode and Human Final Judgment Gate extracted to `references/` (131 lines). Further extraction (Role definitions, Review Rubrics) possible but would increase cross-file coupling.

## 7. Remaining Recommendations

| Priority | Item | Effort |
|----------|------|--------|
| P3 | ff-review further extraction if context budget is tight | Medium |
| P3 | Dependencies audit — verify all _shared refs match declarations | Low |
| P4 | Consider version normalization (0.x → 1.x for stable skills) | Low |
