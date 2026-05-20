# Status Analysis Preflight

Shared preflight procedure for finish, review, and ship stages.
Read the latest task artifacts before taking action.

## Procedure

1. Read the latest `review-report.md`, `brief.md`, and `eval-record.md` when present from the active task directory.
2. Identify the active task by inspecting `.forgeflow/tasks/` directories and finding the one with the most recent artifacts.
3. Cross-check claimed completion against `run-ledger.md` entries when available.

## Review-specific additions

For the review stage, also reconstruct the full task state from artifacts instead of chat memory:

- Read `implementation-notes.md` for current stage/status, decisions, deviations, progress, evidence, and blockers.
- Read `run-ledger.md` for per-task execution status (pending/running/done/blocked), assignee (`worker` | `specialist` | `spec-reviewer` | `quality-reviewer`), evidence refs, and blockers. Cross-check claimed completion against ledger entries.
- For **high/epic**, collect `micro_spec:*` and `micro_quality:*` lines from implementation-notes Evidence. Summarize them in `review-report.md` → **Execute Micro-Gates** (see `templates/review-report.md`). Treat them as **reported evidence** until re-verified in this review turn.
- Read `.forgeflow/evolution/proposed/*.md` when present and validate candidates against `templates/evolution-rule.md`.
- Read `plan.md` to confirm planned tasks, requirements, contracts, and verification plan.
