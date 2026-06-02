# Review Runtime Contract

ForgeFlow review absorbs the useful part of multi-agent runtimes without becoming an agent OS: adapter separation, role separation, tool-bound review, and evidence-based verification.

This contract is intentionally adapter-neutral. Claude Code, Codex, Gemini CLI, Cursor, GitHub, local diff, and file-bundle entrypoints may differ in how they collect input, but they must hand reviewers the same normalized shape and preserve the same human review gate.

## Goals

- Keep ForgeFlow as a lightweight workflow layer, not a heavyweight team runtime.
- Let multiple harnesses feed review without changing review semantics.
- Make standalone review auditable by recording raw input provenance before judgment.
- Keep automated reviewer roles independent and evidence-backed.
- Prevent review from silently becoming execute, ship, cleanup, or auto-approval.

## Non-goals

- No agent OS, persistent team scheduler, or autonomous task marketplace.
- No full team-mode implementation in review.
- No adapter-specific verdict enums or adapter-owned `review-report.md` variants.
- No code copying from external harnesses; absorb patterns as ForgeFlow-native contracts.

## Adapter-neutral core

The review input contract is exactly:

```yaml
brief:        # what is being reviewed and why
  title: string
  description: string
  source: explicit | inferred

evidence:     # concrete observed or reported material available to review
  items:
    - id: string
      type: diff | file | artifact | url | command_output | reported_summary | missing
      source: string
      fetch_status: success | partial | failed | not_applicable
      content: string | null
      evidence_level: observed | reported | missing
      truncated: boolean
      limitations: string

scope:        # boundaries for review judgment
  files: [string]
  ranges: [string]
  exclusions: [string]
  rationale: string
  scope_source_map: {target: [evidence_id]}

constraints:  # role/focus/risk/user restrictions
  roles: [spec-reviewer | quality-reviewer | architecture-reviewer | security-reviewer | ux-reviewer | perf-reviewer]
  focus: [string]
  user_rules: [string]
  inferred_rules: [string]
  ignored_flags: [string]
```

Markdown artifacts may use prose sections instead of this exact YAML block, but the same four fields must be present in `normalized-input.md` before reviewer judgment begins.

## Input source detection

Standalone review accepts several source classes. Detection must be explicit and recorded in `input-source.md`.

- GitHub PR: original input is PR URL or number; fetch PR metadata, changed files, and diff.
- GitHub commit: original input is commit SHA; fetch commit message, stat, and diff.
- GitHub compare/range: original input is a range; fetch changed files and range diff.
- Other URL: fetch page content and record fetch method/status.
- Repo path/current tree: inspect git status, staged diff, unstaged diff, and recent log if clean.
- Diff/patch text or `.diff` / `.patch` file path: preserve raw diff text and parsed file headers; when the input is a patch file path, record provenance as `file-read:<path>` while scope comes from the diff headers.
- File bundle: read only listed files; missing files are missing evidence, not silently skipped.
- Existing ForgeFlow artifact/task directory: read declared artifacts and referenced files that exist.

Ambiguous input must not be forced into a convenient source type. If the input cannot be classified, standalone review is blocked or asks for clarification.

## Thin adapter responsibilities

Each adapter may do only these things:

1. Detect the input type and original source.
2. Fetch raw evidence using a recorded command, API, or source label.
3. Normalize raw evidence to `brief / evidence / scope / constraints`.
4. Write provenance to `input-source.md`.
5. Write normalized review input to `normalized-input.md`.
6. Invoke the canonical review skill using the normalized artifacts.

Adapters must not:

- auto-approve findings or change verdicts
- rewrite reviewer role routing after normalization
- hide fetch failures behind fallback content
- synthesize evidence that was not fetched or provided
- create adapter-specific ownership paths for `review-report.md`
- mutate product files to fix findings
- bypass the human review gate
- introduce new stage names or verdict enums

### Adapter compliance checklist

Before invoking the canonical review skill, every adapter must leave an auditable handoff that answers these questions in markdown:

- **Source classified**: which input source class was detected, and why other plausible classes were not used when ambiguous.
- **Fetch reproduced**: the exact command, API label, or tool/source label used to obtain each evidence item.
- **Fetch posture constrained**: every evidence fetch is recorded as read-only, verification-only, or not-applicable; any state-changing remote/API action or product mutation during evidence fetch fails the handoff.
- **Normalization complete**: `brief`, `evidence`, `scope`, and `constraints` are all present in `normalized-input.md`.
- **Limitations visible**: every failed, partial, missing, or truncated fetch is recorded as an evidence item with `evidence_level: missing` or an explicit truncation note.
- **Review ownership delegated**: the adapter hands off to the canonical review skill and does not keep a parallel verdict, report file, or hidden approval path.

If any checklist item cannot be satisfied, the adapter should still write `input-source.md` and `normalized-input.md`, but the review verdict must be `blocked` unless a human explicitly narrows the scope and records the limitation.

## Provenance artifacts

Standalone review creates a synthetic task directory:

```text
.forgeflow/tasks/standalone-<YYYYMMDD-HHMMSS>/
├── input-source.md
├── normalized-input.md
└── review-report.md
```

`input-source.md` should be created from `templates/input-source.md` and must include:

- detected input type
- source classification rationale: the concrete signal used, plausible alternate source classes considered, and whether ambiguity was resolved or blocked
- original user input
- adapter or tool used to fetch input
- commands/API labels executed, when available
- access posture for each fetch (`read_only`, `verification_only`, or `not_applicable`) plus a mutation check proving the fetch did not comment, approve, label, dispatch CI, deploy, write product files, change branches, or perform destructive cleanup
- fetch status: `success`, `partial`, `failed`, or `not_applicable`
- missing or truncated evidence notes
- an Evidence Source Map that ties each normalized evidence ID to its fetch command/API/source label, normalized evidence type, fetch status, evidence level, and integrity
- timestamp or run label

`normalized-input.md` should be created from `templates/normalized-input.md` and must include:

- `brief`: explicit or inferred review target
- `evidence`: each evidence item with a stable, unique evidence ID, source, fetch status, evidence level, and truncation/missing-evidence limitation note; its type/status/level must match the corresponding `input-source.md` Evidence Source Map row, and IDs must not be reused for different content
- `Evidence Gap Register`: every expected evidence class that is missing, partial, sampled, truncated out of trigger visibility, or blocked by fetch/auth/tool failure, with expected source, affected normalized field, affected reviewer roles, disposition (`blocked`, `limited`, or `not_applicable`), and reason; write `none` only when no known gap exists
- `scope`: files/ranges/content boundaries reviewed, plus a `scope_source_map` tying every in-scope file, range, or content bound back to normalized evidence IDs or an explicit blocked/missing scope-evidence note
- `constraints`: role, focus, exclusions, user rules, inferred rules, and any ignored adapter/user flags such as `--focus` losing to `--type`
- `role trigger matrix`: every supported reviewer role marked `run`, `skipped`, or `blocked`, with the normalized evidence ID(s), route rule, explicit flag, or explicit non-trigger signal that made the routing decision
- `role evidence map`: every active reviewer role mapped to the evidence IDs it may use, or `none — <reason>` when blocked/not triggered
- Role routing consistency: every role listed in `constraints.roles` must be `run` or `blocked` in the role trigger matrix and must have either allowed evidence IDs or an explicit blocked rationale in the role evidence map; a role marked `run` must not be absent from `constraints.roles`.
- `evidence integrity check`: every evidence ID cited by `constraints.roles`, the role trigger matrix, role evidence map, `scope_source_map`, or role input packets must resolve to exactly one normalized evidence item and to a matching `input-source.md` Evidence Source Map row for source, type, fetch status, and evidence level; missing, duplicated, mismatched, or stale references block reviewer judgment until corrected or explicitly limited
- `role input packet readiness`: every active, blocked, or skipped reviewer role marked `READY`, `BLOCKED`, or `SKIPPED` based on whether trigger decision, evidence IDs, scope, constraints, limitations, and packet freshness are normalized before judgment; readiness must be refreshed after any Evidence Escalation Log entry, new evidence item, scope change, constraint change, or role-routing change
- `role input packets`: for every `READY` or `BLOCKED` role, the exact trigger, evidence IDs, scope, constraints, limitations, and packet freshness handed to the role, copied from normalized fields rather than chat memory or hidden adapter state
- `role capability hints`: optional advisory model/profile/tooling hints per reviewer role, recorded only for auditability; they must use capability language rather than provider-specific requirements and must not affect routing, evidence IDs, evidence levels, verdict enums, approval rules, or the human review gate
- `review ownership plan`: the lead reviewer, any member assignments, aggregation owner, claim marker integrity, child-work policy, conflict policy, and product-mutation policy recorded before delegated or parallel reviewer passes start
- `adapter handoff checklist`: source classified, fetch reproduced, normalization complete, limitations visible, and canonical review ownership recorded as `PASS`/`FAIL` before reviewer judgment begins

