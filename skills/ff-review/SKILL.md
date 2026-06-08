---
name: ff-review
description: Perform independent ForgeFlow review. Use as /ff-review or /forgeflow:ff-review — either after execute (pipeline mode) or directly with external input (standalone mode). Also use when the user says 'review this', 'audit changes', 'check implementation', 'code review', review 해줘, or 'review PR' in a ForgeFlow context. Not for grammar checks, syntax lookups, or simple correctness questions.
version: 0.6.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must separate findings by reviewer role (spec, quality, architecture, security, ux, perf).
  Must not approve work with unresolved blockers or missing verification evidence.
  Must apply applicable review rubric (Spec Review or Quality Review) per role.
  Must handle standalone mode input detection (URL, repo, diff, files) and synthetic task directory bootstrapping.
  Must enforce evidence discipline — every finding must cite observed evidence, not inference.
  Must run artifact completeness gate before starting review.
  Must apply 7-angle deep code analysis for quality-reviewer when diff/code input is available.
  Must verify each finding as CONFIRMED or PLAUSIBLE before including in review report.
  Must run plan conformance gate in pipeline mode — every plan task traced to execution evidence before approval.
dependencies:
  - skills/_shared/discipline.md
  - skills/_shared/isolation.md
  - skills/_shared/preflight.md
  - skills/_shared/automation.md
  - skills/_shared/context-resume.md
---

# Review

Use this skill to review completed ForgeFlow work independently.

## Reference inventory

- [references/standalone-mode.md](references/standalone-mode.md) — standalone input detection, synthetic task bootstrap, and scope constraints.
- [references/input-normalization.md](references/input-normalization.md) — normalization gate and evidence/source mapping.
- [references/role-checklists.md](references/role-checklists.md) — reviewer role rubrics and checklist criteria.
- [references/pipeline-procedure.md](references/pipeline-procedure.md) — post-execute review flow and artifact trace procedure.
- [references/consensus-and-drift.md](references/consensus-and-drift.md) — multi-model consensus review and quantitative drift detection.

## Input

Review supports two entry modes. The detected mode determines which artifacts and evidence are available.

### Post-execute mode (pipeline)

Review after execute stage. Requires pipeline artifacts from the resolved task directory (`~/.forgeflow/projects/<project-slug>/tasks/<id>/` by default):
- `brief.md` from clarify stage
- `plan.md` from plan stage
- `implementation-notes.md` from execute stage
- `ledger.md` from execute stage
- `ship-summary.md` Evidence Manifest section from execute stage (required — missing Evidence Manifest → `blocked` verdict)
- `implementation-notes.md Decisions` from clarify/plan/execute stages (optional but recommended for tracing prior decisions)
- Final codebase state
- Verification commands/results

> **High/epic dual review**: For `high` and `epic` routes, auto-chain runs review twice: first as `spec-reviewer` (spec compliance), then as `quality-reviewer` (code quality). Each pass writes its own findings. See `_shared/automation.md` → Chain sequence by route.

### Standalone mode

Review without prior pipeline artifacts. Accepts external input directly:
- **URL** — PR diff, commit range, or any web page
- **Repo snapshot** — Local directory structure listing
- **File bundle** — Explicit file paths to review
- **Git range** — Commit range (e.g., `main..feature`)

When in standalone mode, set `evidence_source` in `normalized-input.md` to record the input origin (e.g., `gh pr diff 42`, `git diff main..feature`, `file-read: src/api/auth.ts`). Scope is always explicit — default: changed files only.

### Input type matrix

| Input Source | Artifact | Evidence | Scope |
|---|---|---|---|
| Post-execute | implementation-notes.md | ledger.md | plan.md scope |
| URL (PR diff) | diff URL | diff hunks | changed files |
| Repo snapshot | directory structure | file listing | specified paths |
| File bundle | file list | file contents | specified files |
| Git range | commit range | diff output | changed paths |

## Standalone Mode

When review is invoked without prior clarify/plan/execute stages — no resolved task directory with pipeline artifacts — it operates in **standalone mode**. The review becomes an independent inspection gate.

Full standalone mode procedure (input type detection, synthetic task directory bootstrapping, constraints): **read `references/standalone-mode.md` before executing standalone review**.

## Input Normalization

For standalone input, normalize to `brief / evidence / scope / constraints` before reviewer judgment. Write the result to `normalized-input.md` and complete the `normalization gate`.

