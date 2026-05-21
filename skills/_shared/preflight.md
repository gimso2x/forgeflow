# Status Analysis Preflight

Shared preflight procedure for review and ship stages.
Uses **checkpoint-first, section-targeted reads** — not full artifact re-reads by default.

→ Compact/resume rules: `_shared/context-resume.md`

## Procedure

1. Read `checkpoint.md` from the active task directory when present. Use its `Minimum Read Set`, `Next Action`, and `Blockers` before opening other artifacts.
2. Identify the active task from checkpoint `Active Task` or the most recent `.forgeflow/tasks/<task-id>/` with artifacts.
3. Read `run-ledger.md` — active task row, Gate Results, Completion Summary. Cross-check claimed completion against ledger (ledger = execution truth).
4. Read `implementation-notes.md` — **Reader Summary** and **Evidence Index** first; expand Decisions/Evidence sections only when findings require it.
5. Expand other artifacts per checkpoint Minimum Read Set — **not** all files by default:
   - `brief.md` → Acceptance Criteria, Scope (In/Out) sections
   - `plan.md` → Requirements, Verification Plan, and task sections implicated by findings or open gates (not full plan unless route/high complexity demands)
   - `review-report.md` → Reader Summary, Verdict, Findings (ship stage)
   - `eval-record.md` → only when checkpoint Next Action or long-run route requires it
   - `.forgeflow/evolution/proposed/*.md` → only when review scope includes evolution candidates

## Review-specific additions

Reconstruct task state from artifacts instead of chat memory. Do **not** read every artifact in full at entry.

- For **high/epic**, collect `micro_spec:*` and `micro_quality:*` from implementation-notes Evidence Index or Evidence section. Summarize in `review-report.md` → **Execute Micro-Gates**. Treat as **reported evidence** until re-verified.
- Read `.forgeflow/evolution/active/*.md` (project) when consistency check is in scope.
- Expand `plan.md` beyond Requirements/Verification Plan only for tasks under review or with failed gates.
- Expand `brief.md` beyond Acceptance Criteria only when scope disputes arise.

## Ship-specific additions

- Start from `review-report.md` Reader Summary + Verdict + Open Blockers.
- Read `ship-summary.md` draft if present; expand `implementation-notes.md` only for handoff evidence gaps.
- Avoid re-reading full `plan.md` unless ship-summary or evolution extraction requires traceability to specific tasks.

## Anti-patterns

| Anti-pattern | Fix |
|--------------|-----|
| Reading all artifacts at review entry | Follow checkpoint Minimum Read Set |
| Full `plan.md` re-read on every resume | Reader Summary + implicated task sections |
| Ignoring Evidence Index compact lines | Parse index before expanding Evidence |
| Using checkpoint as progress report | Keep checkpoint terse; details live in notes/ledger |
