# Automation / Non-Interactive Approval Mode

Shared rules for handling automated ForgeFlow stage transitions.

## Flags

The following flags enable automated stage transitions:

- `--yes` — approve the current stage boundary only
- `--auto-approve` — same as `--yes`
- `--non-interactive` — suppress interactive prompts where possible
- `--auto` — **auto-chain**: proceed through all remaining stages without stopping at stage boundaries

## --auto chaining behavior

When `--auto` is active (set via flag, `brief.md` auto field, or user instruction), the agent:

1. Writes the required artifact for the current stage
2. Updates `checkpoint.md` at stage exit (see Strict auto-chain)
3. Invokes the next stage skill directly in the same turn (or immediately in the next turn if context limits require it — **never** wait for `(y/n)`)
4. Continues chaining until the workflow completes or hits an auto-break condition

### Chain sequence by route

| Route | Auto-chain sequence |
|-------|-------------------|
| small | clarify → execute → review → ship |
| medium | clarify → plan → execute → review → ship |
| high | clarify → plan → execute → review(spec) → review(quality) → ship |
| epic | clarify → plan → execute → review(spec) → review(quality) → ship |

### Auto-break conditions (--auto stops here)

The agent must **stop and wait for user input** when any of these occur, even under `--auto`:

- **Failed verification**: build, lint, type_check, or test failure that the bounded fix loop cannot resolve
- **Blockers**: unresolved open questions or missing dependencies in `brief.md`
- **Review verdict: `changes_requested`**: must present findings and wait for user direction before re-executing
- **Destructive actions**: ship branch-disposition discard confirmation, force-push, branch deletion
- **Ambiguous route or scope change**: when the request no longer matches the original brief (see Scope change under --auto)
- **Missing required artifact**: any mandatory artifact that could not be produced
- **External dependency hard failure**: required external call (API, credential, service) fails and no brief-approved fallback exists — record blocker in `checkpoint.md` and stop; do not silently substitute a workaround and continue coding
- **Context limit**: cannot fit the next stage in the current turn — write checkpoint with explicit `Next Action: invoke /forgeflow:<next>` and continue in the **next assistant turn without asking the user**

### --auto does NOT bypass

- Safety confirmations for `--real` external execution
- Discard confirmation in ship branch disposition (always requires exact `discard` input)
- The 4-option choice in ship branch disposition (merge/PR/keep/discard)
- Quality improvement loop-back in `ship` (if issues found, ask before returning to execute)

## Strict auto-chain mode

`--auto` implies **strict auto-chain**: one user approval at clarify entry covers the full route sequence through ship summary. Treat any deviation below as a contract violation unless an auto-break condition applies.

### Core ordering rule

**Artifacts before code.** At every stage boundary and during execute:

1. Write or update the stage artifact on disk
2. Update `checkpoint.md` (`Current Stage`, `Status`, `Active Task`, `Next Action`, `Latest Artifacts`)
3. Only then edit application code or invoke the next stage

Never start implementation while `plan.md` is missing, `run-ledger.md` scaffolds are absent, or `checkpoint.md` still points at a prior stage.

### Per-stage exit checklist

Complete **all** items before invoking the next stage or editing code outside the current stage scope.

#### clarify → next

| Step | Required before next stage |
|------|---------------------------|
| Artifact | `brief.md` with route, scope, AC, blockers resolved |
| Checkpoint | `Current Stage: clarify` → exit update; `Next Action: invoke /forgeflow:plan` (medium+) or `/forgeflow:execute` (small) |
| Chain | Invoke next stage skill **immediately** — no `(y/n)` prompt |
| Forbidden | Starting code edits in the clarify turn; skipping plan on medium/high/epic |

#### plan → execute

| Step | Required before execute |
|------|------------------------|
| Artifact | `plan.md` + scaffolds: `implementation-notes.md`, `run-ledger.md` |
| Checkpoint | `Current Stage: plan`; `Active Task: Task 1` (or first pending); `Next Action: begin Task 1` |
| Chain | Invoke `/forgeflow:execute` immediately — no `(y/n)` prompt |
| Forbidden | Implementing plan tasks in the plan turn; asking "execute 진행?" under `--auto` |

#### execute → review

| Step | Required before review |
|------|------------------------|
| Ledger | Each task row updated incrementally (`pending` → `in_progress` → `done`/`blocked`) — **not** batch-marked at the end |
| Notes | `implementation-notes.md` updated per task (Decisions, Evidence, Deviations) |
| Checkpoint | Updated after **each** task completes; `Active Task` must not stay stale on Task 1 while later tasks finish |
| Evidence | Verification commands run; results in Evidence / Gate Results |
| **/clear** | **Mandatory between every task** — after checkpoint, ledger, evidence are written to disk, `/clear` before starting the next task. Do not chain tasks in the same context. Resume follows checkpoint-first protocol (→ `_shared/context-resume.md`). |
| Chain | Invoke `/forgeflow:review` immediately when all tasks done — no `(y/n)` prompt |
| Forbidden | Deferring ledger/notes until the user asks "어디까지?"; coding after execute exit without review; skipping `/clear` between tasks |

#### review → ship

| Step | Required before ship |
|------|---------------------|
| Artifact | `review-report.md` with written verdict |
| Checkpoint | `Current Stage: review`; verdict reflected in `Next Action` |
| Chain | If `approved`: invoke `/forgeflow:ship` immediately — no `(y/n)` prompt |
| Forbidden | "리뷰 통과. ship 진행?" under `--auto`; proceeding to ship when verdict ≠ `approved` |