Read `skills/ff-review/references/input-normalization.md` when classifying standalone input, fetching evidence, deriving scope, handling `--scope`, applying `--type` or `--focus`, or filling normalization gate fields. Do not approve a review when `brief_present`, `evidence_present_or_blocked`, `scope_explicit`, `constraints_explicit`, or `limitations_visible` is `FAIL`.

## Runtime contract

ForgeFlow review follows `docs/review-runtime-contract.md`. Load that document before changing review routing, standalone input handling, role output, tool permissions, evidence handling, or adapter behavior.

Contract obligations:
- Adapters are thin: detect input, fetch raw evidence, normalize to `brief / evidence / scope / constraints`, write `input-source.md` and `normalized-input.md`, then invoke canonical review.
- `normalized-input.md` must include stable evidence IDs and a role evidence map so reviewer roles cite only normalized, provenance-visible material.
- Adapter handoff must satisfy the contract's Adapter compliance checklist: source classified, fetch reproduced, fetch ledger complete for multi-fetch evidence, fetch posture constrained, normalization complete, limitations visible, and review ownership delegated to the canonical review skill.
- Evidence fetch provenance must include a read-only/verification-only access posture and mutation check; any state-changing fetch path blocks approval unless a human records a narrowed, safe scope.
- Adapters must not change verdict enums, auto-approve findings, hide fetch failures, rewrite role routing, create adapter-specific `review-report.md` ownership, or mutate product files.
- Reviewer roles remain independent. Every finding must cite role, confidence, criteria basis, evidence source, evidence level, priority/severity, side effect, and disposition state when applicable.
- Cross-role conflicts stay visible and require human decision; do not silently pick a winner.
- Review is read-only except for review artifacts, telemetry, and checkpoint updates required by the review skill. If code changes are needed, hand back to execute.
- Approval-grade review requires observed evidence for at least one relevant verification gate unless `review-report.md` explicitly records why no such gate exists.
- If multiple agents are used for reviewer passes, apply the contract's lead/member guardrails: one lead aggregates and owns final `review-report.md`; each member owns exactly one assigned pass/section, records a markdown claim marker, does not spawn unmanaged child work, and does not mutate product files.
- Evidence gaps discovered by reviewer roles must go through the Evidence Escalation Log; new evidence is usable only after it is normalized with provenance, otherwise the role records blocked/limited judgment.

### Review tool posture

Review is an inspection gate, not a repair stage. Allowed actions are limited to reading artifacts/source, inspecting git status/diffs/logs, fetching declared review input through read-only commands, APIs, or web extraction, running deterministic verification commands, and writing review-owned artifacts (`input-source.md`, `normalized-input.md`, `review-report.md`, telemetry, and checkpoint updates required by this skill).

Forbidden actions include product fixes, branch changes, destructive cleanup, release/ship mutations, remote mutations such as issue comments, PR reviews, approvals, labels, CI dispatch, deploys, or state-changing API calls, hiding failed verification behind a passing summary, and approving solely from implementer self-report. If a finding requires code or product changes, record the finding and hand it back to execute instead of fixing it during review.

## Reviewer Roles

Standalone mode and high/epic pipeline mode use role-based review. Each role has its own checklist and produces findings independently. The review report aggregates all role findings.

### Role routing and output

Read `skills/ff-review/references/role-routing.md` before selecting roles, assigning role/model hints, applying specialist profiles, handling cross-role conflicts, or writing role-pass records. Read `skills/ff-review/references/role-checklists.md` before executing any role pass and cite the exact `Checklist version: YYYY-MM-DD` value in `review-report.md` as `Checklist Version`.

Before running roles, write a compact role routing rationale in `review-report.md`: list `Active roles` and `Skipped roles` explicitly. In standalone mode, also fill `normalized-input.md` → `Role trigger matrix` before any role begins. Missing role input packets, `BLOCKED` readiness rows, chat-only role completion claims, or chat-only trigger evidence block the role instead of allowing inferred evidence. If trigger evidence is absent, record `skipped — missing trigger evidence` or `blocked`; this prevents silently broadening or narrowing review scope.

Supported roles: `spec-reviewer`, `quality-reviewer`, `architecture-reviewer`, `security-reviewer`, `ux-reviewer`, and `perf-reviewer`. `quality-reviewer` always runs in standalone mode; `spec-reviewer` runs when requirement/spec evidence exists; architecture/security/ux/perf run only from explicit `--type`/`--focus` or normalized trigger evidence.

