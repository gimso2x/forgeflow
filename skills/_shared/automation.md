# Automation / Non-Interactive Approval Mode

Shared rules for handling automated ForgeFlow stage transitions.

## Flags

The following flags enable automated stage transitions:

- `--yes` — approve the current stage boundary only
- `--auto-approve` — same as `--yes`
- `--non-interactive` — suppress interactive prompts where possible
- `--auto` — **auto-chain**: proceed through all remaining stages without stopping at stage boundaries
- `--loop` — **full loop**: auto-chain + retry failed tasks, re-execute on review changes, auto-promote route, re-plan on scope drift. Runs the complete lifecycle in one invocation until ship or irrecoverable blocker.

### How --auto is activated

`--auto` is active when ANY of these is true:
1. `--auto` flag passed to the skill invocation
2. `<storage-root>/defaults.md` contains `auto: true` (read at clarify stage, propagated to `brief.md`)
3. `brief.md` has `auto: true` in its metadata
4. User explicitly says to auto-chain (e.g., "자동으로 진행", "auto chain", "계속 진행")

### How --loop is activated

`--loop` is active when ANY of these is true:
1. `--loop` flag passed to the skill invocation
2. User explicitly says to loop (e.g., "루프로 돌려", "loop로 해", "한 번에 끝까지")
3. `<storage-root>/defaults.md` contains `loop: true`

`--loop` implies `--auto`. When `--loop` is active, all `--auto` chaining rules apply **plus** the loop extensions below.

`--auto-approve` and `--yes` approve only the current stage boundary. They do not opt into full-route chaining unless the user also says to auto-chain or another `--auto` activation source is present.

When clarify reads `<storage-root>/defaults.md` and finds `auto: true`, it MUST set `brief.md`'s auto field to `true` so all subsequent stages see it.

## --auto chaining behavior

When `--auto` is active (set via flag, `brief.md` auto field, or user instruction), the agent:

1. Writes the required artifact for the current stage
2. Updates `checkpoint.md` at stage exit (see Strict auto-chain)
3. Invokes the next stage through the adapter's native skill mechanism in the same turn — **never** just print the skill name as text without actually invoking or continuing the next stage
4. If context limits prevent the next Skill call in the same turn, write checkpoint with `Next Action: invoke /forgeflow:<next>` and continue in the **next assistant turn** without asking the user
5. Continues chaining until the workflow completes or hits an auto-break condition

### How to invoke the next stage (CRITICAL)

Under `--auto`, "invoke the next stage" means **calling the Skill tool when the adapter exposes one, or immediately continuing with the next stage skill instructions when it does not**. Printing text is not enough.

```
✅ Correct: Call Skill(skill: "forgeflow:ff-plan", args: "--task-id <id>")
✅ Correct: Call Skill(skill: "forgeflow:execute", args: "--task-id <id>")
✅ Correct in Codex App/CLI when no Skill tool is exposed: write checkpoint Next Action, load/follow the next stage SKILL.md contract, and continue without a y/n prompt
❌ Wrong: Printing "/forgeflow:ff-plan" as text without calling Skill tool
❌ Wrong: Printing "defaults에 auto: true가 설정되어 있어 자동 진행합니다" then stopping
❌ Wrong: Asking "(y/n)" under --auto
```

If you find yourself about to print a y/n prompt or just mention the next skill name, STOP and invoke the next stage through the available adapter-native mechanism instead.

**Codex App compatibility rule:** Codex skills can run in app, CLI, or IDE surfaces, and some Codex contexts expose skills as instructions rather than a callable `Skill` tool. In that case the strict contract is still: artifact written, checkpoint updated, next stage contract loaded, and execution continues from that contract. The only invalid behavior is stopping after a textual slash-command suggestion when no auto-break condition applies.

### Chain sequence by route

| Route | Auto-chain sequence |
|-------|-------------------|
| small | clarify → execute → ship (self-verify replaces formal review) |
| medium | clarify → plan → execute → review → ship |
| high | clarify → plan → execute → review(spec) → review(quality) → ship → long-run |
| epic | clarify → plan → execute → review(spec) → review(quality) → ship → long-run |

### Auto-break conditions (--auto stops here)

The agent must **stop and wait for user input** when any of these occur, even under `--auto`:

- **Failed verification**: build, lint, type_check, or test failure that the bounded fix loop cannot resolve
- **Blockers**: unresolved open questions or missing dependencies in `brief.md`
- **Review verdict: `changes_requested`**: must present findings and wait for user direction before re-executing. Exception: if ALL findings are artifact-only (scope_files, brief, plan, implementation-notes 등 `.forgeflow/` 메타데이터 수정만 필요한 경우), auto-fix artifacts then re-invoke `/forgeflow:ff-review` without stopping. 코드 로직 변경이 필요한 finding이 하나라도 있으면 기존대로 auto-break.
- **Destructive actions**: ship branch-disposition discard confirmation (always requires exact `discard` input), force-push, branch deletion — note: "Merge locally" under `--auto` is NOT destructive and does not require confirmation, but merge conflicts are auto-break: stop and present conflicts for user resolution before continuing
- **Ambiguous route or scope change**: when the request no longer matches the original brief (see Scope change under --auto)
- **Missing required artifact**: any mandatory artifact that could not be produced
- **External dependency hard failure**: required external call (API, credential, service) fails and no brief-approved fallback exists — record blocker in `checkpoint.md` and stop; do not silently substitute a workaround and continue coding
- **Context limit**: cannot fit the next stage in the current turn — write checkpoint with explicit `Next Action: invoke /forgeflow:<next>` and continue in the **next assistant turn without asking the user**

### --auto does NOT bypass

- Safety confirmations for `--real` external execution
- Discard confirmation in ship branch disposition (always requires exact `discard` input)
- The 4-option choice in ship branch disposition — only when NOT `--auto`. Under `--auto`, default to "Merge locally" and proceed without prompting (see ship completion below).
- Quality improvement loop-back in `ship` (if issues found, ask before returning to execute)

## --loop mode

`--loop` extends `--auto` with **retry, re-execution, promotion, and re-plan** capabilities. Under `--loop`, the agent keeps running the full lifecycle until ship succeeds or an irrecoverable blocker is hit.

### Loop-specific behaviors

| Situation | --auto (no loop) | --loop |
|---|---|---|
| Verification failed | Auto-break | Retry up to route budget, then auto-break |
| Review `changes_requested` (code) | Auto-break | Re-execute affected items, re-run review |
| Review `changes_requested` (artifact-only) | Auto-fix + re-review | Auto-fix + re-review (same) |
| Scope drift detected | Auto-break | Re-plan in place, update brief if needed, continue |
| Retry budget exhausted | Auto-break | **Promote route** (small→medium, medium→high) and retry |
| Promotion not possible (already high/epic) | Auto-break | Auto-break (record as irrecoverable blocker) |
| Route promoted | N/A | Record in `implementation-notes.md` as `D-<!-- N --> route_change`, update ledger route, continue |
| Plan needs update after scope drift | Auto-break | Re-plan affected items, update `plan.md` and `ledger.md`, continue |
| Context limit hit | Write checkpoint, continue next turn | Same — write checkpoint, continue next turn |
| Irrecoverable blocker (credential, missing dep, user decision) | Auto-break | Auto-break (same) |

### Retry budgets (--loop)

| Route | Max retries per task | Max total loop iterations |
|---|---|---|
| small | 1 | 2 |
| medium | 2 | 4 |
| high | 2 | 5 |
| epic | 3 (per milestone) | 6 |

A retry requires a **changed condition**: modified code, modified plan, new evidence, resolved blocker, or revised scope. Blind reruns without changes are noise — do not count them toward the budget.

### Route promotion (--loop)

When retry budget is exhausted and the task still fails:

1. Record in `implementation-notes.md`:
   ```
   D-<!-- N --> route_change from=<old> to=<new> reason=<evidence-based reason>
   ```
2. Update `ledger.md` frontmatter `route:` to the new route
3. Update `checkpoint.md` with the new stage expectations
4. Continue from the current stage with the higher route's verification floor

Promotion path: `small → medium → high`. Epic is the ceiling.

### Loop execution flow

```text
clarify
  │
  ▼
plan (medium+)
  │
  ▼
execute ─────────────────────┐
  │                           │
  ▼                           │ (retry if budget remains)
verify ─── fail? ── retry ───┘
  │
  │ budget exhausted?
  │   └── promote route, continue
  │
  ▼
review ─── changes_requested?
  │           │
  │           └── re-execute affected items → back to verify
  │
  │ scope drift?
  │   └── re-plan affected items → back to execute
  │
  ▼ (approved)
ship
  │
  ▼
done (or long-run for high/epic)
```