`review-report.md` remains the single review result artifact. Adapter-specific reports are not allowed.

### Evidence escalation log

If a reviewer role needs material that is not already present in the role evidence map, it must pause judgment and record an evidence escalation before using that material. The lead reviewer either adds a new normalized evidence item and mirrors its provenance in `input-source.md`, or marks the request unavailable and records the affected role as blocked/limited. The escalation record lives in `review-report.md` and includes requester role, requested evidence, reason, action taken, resulting evidence ID or blocked rationale, and approval impact.

Reviewer roles must not satisfy evidence gaps from chat memory, hidden adapter state, or unrecorded file reads. This keeps parallel role passes auditable and prevents member reviewers from silently expanding scope after normalization.

## Role separation

Reviewer roles are independent lenses:

- `spec-reviewer`: checks traceability to brief, acceptance criteria, intended behavior, and planned scope.
- `quality-reviewer`: checks maintainability, simplicity, verification quality, and residual risk.
- `architecture-reviewer`: checks existing pattern compliance, shared-module reuse, unnecessary new implementations, layer/dependency consistency, public contracts, and project-level architectural rules.
- `security-reviewer`: checks auth, authorization, secrets, input validation, dependency, filesystem, and network boundaries.
- `ux-reviewer`: checks user-facing text, flows, accessibility, forms, loading/error states, and interaction clarity.
- `perf-reviewer`: checks query patterns, loops, batching, caching, memory pressure, and large-data behavior.

A role finding must cite:

- reviewer role
- checklist source and exact checklist version used
- confidence
- criteria basis
- evidence source
- evidence level
- severity and priority
- side effect of the proposed remediation
- disposition and disposition rationale when applicable

Every role pass, including passes with zero findings, must leave a compact role-pass record in `review-report.md` so the lead can audit what was inspected without reading chat logs. The record includes active role, markdown claim marker (`role=<reviewer> scope=<artifact section/evidence IDs> at=<ISO8601>`), checklist version, reviewed scope/evidence IDs, verification command(s) observed or reason none ran, limitations, an Independence Check that fails if implementer self-report or chat-only claims substituted for normalized/observed evidence, finding counts, and the role verdict. Chat-only role completion claims are not sufficient evidence.

Before each role starts, the lead reviewer provides a role input packet from `normalized-input.md` only: trigger decision, allowed evidence IDs, scoped files/ranges/exclusions, scope source map IDs, constraints/focus flags, visible limitations, applicable Evidence Gap Register entries, and packet freshness relative to the latest evidence/scope/constraint/routing state. `normalized-input.md` records both the role input packet readiness row (`READY`, `BLOCKED`, or `SKIPPED`) and the concrete packet row for each READY/BLOCKED role; the role-pass record echoes that packet status and cited evidence IDs. If the packet is missing, stale, `BLOCKED`, or depends on hidden adapter state, that role is blocked until the evidence is normalized or recorded unavailable. The role summary also cites the normalized conflict policy so delegated reviewers know unresolved cross-role conflicts remain visible and route to the Human Review Gate rather than being resolved in chat.

Reviewer roles may cite only normalized evidence IDs from the role evidence map unless they first update `normalized-input.md` with a new evidence item and visible limitation note. Chat-only context, unrecorded web pages, or ad-hoc file reads are not valid role evidence.

Cross-role conflicts stay visible. The report must keep both findings, mark the conflict as requiring human decision, and avoid silently choosing a winner.