### Role routing

Pipeline and standalone role routing details live in `references/role-routing.md`. Human review is a separate decision-partner gate, not an automated reviewer role. Apply the Human Review Gate below after automated review has produced `review-report.md`.

## Human Review Gate

After automated review, classify whether a human decision-partner review is required. Apply `docs/review-model.md` and read `skills/ff-review/references/human-review-gate.md` before marking Human Review Gate as `required` or `skipped`, especially when API/CLI/schema, state/data, security, dependency, config/deploy, business-rule, cross-module contract, p1/p2 risk-acceptance, weak evidence, or cross-role conflict signals exist.

When required, append a Human Review Packet to `review-report.md`; when skipped, record the skip reason and make it explicit that automated review is the final review gate for this task.

## Output Artifacts

Write `review-report.md` (schema: review-report/v2, from `templates/review-report.md`) to the active task directory. The report must capture:

- Review Type (spec | quality | architecture | security | ux | perf — or list multiple for standalone)
- Verdict (approved | changes_requested | blocked) — never use "passed"
- **Blocker Enforcement Rule:** `approved` verdict is allowed **only** when Open Blockers is empty. If any blocker finding exists, verdict must be `changes_requested` or `blocked`. There is no "minor blocker" category — a finding classified as blocker is a blocker regardless of perceived severity. Reviewer may reclassify a finding from blocker to major before verdict, but may not leave a blocker open and still give `approved`.
- Reviewer (role or identifier)
- Findings with severity (blocker | major | minor | nit), priority (p1 | p2 | p3 | p4), category (spec-compliance | quality | maintainability | risk | security), Criteria Basis, Evidence Source, Evidence Level (`observed | reported | missing`), Side Effect, Why This Remediation, Disposition, and Disposition Rationale when needed
- Reviewer Role Summary with checklist source, exact `Checklist Version`, evidence requirements source, per-role verdict counts, and cross-role conflict count when role-based review runs
- Review ownership plan citation with lead reviewer, member assignments, aggregation owner, child-work policy, and product-mutation policy when standalone or delegated review runs
- Role-pass records for every active role, including zero-finding passes, with markdown claim marker, inspected scope/evidence, observed verification or no-command rationale, limitations, Independence Check, finding counts, and role verdict
- Spec Compliance checklist (for spec review)
- Quality Assessment checklist (for quality review)
- Open Blockers (list or "none")
- Human Review Gate (`required | skipped`) and decision rationale
- Human Review Packet when a human decision is required
- Safe for Next Stage (yes | no)
- Harness Follow-up (`none | eval-needed | skill-rule-needed | template-needed | docs-needed`) with reason and suggested artifact when the review exposes a repeatable harness gap
- Next Action
- Approved By (only if verdict is approved)

**Small route fast-review exception**:
- Keep the same `review-report.md` file and verdict enum, but use a compact report.
- Hard output cap: target ≤ 80 lines for approved small reviews with no findings.
- Required sections only: Reader Summary, Review Type, Verdict, Reviewer, Route Compliance, Findings (or `none`), Evidence Classification, Open Blockers, Human Review Gate, Safe for Next Stage, Next Action, Approved By, Residual Risks.
- Omit or mark `not_applicable`: Reviewer Role Summary, Spec Compliance, Execute Micro-Gates, Human Review Packet, Harness Follow-up, Evolution Rule Review, Code Quality Metrics, Override Log, Standalone sections, Specialist Assertions.
- Do **not** use Markdown tables in small fast-review. Use bullets only.
- Do not expand every quality rubric item into prose when no finding exists. Record a single line: `Quality Assessment: PASS — smallest safe change, verification acceptable, no blocker found`.
- Target: finish review in one focused pass with one observed verification command unless risk triggers escalation.

**Pipeline mode only**:
- Evolution Rule Review (not_applicable — evolution rules are generated by ship)
- Execute Micro-Gates table (high/epic — summarize `micro_spec` / `micro_quality` from execute; re-verify in this pass)
- Route Compliance

**Standalone mode only**:
- Standalone Input Source (type, original input, fetch status, fetched_at/run label, freshness status, access posture, mutation check, Fetch Method Ledger references, Evidence Source Map references, Adapter Handoff Checklist statuses)
- Reviewer Role Summary (per-role verdict and finding count)
- Override Log (human overrides)
- Standalone Mode Metadata

## Review Rubrics

