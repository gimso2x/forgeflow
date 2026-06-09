---
schema: checkpoint/v1
stage: <!-- clarify|plan|execute|review|ship|long-run -->
status: <!-- in_progress|completed|blocked -->
input_mode: <!-- pipeline | standalone -->
required_fields:
  - name: stage
    description: "clarify|plan|execute|review|ship|long-run"
  - name: status
    description: "in_progress|completed|blocked"
  - name: next_action
    description: "Single immediate action to take"
  - name: resume_pointer
    description: "Ledger task heading/id, status, retry, owner, next artifact section"
optional_fields:
  - name: input_mode
    description: "pipeline | standalone"
  - name: re_execution_conditions
    description: "When to re-execute vs resume"
  - name: handoff_boundary
    description: "What changes between owners"
---

# Checkpoint

<!-- Resume source of truth. On context compression or handoff, read this file first, then the ledger row named in Resume Pointer, then implementation-notes.md Reader Summary/Evidence Index. -->

<!-- INSTANT-ANSWER BLOCK: first 6 fields for rapid resume scan -->

## Stage
<!-- clarify | plan | execute | review | ship | long-run -->

## Status
<!-- in_progress | completed | blocked -->

## Active Task
<!-- Which task from plan.md / ledger.md is currently in progress, or "none" -->

## Next Action
<!-- The single action to take when resuming -->

## Blockers
<!-- List active blockers or "none" -->

## Resume Pointer
<!-- Required before every handoff/compression: ledger task heading/id, current status, retry count, owner, and exact artifact section to update next. Example: ledger.md#task-2-update-docs status=in_progress retry=1 owner=worker next_update=implementation-notes.md#Evidence -->

<!-- DETAIL BLOCK: expanded context below -->

## Last Verified Evidence
<!-- Most recent real command/artifact evidence. Use "none" if no command has run yet. Example: evidence_index:task=T2 command="make validate" exit=0 artifact=implementation-notes.md#Evidence -->

## Resume Read Order
<!-- Default: checkpoint.md Resume Pointer → ledger.md matching task row → implementation-notes.md Reader Summary → implementation-notes.md Evidence Index → plan.md referenced item only. Do not reload the whole chat transcript as state. -->

## Handoff Boundary
<!-- Required when ownership changes or a stage needs a forbidden action. Record: current owner, next owner / owning next stage, handoff reason, requested/forbidden action, evidence or artifact trigger, blocker/limitation impact, explicit stop condition, and exact artifact update location. -->
## Minimum Read Set
<!-- Example: checkpoint → ledger → implementation-notes Reader Summary → plan Task N -->

## Re-Execution Conditions
<!-- Present when review verdict is changes_requested/blocked. Consumed by next execute cycle. -->
<!-- "사과가 아니라 조건이 바뀌어 루프가 닫힌다" -->

### Source Review
<!-- review-report.md path and verdict -->

### Loop Counter
<!-- Current iteration: N (max 3) -->

### Failure Analysis
<!-- Per-finding: severity, root cause, required fix, files to modify -->

### Corrected Execution Conditions
<!-- Changed constraints, scope, verification gates -->

### Rollback Instructions
<!-- git restore <files> | git stash | full rollback to checkpoint -->

### Memory Bank Update
<!-- Record failure as fact for future prevention -->
