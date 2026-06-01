---
schema: ledger/v1
task_id: <!-- TASK_ID -->
route: <!-- small|medium|high|epic -->
total_items: <!-- N -->
---

# Ledger

<!-- ForgeFlow unified tracking. Plan stage writes Plan Items; Execute stage updates Execution Tracking. -->
<!-- Replaces plan-ledger.md and run-ledger.md (both deprecated as of v1.11). -->
<!-- Status truth lives here; implementation-notes.md holds decision narrative — read ledger first on resume. -->

## Plan Items

### [ ] <!-- item title -->
- **Type**: <!-- feature|fix|refactor|docs -->
- **Scope**: <!-- file list -->
- **Dependencies**: <!-- item refs or none -->
- **Estimate**: <!-- small|medium|large -->

## Execution Tracking

### Task 1: <!-- name -->
- **Plan Step**: <!-- which plan step or brief objective -->
- **Status**: <!-- pending | running | done | blocked | skipped -->
- **Assignee**: <!-- worker | specialist | spec-reviewer | quality-reviewer -->
- **Claim Marker**: <!-- role=<assignee> scope=<files/section> at=<ISO8601>; none for direct sequential worker -->
- **Evidence Refs**: <!-- compact strings: verification:PASS gate=... | contract_check:PASS | evidence_index:task=... -->
- **Blocker**: <!-- description or "none" -->
- **Retry Count**: <!-- 0 -->

### Task 2: <!-- name -->
- **Plan Step**:
- **Status**: pending
- **Assignee**:
- **Claim Marker**: none
- **Evidence Refs**:
- **Blocker**: none
- **Retry Count**: 0

## Decisions

- <!-- decision -->: <!-- rationale -->

## Assignee discipline

<!-- worker = controller or direct implementation; specialist = delegated subagent -->
<!-- spec-reviewer / quality-reviewer = execute-stage micro-review only (high/epic) -->
<!-- Claim markers are markdown state, not chat-only claims. Record them before any delegated or parallel pass touches files/sections. -->
<!-- Claim markers are atomic at the artifact level: write the marker, re-read this task row, and proceed only if the row still names the same role/scope/timestamp. -->

## Gate Results

| Gate | Target | Result | Evidence |
|------|--------|--------|----------|
| <!-- gate name --> | <!-- what was checked --> | <!-- pass | fail | skipped --> | <!-- ref --> |

## Completion Summary

- **Total Tasks**: 0
- **Completed**: 0
- **Blocked**: 0
- **Skipped**: 0
- **All Done**: <!-- yes | no -->

## Small Route Minimal Format

small route에서는 plan.md가 없으므로, brief.md를 기반으로 최소 ledger를 생성한다:

```markdown
---
schema: ledger/v1
task_id: <!-- TASK_ID -->
route: small
total_items: 1
---

# Ledger

## Plan Items

### [ ] <brief.md objective에서 추출>
- **Type**: <!-- feature|fix|refactor|docs -->
- **Scope**: <!-- file list -->
- **Dependencies**: none
- **Estimate**: small

## Execution Tracking

### Task 1: <brief.md objective에서 추출>
- **Plan Step**: Task 1
- **Status**: pending
- **Assignee**: worker
- **Claim Marker**: none
- **Evidence Refs**:
- **Blocker**: none
- **Retry Count**: 0

## Decisions

## Assignee discipline

worker = direct implementation (small route는 specialist 사용 안 함)

## Gate Results

| Gate | Target | Result | Evidence |
|------|--------|--------|----------|

## Completion Summary

- **Total Tasks**: 1
- **Completed**: 0
- **Blocked**: 0
- **Skipped**: 0
- **All Done**: no
```