#### ship completion

| Step | Required |
|------|----------|
| Artifact | `ship-summary.md` with verification table and handoff |
| Checkpoint | `Current Stage: ship` remains the terminal workflow stage while disposition completes |
| Chain | After summary: present branch disposition 4-option choice (always user input) |
| Allowed stop | merge/PR/keep/discard choice; discard exact confirmation; ship quality loop-back `(y/n)` |

### Prompts forbidden under --auto

Do **not** emit these (or equivalent) while `--auto` is active:

- `다음 스텝으로 /forgeflow:plan을 진행하시겠습니까? (y/n)`
- `계획은 여기까지 확정됐습니다. /forgeflow:execute을 진행하시겠습니까? (y/n)`
- `구현 완료. /forgeflow:review를 진행하시겠습니까? (y/n)`
- `리뷰 통과. /forgeflow:ship을 실행해주세요.` (without immediately invoking ship)
- `execute하고 리뷰해야겠지?` / `ship까지?` — rhetorical checks that wait for user confirmation

Replace with: write artifact → update checkpoint → invoke next stage (or auto-break with blocker record).

### Scope change under --auto

If implementation would touch **Out of Scope** in `brief.md`, add AC not in the brief, or contradict a stated Non-goal:

1. **Stop** — do not silently expand scope and continue under `--auto`
2. Update `checkpoint.md`: `Status: blocked`, `Blockers: scope change — <description>`
3. Present the delta to the user: proposed scope change, brief sections to update, and whether to resume `--auto` after brief amendment
4. Resume `--auto` only after `brief.md` (and `plan.md` if tasks change) reflect the new scope

**User mid-execute instructions** (e.g. "implement from this screenshot") that contradict the brief are scope changes, not implicit approval to bypass auto-break — unless the user also explicitly says to amend the brief and continue `--auto`.

### External dependency failures (e.g. API 429)

When a verification step depends on an external service:

| Situation | Under --auto |
|-----------|--------------|
| Transient error (429, timeout) | Bounded retry (≤2) with backoff; record attempt in `run-ledger.md` Gate Results |
| Retry exhausted; brief requires live API success | **Auto-break**: checkpoint blocker, stop; do not mark AC met via unapproved fallback |
| Brief or plan documents an approved fallback path | May use fallback; record `Decision` in `implementation-notes.md` and Gate Results as `partial`/`fallback` |
| User requests ad-hoc fallback mid-execute | Treat as scope/process change — update brief/plan or auto-break |

Do not substitute screenshot fixtures, offline modes, or mock paths unless the brief/plan already allows them or the user amends scope and re-approves `--auto`.

### Anti-patterns (observed failure modes)

These patterns indicate `--auto` was **not** honored — correct on the next task:

| Anti-pattern | Correct behavior |
|--------------|-------------------|
| `brief.md` written, then code edits in same clarify/plan turn | Finish stage artifact + checkpoint, invoke next stage, implement only in execute |
| `plan.md` exists but no plan-stage checkpoint / scaffolds | Write scaffolds + checkpoint before any implementation |
| `checkpoint.md` stuck at `execute` / Task 1 while Task 2–3 complete | Update checkpoint after **each** task |
| `run-ledger.md` / `implementation-notes.md` created only when user asks progress | Create scaffolds at plan exit; update incrementally during execute |
| Review passed but agent waits for "ship까지?" | Invoke `/forgeflow:ship` immediately |
| Out-of-scope work (e.g. area tab slider when brief says informational only) without brief update | Auto-break + scope amendment |
| API 429 → unapproved fallback → continue as if AC met | Auto-break or record approved fallback + partial gate; never silent continuation |

### Resume after auto-break

When stopping for auto-break:

1. `checkpoint.md` must list `Status: blocked`, concrete `Blockers`, and `Next Action` (single step)
2. Do not edit application code until the user resolves the blocker or explicitly directs otherwise
3. On resume with `--auto` still active: read checkpoint → resolve blocker → continue chain from `Next Action` without re-asking prior stage boundaries

## Compact timing during auto-chain

When `--auto` chains multiple stages in one turn, context pressure may trigger `/compact`. Follow `_shared/context-resume.md` timing rules, adapted for auto-chain:

| Auto-chain moment | Safe to compact? | Condition |
|---|---|---|
| After stage artifact + checkpoint written | **Yes** | Both artifact and checkpoint are on disk |
| Mid-execute, task done + evidence recorded | **Yes** | Ledger + notes + checkpoint updated for that task |
| Between stage invocation (next skill loading) | **No** | No artifact written yet for the next stage |
| Mid-review before verdict | **No** | Verdict not recorded |

On resume after compact during auto-chain:
1. Read `checkpoint.md` first (see `_shared/context-resume.md`).
2. If `Status: blocked`, treat as auto-break — do not resume chain until blocker is resolved.
3. If `Status: in_progress` and `--auto` is still active, continue chain from `Next Action` without asking the user.

Do **not** use compact as an excuse to pause auto-chain and wait for user input. The chain continues automatically unless an auto-break condition applies.

## General rule

If the user explicitly includes any of the flags above, or says to continue through ForgeFlow stages without further approval, treat that as approval for the current bounded ForgeFlow sequence. This only applies inside the stated task scope and never overrides a blocker, failed verification, missing required artifact, or unsafe/destructive action.
