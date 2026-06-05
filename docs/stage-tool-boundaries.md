# Stage Tool Boundaries

ForgeFlow stays markdown-first by treating tools as stage-scoped evidence collectors, not as a shared agent runtime. This catalog makes the default tool posture explicit for each stage while keeping adapter implementations thin.

## Principles

- Stage artifacts are the handoff boundary; chat-only state is not a tool result.
- Use the smallest tool surface that can produce the required artifact or verification evidence.
- If a stage needs an action outside its allowed posture, record the need in the current artifact and hand off to the stage that owns it.
- Adapter-specific capabilities may change how a tool is invoked, but must not change artifact names, route semantics, review verdicts, or human-gate rules.

## Stage-owned role boundaries

Role names describe the lens for a stage-owned pass; they are not a license to create a parallel runtime or bypass the next stage.

- **Planner / spec roles** may clarify intent, derive acceptance criteria, and judge traceability, but must not implement product fixes during plan or review.
- **Worker / execute roles** may mutate scoped product/docs files and collect verification evidence, but must not approve their own work or ship cleanup.
- **Reviewer roles** may inspect, verify, and write review artifacts, but must not repair product code, broaden scope from hidden state, or resolve cross-role conflicts privately.
- **Lead/member splits** are artifact-local coordination only: one lead owns routing/aggregation, each member owns exactly one declared pass/section, and claim markers must be recorded before concurrent work proceeds. Members must not spawn unmanaged child work, reassign roles, broaden scope, or write outside the claimed artifact section; any of those needs a lead-owned artifact update before work continues.
- **Human decision partner** remains outside automated role routing; when risk, weak evidence, or role conflict requires judgment, record a `Human Review Packet` instead of inventing an automated approval path.

## Catalog

| Stage | Allowed tool posture | Must write | Must not do |
|---|---|---|---|
| clarify | Read user request, repo docs, existing project context, git status, and safe discovery commands. | `brief.md`, optional `checkpoint.md` update. | Edit product files, choose implementation details without recording assumptions, or run destructive cleanup. |
| plan | Read `brief.md`, repo docs/code needed for design, adapter config, validation surfaces, and safe discovery commands. | `plan.md`, `ledger.md` planning entries, optional `roadmap.md` for epic. | Implement fixes, mutate dependencies, or mark verification as passed without execution evidence. |
| execute | Read plan/brief, edit scoped product/docs files, run deterministic verification, inspect git diff/status, and update task artifacts. | `implementation-notes.md`, `ledger.md`, `checkpoint.md`, `ship-summary.md` Evidence Manifest section. | Broaden scope without updating artifacts, hide failed commands, perform ship/merge cleanup, or approve its own work as review. |
| ff-review | Read artifacts/source, inspect git status/diff/log, fetch declared inputs read-only, run deterministic verification, and write review-owned artifacts. | `review-report.md`; standalone mode also writes `input-source.md` and `normalized-input.md`. | Fix product code, change branches, mutate PR/issues/CI/deploys, ship/merge, or approve from implementer self-report only. |
| ship | Read review/ship artifacts, inspect git status/diff/log, run final verification, stage explicit intentional paths, commit/merge/PR/cleanup according to recorded decision. | `ship-summary.md`, final `checkpoint.md`/telemetry when applicable. | Clean unknown dirty work, force destructive branch deletion without recorded decision, or bypass unresolved review/human-gate blockers. |
| long-run / benchmark / ff-config | Use read-only or task-local writes needed for their own documented outputs and deterministic validation. | Their documented markdown outputs/config artifacts. | Mutate unrelated pipeline artifacts, product code, or external automation unless that skill explicitly owns the action. |

## Thin Guard (Artifact Invariant Checker)

`scripts/forgeflow_guard_check.py` is an opt-in artifact invariant checker. It may be wired as an adapter hook preflight/post-action check to observe contract violations.

- Tools may collect evidence and report blocking violations via exit code `2`.
- Tools must not assume stage ownership, repair artifacts, or execute stages.
- Guard checks are deliberately shallow: artifact presence, required sections, status/stage consistency. They do not judge code quality, infer routes from prose, or run tests.
- Guard integration is adapter-neutral and opt-in. No adapter is required to wire guard checks, and no guard check may bypass artifact ownership boundaries.

## Review-specific source of truth

Review has the strictest posture because it is an inspection gate. Keep `docs/review-runtime-contract.md#stage-tool-catalog` as the canonical review tool contract; this page summarizes the cross-stage boundary and must not loosen review restrictions.

## Escalation rule

When a role or stage needs a forbidden action, record the same boundary fields that `checkpoint.md` preserves across context refresh:

- current owner (stage/role that hit the boundary)
- next owner / owning next stage (`execute`, `ff-review`, `ship`, or human decision)
- handoff reason
- requested/forbidden action
- evidence or artifact trigger that shows why it is needed
- blocker/limitation impact
- explicit stop condition: whether the current stage must pause, continue with reduced scope, or invoke the owning next stage
- exact artifact update location: the current artifact section that records the handoff (`checkpoint.md` Handoff Boundary, `review-report.md` Evidence Escalation Log, or the stage-owned notes/ledger section)

Then stop that action in the current stage. Do not silently continue with hidden state or side effects.