## Role routing rules

- Pipeline `small`: quality-reviewer with fast-review depth unless risk triggers escalation.
- Pipeline `medium`: quality-reviewer; medium-full may add spec-reviewer when contract-first traceability exists.
- Pipeline `high`/`epic`: spec-reviewer pass before quality-reviewer pass; quality does not run until spec is approved.
- Standalone default: quality-reviewer always runs; spec-reviewer runs when a brief/spec exists or can be inferred; architecture/security/ux/perf run when requested or triggered by scoped evidence.
- `--type <role>` narrows to the specified reviewer role.
- `--type all` runs all reviewer roles.
- `--focus <role>` is an alias unless `--type` is also present; `--type` wins and the ignored focus is recorded.

Adapter source must never override these routing rules after normalization. The canonical `review-report.md` records both `Active roles` and `Skipped roles`; every skipped supported role needs a reason such as route depth, `--type` narrowing, file-type non-trigger, or unavailable evidence. Silent omission of a role is treated as an incomplete routing record. Architecture, security, UX, and performance roles may be triggered only from normalized evidence or an explicit user flag; if the apparent trigger exists only in chat context or was lost to truncation/fetch failure, record `blocked` or `skipped — missing trigger evidence` in the role trigger matrix rather than broadening review scope invisibly.

## Role model hints

Harnesses that can choose models per role may use capability-based role model hints, but they remain adapter hints rather than review semantics:

- spec-reviewer, architecture-reviewer, security-reviewer, and cross-role conflict aggregation prefer the strongest reasoning available.
- quality-reviewer can use a standard reasoning/coding model, escalating to strongest reasoning for broad refactors, weak verification, or many interacting files.
- architecture-reviewer should use the strongest reasoning available when normalized evidence includes module-boundary, public-contract, dependency-direction, or broad-refactor risk.
- ux-reviewer and perf-reviewer can use a standard reasoning model unless normalized evidence shows accessibility, query-planning, caching, or large-data risk that needs specialist depth.

Adapters may record non-default role/model assignments in adapter notes or role-pass records for auditability. Model choice must not change role routing, role evidence maps, evidence levels, verdict enums, approval rules, or the human review gate. There is no central model database in the review contract.

When the assignment is known before reviewer judgment, record it in `normalized-input.md` under `role capability hints` so the lead and member reviewers share the same advisory profile map. Leave roles as `not_applicable` when the harness has no per-role model/profile selection. A missing or provider-neutral hint is not a review blocker; a hint that changes route/evidence/verdict semantics is a contract violation.

## Stage tool catalog

Review is an inspection gate. The preferred tool surface is read-only or verification-oriented.

Allowed in review:

- read artifacts and source files
- inspect git status, diff, log, and changed-file lists
- fetch declared external input through read-only commands, APIs, or web extraction
- run deterministic verification commands such as tests, lint, typecheck, build, or docs validators
- write review artifacts only: `input-source.md`, `normalized-input.md`, `review-report.md`, telemetry, checkpoint updates required by the review skill

Not allowed in review:

- implement product fixes
- mutate remote systems through issue comments, PR reviews, approvals, labels, CI dispatch, deploys, or state-changing API calls
- mutate unrelated project state
- perform destructive cleanup
- change branches or release artifacts
- ship or merge
- hide failing verification behind a passing summary
- approve based only on implementer self-report

If a finding requires code changes, report it and hand back to execute.

## Evidence levels

- Observed evidence: directly inspected file content, diff, artifact, or command output from the current review turn.
- Reported evidence: executor notes, CI summaries, previous agent claims, user summaries, or ledger claims not independently rerun.
- Missing evidence: required artifact, diff, source, or verification command could not be obtained.

Approval-grade review requires observed evidence for at least one relevant verification gate unless the report explicitly records why no such gate exists.

Evidence rules:

- Never convert reported evidence into observed evidence.
- Never invent paths, commands, test results, or changed files.
- If evidence is truncated, mark what was omitted and why.
- If a fetch fails, keep the failure visible and classify the affected review area as blocked or weakly evidenced.
- If command execution is unavailable, use manual-inspection language and do not claim the command passed.

