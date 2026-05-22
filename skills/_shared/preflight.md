# Status Analysis Preflight

Shared preflight procedure for maintainer automation, review, and ship stages.
Uses **checkpoint-first, section-targeted reads** — not full artifact re-reads by default.

→ Compact/resume rules: `_shared/context-resume.md`

## Maintainer/autonomous repo preflight

When acting as a ForgeFlow maintainer on this repository (cron loop, scheduled improvement run, or release-maintenance pass), protect unknown work before any repository mutation:

1. Read `AGENTS.md`, run `git branch --show-current` to confirm the current branch is the expected target branch (normally `main`), and inspect `git status --short --branch` first so ahead/behind state is visible before pull/push decisions.
2. If the branch is not the configured target branch, stop before pull/edit/commit/push and report the actual branch from `git branch --show-current` as a blocker.
3. If any modified, staged, deleted, or untracked path is present and you did not create it in the current run, stop. Report the dirty paths as user/unknown changes.
4. Do **not** run `git pull`, edit files, commit, push, clean, stash, or discard while the branch or dirty-tree preflight is unresolved.
5. Only after a clean preflight, refresh `main` with `git pull --ff-only` before selecting improvement work.
6. Immediately rerun `git status --short` after the pull. If the refresh leaves any dirty path, stop and report those paths before editing, cleaning, committing, or pushing.
7. After your focused change and validation, rerun `git status --short` before staging. Stage only the files you intentionally changed in this run; if any unexpected path appears, stop and report it instead of committing or pushing.
8. After commit and push, rerun `git status --short` and report any remaining dirty paths instead of claiming the repository is clean.
9. Do not schedule jobs, modify cron/crontab, or change external automation from inside the scheduled run. Treat cadence changes as operator-owned follow-up outside the repository improvement tick.

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
