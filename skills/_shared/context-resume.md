# Context Resume and Compact Safety

Shared rules for `/compact` and `/clear` timing, checkpoint-first resume, minimum read sets, and section-targeted reads across all ForgeFlow stages.

## Principles

1. **Artifact-first stays** — compaction/clear does not replace artifacts; it makes resume discipline mandatory.
2. **Checkpoint-first** — on resume (after /compact or /clear), read `checkpoint.md` before any other task artifact when it exists.
3. **No default full re-read** — expand to full artifacts only when verification, findings, or blockers require it.
4. **Ledger = truth, notes = narrative** — task status from `run-ledger.md`; decisions from `implementation-notes.md`.
5. **Step-complete = checkpoint-first** — once a plan step finishes and checkpoint/ledger/evidence are updated on disk, the next step must be resumable from artifacts. Context refresh is adapter-specific and optional unless context pressure is high; resume from artifacts is mandatory, not optional.

## `/compact` and `/clear` timing

Context refresh is safe when artifacts are up to date. Keep the core skill adapter-neutral: do not require a Claude-only slash command for every plan step. Prefer checkpoint-first continuation; use refresh only when context pressure or role bleed is visible. Claude Code and Codex CLI can both use `/compact` for ordinary pressure. For a fully fresh context, Claude Code can use `/clear` + `/forgeflow:execute --resume`; Codex can use `/clear`/`/new` when interactive, or start a fresh `codex exec`/session with an explicit "resume from .forgeflow/tasks/<task-id>/checkpoint.md" prompt. The checkpoint-driven resume reads exactly what is needed from disk, making accumulated context wasteful.

Compact or clear context at:

- **Stage boundary** — after the stage's exit artifact is written (e.g. `brief.md`, `plan.md`, `review-report.md`).
- **Step boundary (execute)** — after a plan step completes and `checkpoint.md`, `run-ledger.md`, and `implementation-notes.md` evidence are all updated on disk. Continue to the next task from the checkpoint in `--auto`; if context pressure is high, output an adapter-specific refresh hint and stop.
- **Checkpoint refresh** — after task completion when `run-ledger.md`, evidence, and `checkpoint.md` are updated on disk.

Do **not** compact or clear when:

- A file edit is in progress and not saved to artifact or codebase.
- Verification ran but results are not yet in `implementation-notes.md` Evidence.
- A subagent/worker is `running` in `run-ledger.md` without evidence refs.
- You are mid-review before verdict is recorded.

| Stage | Safe to /compact or /clear after | Unsafe during |
|-------|----------------------------------|---------------|
| clarify | brief + checkpoint | pre-brief questioning |
| plan | plan + scaffolds + checkpoint | mid task decomposition |
| execute | step done + ledger + evidence + checkpoint | mid-implementation / pre-evidence |
| review | review-report sections + checkpoint | pre-verdict |
| ship | ship-summary draft + verification | pre-handoff |

## Universal resume read order

```text
checkpoint.md
  → run-ledger.md (active task + gates)
  → implementation-notes.md (Reader Summary + Evidence Index)
  → checkpoint Minimum Read Set sections in other artifacts
  → full artifact (only if needed)
```

Before reading any file, ask: **full content, Reader Summary, or specific section?** Prefer line-range or heading-scoped reads for sections over 80 lines.

## Section-targeted read procedure

1. Read `checkpoint.md` → `Minimum Read Set` and `Next Action`.
2. If artifact has **Reader Summary** (high/epic), read it first (~30 lines max).
3. Jump to named sections (e.g. `## 검증 계획 (Verification Plan)`, `### Task 3:`) instead of reading from line 1.
4. Use Evidence Index compact strings before expanding full Evidence blocks.
5. Record in checkpoint when you expand beyond minimum read set (brief note in Compact-Safe Context Notes).

## Context budget heuristics

- Do not re-read a file already in context unless edited since last read.
- Batch parallel tool calls for independent file inspections.
- Prefer grep/heading search to locate sections before full file read.
- For plans over ~150 lines: read Reader Summary + Requirements + active task + Verification Plan entries for that task only.
- **Anti-pattern**: reading all artifacts at stage entry "to be safe" — use checkpoint Minimum Read Set instead.

## Stage minimum read sets

See task-local `contracts.md` when present, or use these defaults:

| Stage | Minimum read |
|-------|----------------|
| clarify (new) | user request + repo context as needed |
| clarify (resume) | checkpoint → brief in-progress sections |
| plan (new) | brief Objective/Scope/AC |
| plan (resume) | checkpoint → brief summary → plan Tasks/Verification Plan |
| execute (resume) | checkpoint → ledger active row → notes summary → plan active task |
| review | checkpoint → ledger gates → notes summary → brief AC → plan Requirements + implicated tasks |
| ship | checkpoint → review-report summary/verdict → ship-summary draft |

## Evidence index convention

Append compact lines to `implementation-notes.md` Evidence or Evidence Index:

```text
evidence_index: task=<id> gates=<gate>:PASS,<gate>:PASS
verification:PASS gate=<name> command="<cmd>" exit=0
contract_check:PASS <task>
```

Review and ship parse these before reading full Evidence sections.

## Auto-chain resume (compact during --auto)

When `--auto` is active and compact fires between stages, resume follows the same checkpoint-first procedure above. The only difference: after reading checkpoint, if `Status: in_progress` and `--auto` is still active, continue the chain from `Next Action` without asking the user. Do not re-confirm prior stage boundaries.

See `_shared/automation.md` → "Compact timing during auto-chain" for safe compact moments during auto-chain.

## Design reference

Large brownfield tasks (e.g. frontend extension with 300+ line `plan.md`) demonstrate repeated full-plan re-read cost. Keep section anchors in long plans; use Reader Summary at artifact top for high/epic routes.

## Related

- Checkpoint template: `templates/checkpoint.md`
- Preflight (review/ship): `_shared/preflight.md`
- Discipline (Reader Summary): `_shared/discipline.md`
- Automation (auto-chain compact): `_shared/automation.md`