### Loop break conditions (--loop stops here)

Even under `--loop`, stop and wait for user input when:

- **Irrecoverable blocker**: credential, billing, destructive cleanup, external publish, missing human decision
- **Route already at high/epic and retry budget exhausted**: no more promotion possible
- **Context limit**: write checkpoint, continue next turn (not a hard break)
- **Destructive action**: discard confirmation, force-push — always requires human
- **Consecutive failures with no changed condition**: if the same failure repeats 3 times with identical conditions, stop — this is a signal that something fundamental is wrong

### Loop and artifact state

Under `--loop`, artifacts are the loop state machine. The agent MUST:

1. Update `ledger.md` task status after every attempt (`pending → in_progress → done/blocked`)
2. Update `checkpoint.md` after every attempt with current retry count and route
3. Record retry attempts in `implementation-notes.md` Evidence section
4. Record route changes as Decisions in `implementation-notes.md`
5. Never silently retry — each retry must be recorded with what changed

### Resume after loop break

On resume when `--loop` is still active:

1. Read `checkpoint.md` → `ledger.md` → `implementation-notes.md` Reader Summary
2. If `Status: blocked`, check if the blocker is resolvable
3. If resolvable, resolve it and continue from `Next Action`
4. If not resolvable, report to user and wait

## Strict auto-chain mode

`--auto` implies **strict auto-chain**: one user approval at clarify entry covers the full route sequence through ship summary. Treat any deviation below as a contract violation unless an auto-break condition applies.

### Core ordering rule

**Artifacts before code.** At every stage boundary and during execute:

1. Write or update the stage artifact on disk
2. Update `checkpoint.md` (`Current Stage`, `Status`, `Active Task`, `Next Action`, `Latest Artifacts`, and `Handoff Boundary`)
3. Only then edit application code or invoke the next stage

Never start implementation while `plan.md` is missing, `ledger.md` scaffolds are absent, or `checkpoint.md` still points at a prior stage.

### Stage artifact/tool boundary catalog

Keep stage boundaries explicit. Each stage owns a small artifact set and a narrow tool posture; later stages may read prior artifacts, but they must not silently take over another stage's mutation authority.

- **clarify** — owns `brief.md`, `run-state.json`, `checkpoint.md`, and optional `implementation-notes.md` Decisions entries. Allowed posture: read project context, ask or infer requirements, inspect files for scoping. Forbidden: product code edits, implementation planning beyond route/scope/AC, shipping decisions.
- **plan** — owns `plan.md`, task scaffolds (`implementation-notes.md`, `ledger.md`, `run-state.json` if missing), `checkpoint.md`, and optional `implementation-notes.md` Decisions entries. Allowed posture: read code/artifacts, decompose work, define verification gates. Forbidden: product code edits, review verdicts, branch disposition.
- **execute** — owns product changes within `brief.md`/`plan.md` scope plus `implementation-notes.md`, `ledger.md`, `checkpoint.md`, and verification evidence. Allowed posture: edit in-scope files, run tests/builds/validators, record deviations. Before delegated or parallel work, write the `ledger.md` claim marker and re-read the same row; proceed only if role/scope/timestamp still match. Forbidden: expanding scope without a brief/plan update, approving its own work, merging/shipping, or overwriting another active claim.
- **review** — owns `review-report.md` and standalone provenance artifacts (`input-source.md`, `normalized-input.md`) when applicable. Allowed posture: read artifacts/source, inspect diffs/logs, fetch declared review input, run verification commands. Forbidden: product fixes, branch changes, destructive cleanup, hidden auto-approval. Code findings hand back to execute.
- **ship** — owns `ship-summary.md`, terminal checkpoint state, and selected branch/worktree disposition. Allowed posture: final verification, changelog/handoff checks, explicit merge/PR/keep/discard flow. Forbidden: deleting unrelated dirty files, changing external automation, bypassing unresolved human-review decisions.

If a stage needs an action listed as forbidden for that stage, stop at the boundary, record the blocker or requested handoff in `checkpoint.md`, and invoke the correct next stage instead of doing the work inline. The handoff record must use the same escalation field set as the checkpoint boundary: current owner, next owner / owning next stage, handoff reason, requested/forbidden action, evidence/artifact trigger, blocker/limitation impact, explicit stop condition, and exact artifact update location.