These rubrics are applied directly during review. Separate spec and quality reviews use their respective rubrics.

### Scope Boundary Verification

Review 시 scope_boundary 위반을 탐지하고 advisory를 발행합니다.

#### Verification procedure

1. **Read scope_boundary from brief.md**: Extract `files_planned`, `files_limit`, and `boundary_status` from brief.md YAML frontmatter.
2. **Identify actually modified files**: Use `git diff --name-only` (or equivalent) to get the list of files actually changed during execute.
3. **Compare planned vs actual**:
   - `files_in_scope`: files that were in the planned scope (brief.md scope_files)
   - `files_out_of_scope`: files modified but NOT in the planned scope
4. **Route threshold check**: Verify that the total modified file count does not exceed the route threshold (small ≤3, medium ≤8, high ≤20, epic unlimited).
5. **Record violations**: For each out-of-scope file, record `file` path and `reason` (why it is out of scope).

#### Advisory issuance

- If `files_out_of_scope > 0`: Issue a **major** finding with category `spec-compliance`, description "scope creep 의심: N files modified outside planned scope", listing each violating file.
- If total modified files exceed route threshold: Issue an advisory "scope split 권장 — route 임계값 초과" in findings.
- If boundary is clean (no violations): Record `scope_boundary.violations` as empty in review-report.md.

#### review-report.md scope_boundary field

Write the scope_boundary verification results to review-report.md YAML frontmatter:
```yaml
scope_boundary:
  files_in_scope: <!-- N -->
  files_out_of_scope: <!-- N -->
  violations:
    - file: <!-- path -->
      reason: <!-- why out of scope -->
```

This field is mandatory for pipeline mode reviews. For standalone mode, scope_boundary may be omitted.

### Spec Review

Questions to answer for every spec review:
- Did the output satisfy the brief objective?
- Were acceptance criteria met?
- Does the implementation reflect the `plan.md` Design Intent rather than merely touching the named files?
- Were task-specific Review Criteria applied, including relevant coding conventions, ADRs/decisions, active rules, and risk checks?
- Did execution stay inside scope?
- Did the change avoid silent fallback, dual write, or shadow-path ownership drift?
- Is evidence sufficient for the claimed completion?

Automatic fail conditions:
- Missing acceptance coverage
- Missing or ignored Design Intent / Review Criteria for medium/high/epic pipeline reviews
- Unapproved scope drift
- Silent fallback or dual-write drift
- Evidence-free completion claim
- Approved verdict with open blockers or safe_for_next_stage=false → **Blocker Enforcement Rule 위반** (see Verdict field rule above)

### Finding discipline

For each finding, reviewers must make the recommendation auditable and decision-ready:

1. Assign both **Severity** and **Priority**:
   - `p1`: must fix before ship; usually blocker/major with high confidence.
   - `p2`: strongly recommended before ship or requires human risk acceptance.
   - `p3`: recommended improvement; may ship with documented residual risk.
   - `p4`: minor/nit; never blocks by itself.
2. Fill **Criteria Basis** with the exact source that makes the finding valid: `plan.md` Design Intent/Review Criteria, `brief.md` acceptance criterion, `docs/coding-convention.md`, ADR/decision doc, active evolution rule, or directly observed runtime evidence.
3. Fill **Side Effect** for the remediation. Use `none` only when the change is truly side-effect free.
4. Fill **Why This Remediation** with the tradeoff rationale. Do not issue bare edit commands.
5. Set **Disposition**:
   - During initial review: `pending`.
   - After reflection/re-review: `accepted`, `rejected`, `risk_accepted`, or `fixed`.
   - `rejected` and `risk_accepted` require **Disposition Rationale** and should usually trigger the Human Review Gate unless the risk is p3/p4 and low-impact.
6. Do not invent criteria after the fact. If no basis exists but the concern is real, record it as advisory and recommend adding criteria in a future plan/evolution rule.

### Quality Review

Questions to answer for every quality review:
- Is the result simple enough?
- Is the verification quality acceptable?
- Are residual risks documented?
- Is maintainability acceptable for the task size?
- Was this the smallest safe change without alternate ownership paths?
- **Are there line-level bugs?** Apply deep code analysis (see `references/deep-code-analysis.md`) when diff/code input is available. Metrics alone miss inverted conditions, off-by-one, and cross-file breakage.

