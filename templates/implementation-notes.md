---
schema: implementation-notes/v1
stage: <!-- clarify|plan|execute|review|ship|long-run -->
status: <!-- in_progress|completed|blocked -->
required_fields:
  - name: stage
    description: "clarify|plan|execute|review|ship|long-run"
  - name: status
    description: "in_progress|completed|blocked"
  - name: decisions
    description: "D-NNN entries with context, options, chosen, rationale"
  - name: progress
    description: "Current work tracking"
  - name: evidence
    description: "Verification evidence collected"
optional_fields:
  - name: edge_cases
    description: "Boundary conditions encountered"
  - name: metrics
    description: "Quantitative measures"
---

# 구현 기록 (Implementation Notes)

<!-- ForgeFlow execution tracking. Updated throughout execute stage. -->
<!-- Write prose in the user's primary language. Preserve canonical labels, enum values, commands, paths, and artifact filenames in English. -->
<!-- Prefer bullet lists over Markdown tables unless a compact matrix is clearly easier to scan. Keep changed files, evidence, metrics, and blockers readable in plain CLI/Telegram transcripts. -->

## 사용자용 요약 (Reader Summary)
<!-- For high/epic routes especially: summarize completed work, current status, verification evidence, and remaining risks in the user's language. -->

## 현재 단계 (Current Stage)
<!-- clarify | plan | execute | review | ship | long-run -->

## 상태 (Status)
<!-- in_progress | completed | blocked -->

## 결정 사항 (Decisions)

<!-- Primary decision record. Replaces decision-log.md (deprecated as of v1.11). -->
<!-- Append entries as decisions arise throughout all stages (clarify → plan → execute → review → ship). -->

### D-001: <!-- title -->
- **Stage**: <!-- clarify|plan|execute|review|ship -->
- **Category**: <!-- scope | plan | execution | review | recovery | routing -->
- **Context**: <!-- why this decision was needed -->
- **Options**:
  - A: <!-- option A -->
  - B: <!-- option B -->
- **Chosen**: <!-- A or B -->
- **Rationale**: <!-- why this option was selected -->
- **Alternatives Considered**: <!-- what else was evaluated -->
- **Tradeoff**: <!-- what was gained vs sacrificed -->
- **Rollback Implication**: <!-- what happens if this is reversed, or "irreversible" -->
- **Reversible**: <!-- yes|no -->

## 계획 대비 변경 (Deviations from Plan)
<!-- Any deviations from the approved plan and why -->

## 진행 상황 (Progress)
<!-- [██████░░░░] 60% -->
<!-- Checkpoint tracking -->
- [ ] Task 1: <!-- status -->
- [ ] Task 2: <!-- status -->

## 변경 파일 (Files Changed)
<!-- path — description of change -->
-

## 증거 (Evidence)

- `surgical_scope:PASS task=<id> changed=<paths> rationale="maps to approved plan scope"`
- `simplicity_check:PASS task=<id> rationale="no speculative abstraction/configuration added"`
<!-- Gate results, test outputs, verification outcomes -->
<!-- Use compact strings parseable by review/ship preflight: verification:PASS/FAIL, contract_check:PASS/FAIL, evidence_index:task=... -->
-

### Command Evidence Format

<!-- Append one block per real command. Do not summarize invented or unrun commands. -->

```text
evidence_id: E-<!-- N -->
task: <!-- ledger task id/title -->
kind: command
cwd: <!-- absolute or repo-relative cwd -->
command: <!-- exact command -->
exit_code: <!-- integer -->
result: <!-- PASS | FAIL | SKIPPED -->
output_summary: <!-- short factual summary; include counts/errors, not vibes -->
artifact_ref: <!-- path, log file, PR/check URL, or "inline" -->
timestamp: <!-- ISO8601 -->
```

### Artifact Evidence Format

```text
evidence_id: E-<!-- N -->
task: <!-- ledger task id/title -->
kind: artifact
path: <!-- file path or URL -->
claim_verified: <!-- what this artifact proves -->
result: <!-- PASS | FAIL | SKIPPED -->
timestamp: <!-- ISO8601 -->
```

## Evidence Index
<!-- Compact refs updated during execute. Parse before expanding full Evidence above. -->
<!-- Example: evidence_index: task=T2 gates=make validate:PASS,contract_check:PASS -->
<!-- ledger.md = per-task status truth; this file = decisions + evidence narrative -->
- `evidence_index: task=<ledger-task> evidence=<E-N> command="<cmd>" exit=<code> result=<PASS|FAIL|SKIPPED> artifact=<path|inline>`

## 컴포넌트/함수 역할 (Role Descriptions)
<!-- One-line role for each changed component/function. Required for all routes. -->
<!-- Example: FilterTabs — controls tab switching between filter panels -->
<!-- Example: syncPriceRange — syncs slider value to filter state -->

## 엣지 케이스 (Edge Cases)
<!-- Enumerate edge cases verified during execution. Required for medium/high/epic routes. -->
<!-- Example: empty selection resets summary chip -->
<!-- Example: slider drag past preset boundary preserves preset label -->

## 차단 요소 (Blocked By)
<!-- List blockers or "none" -->

## 지표 (Metrics)
<!-- Quantitative code quality metrics collected during execute -->
<!-- Populated by adapter-aware execution code quality metrics step -->

- **LOC generated**: <!-- total lines in src/ -->
- **TS errors**: <!-- npx tsc --noEmit error count -->
- **Type assertions**: <!-- grep -r "as " count -->
- **Debug artifacts**: <!-- console.log/TODO/FIXME count, target: 0 -->
- **Max component LOC**: <!-- largest component, flag if > 100L -->
- **Files created**: <!-- count -->
- **Files deleted**: <!-- count -->
## Next Steps → ff-review
<!-- Stage handoff contract: what the next stage needs from this artifact -->
- **Next Stage**: ff-review
- **Required Input**: evidence, changed files list, decisions
- **Recommended Input**: edge cases, metrics, progress status
- **Known Gaps**: <!-- list unverified areas or incomplete evidence -->