`checkpoint.md` must make ownership transfers explicit in `Handoff Boundary`: current owner, next owner / owning next stage, handoff reason, requested/forbidden action, evidence/artifact trigger, blocker/limitation impact, explicit stop condition, and exact artifact update location. This keeps thin adapters and occasional lead/member work from silently changing which stage owns product edits, review verdicts, or ship disposition.

### Per-stage exit checklist

Complete **all** items before invoking the next stage or editing code outside the current stage scope.

#### clarify → next

| Step | Required before next stage |
|------|---------------------------|
| Artifact | `brief.md` with route, scope, AC, blockers resolved + `run-state.json` with project/storage identity |
| Checkpoint | `Current Stage: clarify` → exit update; `Next Action: invoke /forgeflow:ff-plan` (medium+) or `/forgeflow:execute` (small) |
| Chain | Invoke `forgeflow:ff-plan` or `forgeflow:execute` **immediately** — call the Skill tool when available, or continue with the next stage SKILL.md in Codex App/CLI contexts without that tool. No `(y/n)` prompt; do not print the skill name as text and stop. |
| Forbidden | Starting code edits in the clarify turn; skipping plan on medium/high/epic |

#### plan → execute

|| Step | Required before execute |
|------|------------------------|
| Artifact | `plan.md` + scaffolds: `implementation-notes.md`, `ledger.md`, `run-state.json` if missing |
| **Pre-execution specificity gate** | Verify `brief.md`/`plan.md` contain enough concrete detail. ✅ Pass signals: file paths, issue numbers, camelCase/snake_case symbols, test runner, numbered steps, acceptance criteria, error references, code blocks. ❌ Block: ≤15 effective words + none of the above signals. If blocked, ask user to concretize in-place (do NOT return to clarify). `force:` prefix bypasses this gate. |
| Checkpoint | `Current Stage: plan`; `Active Task: Task 1` (or first pending); `Next Action: begin Task 1` |
| Chain | Invoke `forgeflow:execute` immediately through the adapter-native skill mechanism — no `(y/n)` prompt. Do not just print the skill name. |
| Forbidden | Implementing plan tasks in the plan turn; asking "execute 진행?" under `--auto` |

#### execute → review/ship

| Step | Required before next stage |
|------|------------------------|
| Ledger | Each task row updated incrementally (`pending` → `in_progress` → `done`/`blocked`) — **not** batch-marked at the end |
| Notes | `implementation-notes.md` updated per task (Decisions, Evidence, Deviations) |
| Checkpoint | Updated after **each** task completes; `Active Task` must not stay stale on Task 1 while later tasks finish |
| Evidence | Verification commands run; results in Evidence / Gate Results |
| **Context refresh** | Adapter-neutral by default. After checkpoint, ledger, evidence are written to disk: set `checkpoint.md` `Active Task` to the real next task id and `Next Action` to the next execute step. Under `--auto`, continue unless context pressure is high. If refresh is needed, output adapter-specific hints from `_shared/context-resume.md` and STOP. Do not require a Claude-only fresh-context command in the shared workflow. |
| Chain | `small`: run the small-route self-verify checklist, then invoke `forgeflow:ship` immediately when all checks pass. `medium/high/epic`: invoke `forgeflow:ff-review` immediately when all tasks are done. No `(y/n)` prompt; do not just print the skill name. |
| Forbidden | Deferring ledger/notes until the user asks "어디까지?"; coding after execute exit without the route's required next stage; treating context refresh as a Claude-only mandatory fresh-context step |

#### review → ship

| Step | Required before ship |
|------|---------------------|
| Artifact | `review-report.md` with written verdict |
| Checkpoint | `Current Stage: review`; verdict reflected in `Next Action` |
| Chain | If `approved`: invoke `forgeflow:ship` immediately — call the Skill tool when available, or continue with `skills/ship/SKILL.md` in Codex App/CLI contexts without that tool. No `(y/n)` prompt; do not just print the skill name. If `changes_requested` with artifact-only findings: auto-fix artifacts then re-invoke `forgeflow:ff-review`. **검증**: ship 호출 전 `review-report.md`의 verdict가 `approved`이고 `safe_for_next_stage`가 `yes`인지 확인. |
| Forbidden | "리뷰 통과. ship 진행?" under `--auto`; proceeding to ship when verdict ≠ `approved`; auto-fixing code findings (must stop for code changes) |