Automatic fail conditions:
- Avoidable complexity
- Weak verification
- Hidden residual risk
- Shadow-path ownership drift
- Approved verdict with open blockers or safe_for_next_stage=false → **Blocker Enforcement Rule 위반** (see Verdict field rule above)
- CONFIRMED correctness finding from deep code analysis

### Code Quality Metrics (quantitative)

Extract metrics from `implementation-notes.md` → Metrics section (populated during execute). If missing, collect directly:

| Metric | Collection Command | Blocker Threshold |
|--------|-------------------|-------------------|
| TypeScript errors | `npx tsc --noEmit 2>&1 \| grep -c "error TS"` | > 0 |
| Type assertions | `grep -r "as " src/ --include="*.ts" --include="*.tsx" \| wc -l` | Review judgment |
| Debug artifacts | `grep -rE "console\.log\|TODO\|FIXME\|debugger" src/ ... \| wc -l` | > 0 |
| Max component LOC | `for f in src/**/*.tsx; do wc -l "$f"; done` | > 150L → major |
| Log volume | Size of agent output | Codex > 100KB → normalize |

Record in `review-report.md` → Code Quality Metrics section. Metrics exceeding blocker thresholds generate automatic findings.

## Closed Loop — Re-Execution Condition Generation (L6)

When review verdict is `changes_requested` or `blocked`, write re-execution conditions into `checkpoint.md` under the `## Re-Execution Conditions` section (see `templates/checkpoint.md`). Use `skills/ff-review/references/re-execution-conditions.md` for failure analysis, corrected execution conditions, rollback instructions, Memory Bank recording, auto/manual handling, and the 3-cycle safety limit.

## Multi-model Consensus and Drift Detection

→ Full rules: [`references/consensus-and-drift.md`](references/consensus-and-drift.md).

Summary:
- **Multi-model consensus**: Optional for high/epic via `defaults.md` `consensus_review: true`. Primary + secondary reviewer; disagreements surfaced in review-report.md.
- **Drift detection**: Quantitative `drift_score = goal_drift*0.5 + constraint_drift*0.3 + scope_drift*0.2`. Thresholds: ≤0.2 minimal, 0.2-0.4 moderate, >0.4 significant. Recorded in review-report.md → Drift Analysis.

## Exit Condition

**Pipeline mode**:
- Requirements/acceptance criteria are checked against actual files
- Tests/build/lint are considered or run where appropriate
- Critical/major findings block ship
- `review-report.md` has been written to the active task directory **before** the exit summary
- Approved review has no open blockers and is safe for next stage
- Human Review Gate is recorded. If it is `required`, a human decision is recorded before `/forgeflow:ship`; otherwise the skip rationale is recorded.
- Next step is `/forgeflow:ship` only if review passes and the human review gate is satisfied

**Standalone mode**:
- `review-report.md` has been written to the synthetic task directory **before** the exit summary
- No automatic ship — the review report is the final artifact
- User may start a pipeline from the review output if desired

A review that leaves no `review-report.md` is incomplete. The verdict exists only in the artifact, not in chat sentiment.

### Route-aware review behavior

All routes write a **single** `review-report.md` using `templates/review-report.md`.

- **small** route: Single quality review using **fast-review**. Set Review Type: quality. Do the minimum independent checks needed to reject obvious blockers: changed-file scope, acceptance/scope sanity, one fastest relevant observed verification gate, unresolved blocker scan. Complete Quality Assessment as one PASS/FAIL line; Spec Compliance is `not_applicable`. For approved/no-finding small reviews, write ≤80 lines, no Markdown tables, and no Specialist Assertions or Code Quality Metrics sections. If risk triggers are present (security/data/state/API boundary, route threshold exceeded, failed verification, missing critical artifact, or non-trivial finding), escalate to medium-style quality review and record `review_depth: escalated` in the Reader Summary.
- **medium** route: Single quality review. Set Review Type: quality. Complete Quality Assessment.
  - **medium-light** (brief sub-band): Verify task coverage and verification gates; Contracts/Journeys in plan are optional unless present.
  - **medium-full** (brief sub-band): Verify contract-first traceability — every acceptance criterion maps to plan tasks; Contracts and Verification Plan targets must be checked if present in `plan.md`.
