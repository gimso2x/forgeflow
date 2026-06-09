---
schema: ledger/v1
task_id: <!-- TASK_ID -->
route: <!-- small|medium|high|epic -->
total_items: <!-- N -->
required_fields:
  - name: task_id
    description: "Unique task identifier"
  - name: route
    description: "small|medium|high|epic"
  - name: total_items
    description: "Total number of plan items"
  - name: plan_items
    description: "Item list with type, scope, dependencies, estimate"
  - name: execution_tracking
    description: "Per-item status, evidence, retry count"
optional_fields:
  - name: gate_results
    description: "Verification gate outcomes"
  - name: decisions
    description: "Execution decisions"
---

# Ledger

<!-- ForgeFlow unified tracking. Plan stage writes Plan Items; Execute stage updates Execution Tracking. -->
<!-- Replaces plan-ledger.md and run-ledger.md (both deprecated as of v1.11). -->
<!-- Status truth lives here; implementation-notes.md holds decision narrative — read ledger first on resume. -->
<!-- Loop item status enum: pending | in_progress | blocked | done | discarded. Do not invent alternate status words. -->
<!-- Resume rule: checkpoint.md points to exactly one ledger task; ledger owns item status, retry count, blocker, and evidence refs. -->

## Loop Status Contract

- **Allowed Status Values**: `pending`, `in_progress`, `blocked`, `done`, `discarded`
- **pending**: item is queued and has not been claimed.
- **in_progress**: item is currently claimed by the assignee named in `Claim Marker`.
- **blocked**: item cannot proceed without a recorded blocker or user decision.
- **done**: item has verification evidence and needs no more execute work.
- **discarded**: item was deliberately removed from the loop scope; record the decision in `## Decisions`.
- **Resume Pointer Rule**: `checkpoint.md` `## Resume Pointer` must name the next ledger task before context compression or handoff.
- **Evidence Rule**: every `done` item must cite at least one `Evidence Refs` entry from `implementation-notes.md` `## Evidence Index` or a concrete artifact path.

## Plan Items

### [ ] <!-- item title -->
- **Type**: <!-- feature|fix|refactor|docs -->
- **Scope**: <!-- file list -->
- **Dependencies**: <!-- item refs or none -->
- **Estimate**: <!-- small|medium|large -->

## Execution Tracking

### Task 1: <!-- name -->
- **Plan Step**: <!-- which plan step or brief objective -->
- **Status**: <!-- pending | in_progress | blocked | done | discarded -->
- **Assignee**: <!-- worker | specialist | spec-reviewer | quality-reviewer -->
- **Claim Marker**: <!-- role=<worker|specialist|spec-reviewer|quality-reviewer> scope=<repo paths or artifact section> at=<ISO8601>; none for direct sequential worker -->
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
- **Discarded**: 0
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
- **Discarded**: 0
- **All Done**: no
```