## Finding and verdict contract

`review-report.md` uses the canonical verdict enum:

- `approved`
- `changes_requested`
- `blocked`

Do not use adapter-specific labels such as `passed`, `LGTM`, `success`, or `merged` as the verdict.

Approval requires:

- no unresolved blocker findings
- no required artifact missing without explicit not-applicable rationale
- at least one relevant observed verification gate or a documented reason no gate exists
- human review gate recorded as `skipped` with rationale or `required` with the human decision recorded
- `safe_for_next_stage: yes`

`blocked` is required when:

- the input cannot be fetched or classified
- required evidence is missing enough to hide scope or risk
- required verification fails or cannot be interpreted
- role conflicts require a human decision before automated approval

## Human review gate

Automated role review is not the final authority for high-risk decisions. Human review is a separate decision-partner gate after automated findings.

Human review is required for:

- public API, CLI, workflow, or artifact-schema changes
- authentication, authorization, secrets, permissions, or security-boundary changes
- data persistence, deletion, migration, or state-machine changes
- dependency or lockfile changes
- broad ownership boundaries, hard rollback, or unclear impact
- unresolved cross-role conflicts
- accepted p1/p2 risk rather than fixed p1/p2 risk
- weak or missing approval-grade evidence

When required, `review-report.md` must include a Human Review Packet with the decision needed, context, automated evidence, recommended discussion prompts, and handoff target.

## Minimal team-mode absorption

ForgeFlow may borrow team-mode concepts only as guardrails:

- role separation is allowed; persistent autonomous team runtime is not part of review
- task claiming may be documented for future parallel execution, but review itself owns only the review artifact
- subagents or reviewers must not recursively create unmanaged child work
- markdown artifacts remain the state boundary
- final judgment stays in `review-report.md` plus the human gate, not in agent chat summaries

### Lead/member guardrails

When a future adapter or operator maps review work onto multiple agents, keep the split declarative and artifact-bound:

- **Lead role**: owns input normalization, role routing, aggregation into `review-report.md`, cross-role conflict visibility, and the final human-gate recommendation.
- **Member role**: owns exactly one delegated reviewer pass or evidence-gathering pass and writes only the assigned artifact/section. Members must not create new task directories, launch additional members, change route selection, or mutate product files.
- **Claim marker**: if concurrent review passes are used, record the claimed role and target section in markdown before work starts (for example, in `review-report.md` draft notes or a task-local checkpoint) using `role=<reviewer> scope=<artifact section/evidence IDs> at=<ISO8601>`. Claim markers must be unique per member assignment and read back from the artifact before delegated work proceeds; duplicate or unreadable markers block the member pass. The final role-pass record preserves that marker. Do not rely on chat-only claims.
- **Ownership plan**: standalone normalization records the lead reviewer, member assignments, aggregation owner, claim marker integrity, no-child-work policy, conflict policy, and product-mutation policy in `normalized-input.md` before any delegated/member pass starts. The report cites that plan so aggregation can be audited without chat logs and unresolved disagreements stay visible for the human gate.
- **Merge rule**: unresolved disagreement between members is recorded as a cross-role conflict. The lead aggregates; it does not silently override member findings.
- **Non-goal**: this is not a team scheduler, persistent queue, or autonomous task marketplace. It is a safety boundary for occasional parallel reviewer passes.

## Change requirements

Any future change to review adapters, standalone input handling, role output, tool permissions, or verdict handling must update these surfaces together:

1. `docs/review-runtime-contract.md`
2. `skills/ff-review/SKILL.md`
3. `templates/review-report.md` if report fields change
4. `README.md` if user-visible behavior changes
5. `scripts/validate_advisory_contract.py` for exact contract literals
6. `CHANGELOG.md`

Run at least:

```bash
make validate-advisory-contract validate-markdown-links validate
```

## Completion checklist

A review runtime contract change is complete only when:

- adapters remain thin over the normalized input contract
- role routing and role finding requirements are documented
- evidence levels are enforced in the review skill/report surface
- review tool permissions distinguish read-only verification from execute mutation
- README exposes the user-facing contract location
- local validation passes
