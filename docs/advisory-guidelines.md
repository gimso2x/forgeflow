# ForgeFlow Advisory Guidelines

## Coding Agent Behavior Guardrails

These guardrails are advisory but should be considered during clarify, plan, execute, and review. They adapt common LLM coding failure modes into ForgeFlow's artifact-first workflow.

### 1. Think Before Coding

- Surface assumptions before implementation.
- If multiple interpretations exist, record the selected interpretation in `brief.md` or `decision-log.md`.
- If ambiguity changes files, data, security, or user-visible behavior, ask or block instead of guessing.

### 2. Simplicity First

- Prefer the minimum implementation that satisfies acceptance criteria.
- Do not add speculative abstraction, configurability, dependencies, or future-proofing.
- If an implementation grows materially larger than expected, simplify before marking the task done.

### 3. Surgical Changes

- Every changed line should trace to the approved brief or plan.
- Do not refactor adjacent code unless the plan names it.
- Remove only unused code introduced by the current change.

### 4. Goal-Driven Execution

- Convert vague tasks into verifiable acceptance criteria.
- Each plan task needs a verification check.
- Bugs should have reproduction evidence before fix when practical.


> **Last updated**: 2026-05-21 | **Status**: advisory only — does not hard-block execution.

ForgeFlow stays markdown-only and no-runtime. These guidelines are advisory checklists for `clarify`, `plan`, and `review`; they do not hard-block execution.

## Route Budget Guide

```yaml
budget:
  small: "Single localized change, usually 1-2 files, low rollback risk."
    # score < 10
  medium: "Coordinated work across a few file groups; plan required."
    # score 10–24.9
  high: "Multi-component or risky work; separate spec and quality review."
    # score 25–49.9
  epic: "Milestone-scale work; plan with epic decomposition, roadmap and milestone review required."
    # score ≥ 50
```

### Score Ranges

| Route | Score Range |
|-------|------------|
| small | < 10 |
| medium | 10 – 24.9 |
| high | 25 – 49.9 |
| epic | ≥ 50 |

### Medium Sub-bands

`mid_threshold = 17.0`

- **medium-light**: score 10.0 – 16.9 → lighter coordination, plan may omit full step-by-step if scope is straightforward.
- **medium-full**: score 17.0 – 24.9 → full plan with step-by-step breakdown required.

### WHERE Calibration

Ambition and situational context (e.g. hotfix urgency, learning-mode exploration) may shift the effective route up or down one band. Record the calibration reason in the `Budget Note` inside `brief.md`. For full calibration criteria, see `skills/clarify/SKILL.md`.

## How to use

- `clarify`: record a `Budget Note` in `brief.md` when scope or risk is non-trivial.
- `plan`: align the `Execution Pattern` with the selected route.
- `review`: treat budget overruns as findings only when they changed risk, scope, or evidence quality.
- Operators may override the guide with explicit task constraints, but must record the reason in artifacts.

## Scope Boundary Alerts

review 단계에서 scope_boundary 위반 탐지 시 advisory를 발행합니다.

- **scope creep 의심**: `files_out_of_scope > 0` → major finding (category: spec-compliance), 위반 파일 목록 포함
- **route 임계값 초과**: 총 수정 파일수가 route threshold 초과 → advisory "scope split 권장 — route 임계값 초과"
- **boundary 정상**: 위반 없음 → `scope_boundary.violations` 빈 배열로 기록, advisory 없음

review는 `brief.md` YAML frontmatter의 `scope_boundary` (files_planned, files_limit, boundary_status)와 실제 수정 파일을 비교합니다. 자세한 절차는 `skills/review/SKILL.md` Scope Boundary Verification 섹션을 참조.

## Non-goals

- No token counter, quota runtime, or subprocess manager.
- No automatic skill injection engine.
- No vendor-specific configuration generator.
