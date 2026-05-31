# Run Ledger

<!-- ForgeFlow execution truth. plan.md is intent; run-ledger.md is what actually happened. -->
<!-- Updated by execute stage. Read by review, ship stages. -->
<!-- Status truth lives here; implementation-notes.md holds decision narrative — read ledger first on resume. -->

## Route
<!-- small | medium | high | epic -->

## Plan Reference
<!-- Path to the plan.md this ledger tracks -->

## Tasks

### Task 1: <!-- name -->
- **Plan Step**: <!-- which plan step this corresponds to -->
- **Status**: <!-- pending | running | done | blocked | skipped -->
- **Assignee**: <!-- required when status is running/done/blocked/skipped: worker | specialist | spec-reviewer | quality-reviewer -->
- **Claim Marker**: <!-- required before subagent/concurrent work starts: role=<assignee> scope=<files/section> at=<ISO8601>; none for direct sequential worker -->
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

## Assignee discipline

<!-- Updated by execute per skills/execute/SKILL.md -->
<!-- worker = controller or direct implementation; specialist = delegated subagent -->
<!-- spec-reviewer / quality-reviewer = execute-stage micro-review only (high/epic) -->
<!-- Claim markers are markdown state, not chat-only claims. Record them before any delegated or parallel pass touches files/sections. -->
<!-- Claim markers are atomic at the artifact level: write the marker, re-read this task row, and proceed only if the row still names the same role/scope/timestamp. If another claim appears, stop and hand control back to the controller instead of racing or overwriting it. -->
<!-- Claim marker format: role=<worker|specialist|spec-reviewer|quality-reviewer> scope=<repo paths or artifact section> at=<ISO8601> -->

## Gate Results
<!-- Gate evaluations from execute stage; include micro_spec / micro_quality when high/epic -->

| Gate | Target | Result | Evidence |
|------|--------|--------|----------|
| <!-- gate name --> | <!-- what was checked --> | <!-- pass | fail | skipped --> | <!-- ref --> |

## Completion Summary
<!-- Filled when all tasks are done or blocked -->

- **Total Tasks**: 0
- **Completed**: 0
- **Blocked**: 0
- **Skipped**: 0
- **All Done**: <!-- yes | no -->

## Small Route Minimal Format

small route에서는 plan.md가 없으므로, brief.md를 기반으로 최소 run-ledger를 생성한다:

```markdown
# Run Ledger

## Route

small

## Plan Reference

`brief.md` (small route — no plan)

## Tasks

### Task 1: <brief.md objective에서 추출>
- **Plan Step**: Task 1
- **Status**: pending
- **Assignee**: worker
- **Claim Marker**: none
- **Evidence Refs**:
- **Blocker**: none
- **Retry Count**: 0

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