#### ship completion

| Step | Required |
|------|----------|
| Artifact | `ship-summary.md` with verification table and handoff |
| Checkpoint | `Current Stage: ship` remains the terminal workflow stage while disposition completes |
| Chain | After summary: **under `--auto`** → default to "Merge locally" and execute merge + worktree cleanup without prompting. **without `--auto`** → present 4-option choice. |
| Allowed stop | merge/PR/keep/discard choice; discard exact confirmation; ship quality loop-back `(y/n)` |

### Prompts forbidden under --auto

Do **not** emit these (or equivalent) while `--auto` is active:

- `다음 스텝으로 /forgeflow:ff-plan을 진행하시겠습니까? (y/n)`
- `계획은 여기까지 확정됐습니다. /forgeflow:execute을 진행하시겠습니까? (y/n)`
- `구현 완료. /forgeflow:ff-review를 진행하시겠습니까? (y/n)`
- `리뷰 통과. /forgeflow:ship을 실행해주세요.` (without immediately invoking ship)
- `execute하고 리뷰해야겠지?` / `ship까지?` — rhetorical checks that wait for user confirmation

Replace with: write artifact → update checkpoint → **invoke the next stage** with the Skill tool or adapter-native Codex App/CLI continuation (or auto-break with blocker record).

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
| Transient error (429, timeout) | Bounded retry (≤2) with backoff; record attempt in `ledger.md` Gate Results |
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
| `ledger.md` / `implementation-notes.md` / `run-state.json` created only when user asks progress | Create scaffolds at clarify/plan exit; update incrementally during execute |
| Review passed but agent waits for "ship까지?" | Invoke `forgeflow:ship` immediately |
| Out-of-scope work (e.g. area tab slider when brief says informational only) without brief update | Auto-break + scope amendment |
| API 429 → unapproved fallback → continue as if AC met | Auto-break or record approved fallback + partial gate; never silent continuation |
| Printing "auto 진행합니다" text but NOT invoking the next stage | Call the Skill tool with exact skill name when available, or continue with the next stage SKILL.md — text output alone is not invocation |
| Asking "(y/n)" when `--auto` is active | Skip prompt and invoke the next stage directly |
| Context pressure while chaining tasks | Save checkpoint/ledger/evidence, output adapter-specific context refresh hint, STOP; otherwise continue under `--auto` |

### Resume after auto-break

When stopping for auto-break:

1. `checkpoint.md` must list `Status: blocked`, concrete `Blockers`, and `Next Action` (single step)
2. Do not edit application code until the user resolves the blocker or explicitly directs otherwise
3. On resume with `--auto` still active: read checkpoint → resolve blocker → continue chain from `Next Action` without re-asking prior stage boundaries

## Context refresh timing during auto-chain

When `--auto` chains multiple stages in one turn, context pressure may trigger adapter-specific context refresh. Follow `_shared/context-resume.md` timing rules, adapted for auto-chain:

| Auto-chain moment | Safe to refresh? | Condition |
|---|---|---|
| After stage artifact + checkpoint written | **Yes** | Both artifact and checkpoint are on disk |
| Mid-execute, task done + evidence recorded | **Yes** | Ledger + notes + checkpoint updated for that task |
| Between stage invocation (next skill loading) | **No** | No artifact written yet for the next stage |
| Mid-review before verdict | **No** | Verdict not recorded |

On resume after context refresh during auto-chain:
1. Read `checkpoint.md` first (see `_shared/context-resume.md`).
2. If `Status: blocked`, treat as auto-break — do not resume chain until blocker is resolved.
3. If `Status: in_progress` and `--auto` is still active, continue chain from `Next Action` without asking the user.

Do **not** use context refresh as an excuse to pause auto-chain and wait for user input. The chain continues automatically unless an auto-break condition applies.

## General rule

If the user explicitly includes any of the flags above, or says to continue through ForgeFlow stages without further approval, treat that as approval for the current bounded ForgeFlow sequence. This only applies inside the stated task scope and never overrides a blocker, failed verification, missing required artifact, or unsafe/destructive action.
