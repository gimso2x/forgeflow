# Eval scenario: fan-out execute + stage review

**Purpose:** Guard against drift between execute delegation docs and run-ledger assignee discipline.  
**Eval id:** `fan-out-execute-ledger` in `evals/evals.json`  
**Route:** high (fan-out/fan-in)

## Setup

Plan with two parallel steps:

| Step | Files | Depends |
|------|-------|---------|
| A — API auth handler | `src/api/auth.ts` | (none) |
| B — Login UI | `src/ui/login.tsx` | (none) |

Architecture Notes: `fan-out/fan-in + producer-reviewer`

## Expected execute behavior

1. Dispatch two specialist workers in parallel (`references/implementer-prompt.md`)
2. Controller verifies each: `git diff --stat`, step verification
3. Per-step micro-gates: `micro_spec:PASS` (high route)
4. `run-ledger.md`: Assignee `specialist` while running; `done` only after verification
5. Fan-in: cross-check shared types/contracts if plan names them

## Expected review behavior (after execute)

1. `/forgeflow:review --type spec` — fill `review-report.md` → **Execute Micro-Gates** from implementation-notes; re-verify each step (`Stage re-verified: yes` only after independent inspection)
2. `/forgeflow:review --type quality` — only after spec approved
3. **Evidence Classification** — list `micro_spec` / `micro_quality` under reported evidence until re-verified

Eval: `fan-out-execute-ledger` (execute), `review-micro-gates-table` (review handoff).

## Failure modes this catches

- Steps marked `done` on subagent DONE without verification
- Empty Assignee in run-ledger
- Skipping spec micro-check on high route
- Merging spec + quality stage review in one turn