- **high/epic** route: Two separate review **passes** are **required** (same file, sequential gates):
  1. `/forgeflow:ff-review --type spec` — Create or update `review-report.md`. Set Review Type: spec. Complete Spec Compliance and Evolution Rule Review. Record spec verdict. Do not proceed to quality until spec verdict is approved.
  2. `/forgeflow:ff-review --type quality` — Update the same `review-report.md`. Set Review Type: quality (or note both passes in Findings). Complete Quality Assessment. Final verdict must reflect quality pass.

  For high/epic, if Spec Compliance is missing, incomplete, or spec verdict != approved, do not proceed to the quality pass. Each pass is an independent gate; do not merge both passes into one review turn.

## Dependencies

- `docs/review-runtime-contract.md` — Adapter-neutral review contract, role separation, and read-only tool surface
- `skills/_shared/isolation.md` — Worktree detection and isolation handling (required for review inside worktrees)
- `skills/_shared/preflight.md` — Checkpoint-first status analysis preflight
- `skills/_shared/context-resume.md` — Context refresh/resume read discipline
- `skills/_shared/discipline.md` — File write and output discipline
- `skills/_shared/automation.md` — Non-interactive approval mode
- `templates/review-report.md` — Review report template

## Constraints

## File write and output discipline

→ Core rules: `_shared/discipline.md`.

Follow the user language rules there: write user-facing replies and artifact prose in the user's primary language, while preserving canonical English labels, commands, paths, artifact filenames, and enum values.

Write `review-report.md` under `<task-dir>`. If the task directory is missing, bootstrap or recover it first. A review that leaves no artifact is just vibes with punctuation.

## Strict response constraints

→ `_shared/discipline.md`.

For exact-count list prompts, output numbered lines only. No preamble, heading, fenced block, verdict, or extra commentary.

## Evidence discipline

Review evidence is not fan fiction. Use a blocker-first verdict: unresolved blocker, missing required artifact, failed required verification, or uninspected claimed evidence prevents approval before any quality praise matters.

**Role separation principle**: The implementing session's self-report is input for review, not a substitute. Do not approve work based solely on the implementer's summary. Cross-check claimed evidence against `ledger.md` and `implementation-notes.md`. If the implementer says a test passed, verify it independently. The reviewer is an independent role with a separate responsibility boundary.

**Small-route evidence budget**: For route `small`, cross-check only the minimum read set, changed files, and one fastest relevant verification command by default. Escalate to medium-style review only if the diff exceeds the small route threshold, touches security/data/state/API boundaries, verification fails, artifacts are missing enough to hide scope, or a concrete finding requires deeper evidence.

- Claim only what you directly observed in this review turn or what is explicitly present in provided artifacts.
- If a worker, previous assistant, or user says a command passed, cite it explicitly with the phrase `reported evidence` unless you personally ran or inspected the command output in this turn.
- Use `observed evidence` only for command outputs, artifacts, files, or diffs you directly inspected in this review turn.
- Do not say lint/build/tests/dev-server/runtime verification passed unless you ran the command or inspected the concrete captured output.
- If verification is missing, blocked, or only reported second-hand, mark it as missing or reported; do not convert it into approval-grade evidence.
- Evidence refs must name concrete files, command outputs, diffs, or user-provided artifacts. Avoid vague refs like "verified behavior".
- Referenced repository paths must exist in the reviewed diff/worktree unless explicitly labeled as planned, missing, or user-provided hypothetical paths.
- Do not approve a review that treats nonexistent files, commands, or evidence refs as observed facts. Path hallucination is a blocker, not a typo.
- When command execution is disallowed, use manual inspection language only: "not run", "manual inspection", "requires verification".

## Output normalization (review input)

When reading agent output during review, normalize before analyzing:

- **Codex**: Diff blocks may dominate the log (80%+). Extract only the final summary, file list, and verification results. Ignore intermediate diff hunks.
- **All adapters**: Strip ANSI codes, cache warm-up messages, and non-artifact metadata before evidence extraction.
- Mark normalized output as `processed evidence` vs `raw evidence` in findings when the distinction matters.

## Consistency check

Before approving, check whether the work kept instructions, tools, environment, state, and feedback consistent across artifacts and code. Requirement/contract drift, nonexistent verification tools, ignored environment blockers, stale artifacts, or unclosed feedback from failures are review findings. Label verification evidence as observed, reported, or missing before deciding whether it can support approval.

## Test verification gate

Review MUST independently verify at least one relevant gate before approving. Test execution depth is route-aware:

1. **Run the relevant test command yourself when tests are the selected gate.** Do not trust worker-reported pass/fail counts. Execute the narrowest appropriate command (`pytest path/to/test.py`, `npm test -- <file>`, `make test`, etc.).
2. **Small route fast path**: if the change is non-logic or tests are expensive/unrelated, choose the fastest relevant gate instead (`lint`, `type_check`, or `build`). Do not run a broad full suite merely because a generic test command exists.
3. **Medium+ routes**: run tests when tests exist for changed files; pair with at least one other required gate per Standard verification checklist.
4. **Parse the output.** If any selected gate fails, the review verdict MUST be `changes_requested` — never `approved`.
5. **Record evidence.** Include the command, total/pass/fail counts when available, or concise PASS/FAIL output when the gate is not test-count based.
6. **Flaky test disclaimer.** If selected tests are flaky and fail intermittently, run them once more. If they still fail, they fail. A flaky test failure is still a failure for review purposes.
7. **No relevant command found.** If no relevant verification command exists or commands cannot be run, record this as `reported evidence: no command found` and note it as a minor finding. Do not treat this as a blocker, but do not claim verification passed.

### Standard verification checklist

When reviewing, run the **independent verification suite** (all that apply, minimum 1):

| Gate | Command pattern | Required when |
|------|----------------|---------------|
| build | `pnpm build` / `npm run build` / `cargo build` | All code tasks |
| lint | `pnpm lint` / `npm run lint` / `ruff check` | Lint config exists |
| type_check | `tsc --noEmit` / `mypy` / `cargo check` | Typed codebase |
| test | `pnpm test` / `npm test` / `pytest` | Tests exist for changed files |

Small routes: minimum 1 gate; choose the fastest relevant observed gate (`test` for logic with tests, otherwise `lint`, `type_check`, or `build`). Do not run the full suite by default for small changes unless the project has only one cheap all-in-one command. Medium+: minimum 2 gates (build + 1 other). High/epic: all applicable gates.
Record each result in findings as `verification:PASS/FAIL gate=<name> command="<cmd>"` (observed evidence).

## Git safety summary

- Name the exact diff scope reviewed: files, directories, commit range, or staged changes.
- Name verification evidence: commands run, artifacts inspected, or missing evidence.
- Treat broad staging, destructive git actions, and dirty unrelated user work as review risks unless explicitly justified and approved.

## Evolution rule validation

Evolution rules are generated during the **ship** stage. Review does not need to validate or handle evolution rules. If `eval-record.md` exists (from long-run, high/epic routes), it may contain pattern observations that ship will use for rule extraction, but review treats it as read-only context, not a validation target.

## Automation / non-interactive approval mode

→ `_shared/automation.md`.

## Status analysis preflight

→ Core procedure: `_shared/preflight.md` (checkpoint-first, section-targeted reads).

→ Context refresh/resume rules: `_shared/context-resume.md`.

Review-specific: reconstruct task state from artifacts, not chat memory. **Do not read all artifacts in full at entry.**

- **Minimum read set**: checkpoint → ledger gates + active/completion summary → implementation-notes Reader Summary + Evidence Index → brief Acceptance Criteria → plan Requirements + Verification Plan + implicated task sections only.
- Expand `implementation-notes.md` Decisions/Evidence only when findings or blockers require it.
- Expand `plan.md` beyond Requirements/Verification Plan/implicated tasks only when scope or fulfills traceability demands it.
- For **high/epic**, collect `micro_spec:*` and `micro_quality:*` from Evidence Index or Evidence. Summarize in `review-report.md` → **Execute Micro-Gates**. Treat as **reported evidence** until re-verified.
- Read `<storage-root>/evolution/active/*.md` (resolved via `forgeflow_storage.py`) when project rule consistency is in scope.
- **Perf-review lens**: flag repeated full-artifact read patterns; prefer checkpoint Minimum Read Set.

## Artifact completeness gate

Before approving review, inspect required ForgeFlow artifacts for unresolved template residue. Treat unresolved placeholders as `changes_requested` or `blocked` before quality praise:

- Check `brief.md`, `plan.md`, `implementation-notes.md`, `ledger.md`, `ship-summary.md` (including Evidence Manifest section), and any existing `review-report.md`.
- Flag unresolved `TODO`, `TBD`, `FIXME`, template comments such as `<!-- ... -->`, and angle-bracket placeholders such as `<task-id>`, `<branch-name>`, or `<...>` when they are artifact-writing residue.
- Do not flag intentional Markdown checkboxes, code snippets, command output, or literal examples when they are clearly part of the reviewed content rather than unfinished artifact fields.
- If placeholder residue remains in an artifact required for the current route, do not approve. Name the file and the unresolved marker in Findings.
- **Completion checklist completeness**: For medium/high/epic routes, verify `implementation-notes.md` has filled sections for `## 컴포넌트/함수 역할 (Role Descriptions)` and `## 엣지 케이스 (Edge Cases)`. If either section is missing or still contains only template comments, flag as a `major` finding with category `process / artifact-completeness`. Empty sections mean the execute stage did not complete its mandatory checklist.
- **File size gate**: Check `## 지표 (Metrics)` for `oversized_file` entries. If any changed file exceeds the project's line limit (default 300) and no split plan is documented, flag as a `major` finding with category `quality / maintainability`.
- **Evidence manifest gate**: For post-execute mode, `ship-summary.md` Evidence Manifest section must exist and have all verification gates filled (not template placeholders). If missing or incomplete, set verdict to `blocked` — the execute stage did not fulfill its evidence contract. Review must independently verify each gate result listed in the manifest.

## Procedure

### Isolation detection

→ `_shared/isolation.md`.

Detect worktree environment at entry:
- `test -f .git` → worktree environment. Artifact access via symlinked `.forgeflow/` should work.
- `test -d .git` → main repository. Proceed normally.

Review is read-only. It can run in either environment. If running in a worktree, verify the `.forgeflow` symlink resolves and task artifacts are accessible before starting review.

### Step 0 — Mode detection and routing

**Pipeline mode detection**: If `brief.md`, `plan.md`, or `implementation-notes.md` exist in the active task directory (resolved task directory: `~/.forgeflow/projects/<project-slug>/tasks/<id>/` by default), proceed in **pipeline mode** (steps 1-18 below).

**Standalone mode detection**: If only external input is provided (URL, diff, files, repo path), or if the user explicitly requests standalone review, enter **standalone mode** and follow the standalone procedure (steps S1-S10 below).

Do not enter standalone mode if pipeline artifacts exist, even if the user provides a URL. Pipeline artifacts take precedence.

### Pipeline mode procedure

Follow the full pipeline checklist in `skills/ff-review/references/pipeline-procedure.md` for task traceability, Plan Conformance Gate, independent verification, 3-Lane Review Routing, execute checklist verification, and next-step output. The non-negotiable gates are:

1. Review from artifacts and code, not worker self-report.
2. Verify scope, acceptance criteria, plan tasks, verification evidence, ledger consistency, and unresolved blockers before approval.
3. Run independent verification when allowed; any selected gate failure prevents approval.
4. Apply the appropriate review rubric plus role checklist; quality-reviewer with diff/code input also applies `skills/ff-review/references/deep-code-analysis.md`.
5. Write or update `review-report.md`; the verdict in the file is the only valid verdict.
6. Do not call `/forgeflow:ship` unless verdict=approved, safe_for_next_stage=yes, and open_blockers=none are all true in the written `review-report.md`.

Do not merge spec and quality review passes into a single turn for high/epic work. Use one `review-report.md` with sequential passes.

### Standalone mode procedure

Follow `skills/ff-review/references/standalone-mode.md` and `skills/ff-review/references/input-normalization.md` for input type detection, synthetic task directory bootstrap, read-only provenance capture, normalization, role selection, finding aggregation, `review-report.md` writing, and human response handling. Standalone review ends at the review report and never auto-proceeds to ship.

## Human Final Judgment Gate

AI review results are **advisory**, not auto-approval. The review report is a structured recommendation. The human decides what to act on.

Full judgment gate procedure (advisory labels, priority classification, override process, ship gate): **read `references/human-judgment.md` before presenting review results to the human**.

## Output mode examples

If asked:

```text
/forgeflow:ff-review Dry run only. List exactly two review checks. Do not write files. Do not run commands.
```

Return exactly two review checks. Do not add a verdict, extra commentary, or file writes.

## Telemetry

On completion of this stage, record a telemetry event to `<telemetry-dir>/<task-id>.md`:
- **event**: `stage_complete` on success, `stage_fail` on error/failure
- **stage**: review
- **outcome**: `success` | `partial` | `failed`
- **failure_type**: on failure, categorize as `assertion_mismatch` | `scope_creep` | `validation_error` | `adapter_error` | `timeout` | `unknown`

On scope boundary violations detected during review, record:
- **event**: `boundary_alert`
- **stage**: review

Follow `skills/_shared/discipline.md` Telemetry Event Recording for format details.
