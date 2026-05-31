---
name: review
description: Perform independent ForgeFlow review. Use as /review or /forgeflow:review — either after execute (pipeline mode) or directly with external input (standalone mode).
version: 0.5.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must separate findings by reviewer role (spec, quality, security, ux, perf).
  Must not approve work with unresolved blockers or missing verification evidence.
  Must apply applicable review rubric (Spec Review or Quality Review) per role.
---

# Review

Use this skill to review completed ForgeFlow work independently.

## Input

Review supports two entry modes. The detected mode determines which artifacts and evidence are available.

### Post-execute mode (pipeline)

Review after execute stage. Requires pipeline artifacts from `.forgeflow/tasks/<id>/`:
- `brief.md` from clarify stage
- `plan.md` from plan stage
- `implementation-notes.md` from execute stage
- `run-ledger.md` from execute stage
- `decision-log.md` from clarify/plan/execute stages (optional but recommended for tracing prior decisions)
- Final codebase state
- Verification commands/results

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
| Post-execute | implementation-notes.md | run-ledger.md | plan.md scope |
| URL (PR diff) | diff URL | diff hunks | changed files |
| Repo snapshot | directory structure | file listing | specified paths |
| File bundle | file list | file contents | specified files |
| Git range | commit range | diff output | changed paths |

## Standalone Mode

When review is invoked without prior clarify/plan/execute stages — no `.forgeflow/tasks/<id>/` with pipeline artifacts — it operates in **standalone mode**. The review becomes an independent inspection gate, not a pipeline post-step.

### Input type detection

Detect input type by pattern, in this priority order:

1. **URL** — String starts with `https://` or `http://`. Known patterns:
   - `github.com/<owner>/<repo>/pull/<n>` → GitHub PR. Fetch via `gh pr diff <n>` or `gh pr view <n> --json title,body,files`.
   - `github.com/<owner>/<repo>/commit/<sha>` → GitHub commit. Fetch via `gh api repos/<owner>/<repo>/commits/<sha>`.
   - `github.com/<owner>/<repo>/compare/<a>...<b>` → GitHub compare. Fetch via `gh api repos/<owner>/<repo>/compare/<a>...<b>`.
   - Any other URL → Fetch page content via `web_extract` or `curl`. Extract main content, strip navigation/chrome.
   - **Failure handling**: If fetch returns 404, auth error, or empty content, record as `blocked: input fetch failed — <url>`. Do not proceed with guessed content.

2. **Repo path** — String is a local directory path that exists on disk and contains a `.git/` directory or is inside a git worktree.
   - No branch/commit specified → use current worktree diff (`git diff HEAD`) and working tree state.
   - Branch range specified (`main..feature`) → `git diff <range>`.
   - Single commit → `git show <sha> --stat` + `git diff <sha>~1 <sha>`.
   - **Failure handling**: If directory doesn't exist or isn't a git repo, record as `blocked: invalid repo path — <path>`.

3. **Diff/patch** — Input contains unified diff markers (`--- a/`, `+++ b/`, `@@`), is provided with `--diff` flag, or is a local file path ending in `.diff` or `.patch`.
   - For `.diff` / `.patch` paths, read the file first and record `input-source.md` with original input as the file path and fetch command/source as `file-read:<path>`.
   - Parse hunks: extract file paths from `---`/`+++` headers, line ranges from `@@` markers.
   - Build a virtual file map: for each file in the diff, record additions, deletions, and context lines.
   - **Failure handling**: If diff cannot be parsed (no markers, malformed hunks), attempt to treat as file bundle. If neither works, record as `blocked: unparseable diff input`.

4. **File bundle** — One or more file paths provided. Verified to exist on disk.
   - Read each file. For each file, detect language and structure.
   - Build evidence from file contents. Scope = the listed files.
   - **Failure handling**: If any file doesn't exist, record as `blocked: missing input file — <path>`. Do not skip silently.

5. **Existing artifact** — Path to a `.forgeflow/tasks/` directory or specific artifact file (e.g., `review-report.md`, `implementation-notes.md`).
   - Read the artifact. Use its content as evidence.
   - If it's a task directory, read all artifacts found inside for context.
   - **Failure handling**: If path doesn't exist, fall through to other detection. Do not assume artifact format.

6. **Ambiguous input** — If no type matches, ask the user to clarify the input type. Do not guess and proceed with wrong assumptions.

### Synthetic task directory bootstrapping

When standalone mode is detected, create a synthetic task directory:

```
.forgeflow/tasks/standalone-<YYYYMMDD-HHMMSS>/
├── input-source.md      # Raw input provenance (URL, path, diff metadata)
├── normalized-input.md   # Brief + evidence + scope + constraints (auto-generated)
└── review-report.md      # Output (written during review)
```

Create `input-source.md` from `templates/input-source.md`. It records:
- Input type detected
- Source classification rationale: why the type was selected, plausible ambiguities considered, and whether ambiguity was resolved or blocked
- Original input value (URL, path, diff snippet)
- Fetch command used (if applicable)
- Fetch result status (success/partial/failed)
- Missing/truncated evidence notes
- Evidence Source Map linking each normalized evidence ID to the fetch command/API/source label, normalized evidence type, fetch status, evidence level, and integrity
- Timestamp

Create `normalized-input.md` from `templates/normalized-input.md`. It records the 4-field structure (see Input Normalization below).

Before reviewer roles begin, fill the template's **role evidence map**. Map every active reviewer role to the normalized evidence IDs it may cite; for inactive or blocked roles, write `none — <reason>`. Evidence IDs must be stable and unique within `normalized-input.md`; never reuse an ID for a different file, diff hunk, command output, or sampled content. Roles must not cite chat-only or unnormalized evidence. If a role needs additional material, add it as a new evidence item in `normalized-input.md` first, including type, source, fetch status, evidence level, and limitation/truncation notes, then mirror the same type/status/level plus provenance in `input-source.md` Evidence Source Map.

After the role evidence map is filled, perform a routing consistency check: every role listed in `constraints.roles` must be `run` or `blocked` in the Role trigger matrix and must have either allowed evidence IDs or an explicit blocked rationale in the role evidence map. Any role marked `run` must also appear in `constraints.roles`. A mismatch blocks reviewer judgment until normalization is corrected; do not silently add or drop roles in `review-report.md`.

Then fill **role input packet readiness** for every active, blocked, or skipped reviewer role. Mark a role `READY` only when its trigger decision, allowed evidence IDs, scoped files/ranges/exclusions, constraints/focus flags, visible limitations, and packet freshness are all present in `normalized-input.md`. Mark it `BLOCKED` when any packet field is missing or stale and prevent that role from judging until the missing/stale field is normalized or recorded as unavailable. Mark skipped roles `SKIPPED` with an explicit non-trigger reason. After readiness is set, fill **role input packets** for every READY or BLOCKED role by copying the trigger, evidence IDs, scope, constraints, limitations, and packet freshness from normalized fields; skipped roles may be `none — <explicit non-trigger reason>`. Refresh readiness and packets after any Evidence Escalation Log entry, new evidence item, scope change, constraint change, or role-routing change. Reviewer roles must cite their packet row before judgment and must not replace missing packet fields with chat memory or hidden adapter state.

Before any delegated or parallel reviewer pass begins, fill the template's **review ownership plan**. Record exactly one lead reviewer for normalization, role routing, aggregation, conflict visibility, and the human gate; record each member assignment with one reviewer role, evidence/scope IDs, claim marker, and writable report section. The `aggregation_owner` must match the single `lead_reviewer`; multiple leads, missing leads, or lead/aggregation-owner mismatch block approval. If no delegation is used, write `member_assignments: none — single lead review`. Member assignments are role claims, not a task scheduler: members cannot create additional reviewer roles, reassign scope, broaden their evidence map, or write outside their assigned report section. Any missing lead, duplicate aggregation owner, unmanaged child-work allowance, member-side role reassignment, scope broadening, or product-mutation allowance blocks approval until corrected.

Before any reviewer role begins, complete the template's **normalization gate**. If `brief_present`, `evidence_present_or_blocked`, `scope_explicit`, `constraints_explicit`, or `limitations_visible` is `FAIL`, stop with `blocked` and record the missing provenance in `review-report.md`; do not let reviewer roles fill gaps by assumption.

Before reviewer judgment, also complete the template's **adapter handoff checklist**. Mark `source_classified`, `fetch_reproduced`, `normalization_complete`, `limitations_visible`, and `canonical_review_ownership` as `PASS` or `FAIL`. Any `FAIL` blocks approval unless a human explicitly narrows the review scope and records the limitation; adapters must not compensate by writing a parallel verdict or report.

If any reviewer role needs evidence outside the role evidence map, pause that role and add an **Evidence Escalation Log** entry in `review-report.md` before judgment continues. The lead reviewer must either add a new evidence item to `normalized-input.md` and mirror its provenance in `input-source.md`, or record the request as unavailable with the affected role blocked/limited. After the escalation outcome, refresh the affected role evidence map, input packet readiness, and role input packet before that role can continue; stale packets block judgment. Do not use chat memory, hidden adapter state, or unrecorded file reads to satisfy the gap.

If `.forgeflow/` doesn't exist, create it. Do not initialize a full ForgeFlow workspace — only the task directory and its files.

### Standalone constraints

- No `brief.md`, `plan.md`, `run-ledger.md`, or `implementation-notes.md` is expected. Do not flag their absence as findings.
- No route selection (small/medium/high/epic) — standalone mode always runs as a single comprehensive pass unless `--type` is specified.
- No execute micro-gates table — skip that section in the report.
- Evolution rule review is always `not_applicable` in standalone mode.
- The review report is the final artifact. There is no automatic ship.

## Input Normalization

Regardless of input type, normalize to a standard 4-field structure before review proceeds. Write the result to `normalized-input.md` in the synthetic task directory.

### brief

What is being reviewed. Auto-generated from input:

| Input type | brief source |
|------------|-------------|
| GitHub PR | PR title + body (from `gh pr view`) |
| GitHub commit | Commit message (first line = title, body = context) |
| GitHub compare | `"<base>...<head> comparison"` + commit messages in range |
| Other URL | Page `<title>` or first `<h1>`. If none: `"Review of <url>"` |
| Repo path (current) | `"Review of working tree in <repo>"` + `git log --oneline -5` summary |
| Repo path (range) | `"Review of <range> in <repo>"` + commit count + file count from `git diff --stat` |
| Diff/patch | `"Review of diff: <N> files, <M> additions, <K> deletions"` |
| File bundle | `"Review of: <file1>, <file2>, ..."` (list all files) |
| Existing artifact | Artifact filename + first heading or summary line |

If the user provides an explicit description (`--desc "..."` or natural language in the command), use that as brief and append the auto-generated version as context.

### evidence

The concrete content to review. Extraction rules:

| Input type | evidence extraction |
|------------|-------------------|
| GitHub PR | `gh pr diff <n>` output (full diff). Separate from PR metadata. |
| GitHub commit | `git show <sha>` output (stat + diff). |
| GitHub compare | `git diff <range>` output. If too large (>5000 LOC changed), sample: first/last 200 lines per file + file list. |
| Other URL | Extracted page content (markdown). If page is a code host, extract code blocks. |
| Repo path (current) | `git diff HEAD` + `git diff --cached`. If clean, `git log --oneline -10` + tree listing. |
| Repo path (range) | `git diff <range>`. Same large-diff sampling rule as compare. |
| Diff/patch | The raw diff text, including content read from `.diff` / `.patch` file paths. Parse into per-file hunks. |
| File bundle | Each file's full content. If a file exceeds 2000 lines, read first 500 + last 200 and note truncation. |
| Existing artifact | Full artifact content. |

**Evidence integrity rules**:
- Never fabricate or infer evidence. If fetch fails, the field is `null` and review is `blocked`.
- Mark truncated evidence with `[TRUNCATED: showing N/M lines]`.
- Mark fetched evidence with source: `[source: gh pr diff]`, `[source: file read]`, `[source: web_extract]`.

### scope

What range is in scope for this review:

| Input type | scope definition |
|------------|-----------------|
| GitHub PR | Files changed in the PR (from `gh pr diff --name-only`). |
| GitHub commit | Files changed in the commit (from `git show --stat`). |
| GitHub compare | Files changed in the range. |
| Other URL | Entire fetched content. |
| Repo path (current) | All uncommitted changes + staged changes. If clean: last 5 commits. |
| Repo path (range) | Files changed in the range. |
| Diff/patch | Files mentioned in diff headers (`---`/`+++`); for `.diff` / `.patch` files, the patch file itself is provenance, not review scope unless explicitly requested. |
| File bundle | The listed files only. |
| Existing artifact | The artifact itself + any referenced files that exist. |

User can narrow scope with `--scope <pattern>` (glob). Only review files matching the pattern within the detected scope.

### constraints

Review focus areas or restrictions:

- **User-specified**: `--focus security`, `--focus quality`, `--type spec`, `--type quality`. These constrain which reviewer role runs.
- **Inferred from input**:
  - PR with no description → quality review only (no spec to check against).
  - Diff with only test files (all changed filenames match test patterns: `*.test.*`, `*.spec.*`, `*_test.*`, `test_*`, or live under a test directory) → quality-reviewer with test-quality focus: check coverage adequacy, assertion quality, test isolation, fixture management.
  - URL to a design doc → spec/ux review only.
  - File bundle of config files → quality/security review.
- **Default** (no constraints specified): run both spec and quality reviews. Spec review uses auto-generated brief as the "spec" to check against.

Write constraints to `normalized-input.md` as a structured list:
```
constraints:
  - type: <auto-inferred | user-specified>
  - focus: [spec | quality | security | ux | perf]
  - excluded_paths: [...]  (if --scope narrows)
  - additional_rules: [...]  (user-provided or inferred)
```

### Normalization gate

After writing `brief`, `evidence`, `scope`, and `constraints`, mark the `normalization gate` in `normalized-input.md`:
- `brief_present`: `PASS` only when the review target is named and sourced.
- `evidence_present_or_blocked`: `PASS` only when concrete evidence exists, or evidence fetching failed and the failure is recorded as a blocker.
- `scope_explicit`: `PASS` only when included/excluded files, ranges, or URL bounds are explicit.
- `constraints_explicit`: `PASS` only when active roles/focus and ignored/conflicting flags are explicit.
- `limitations_visible`: `PASS` only when truncation, sampling, auth/fetch failures, excluded paths, and missing evidence are visible to reviewer roles.

Any `FAIL` blocks review approval. Record the failed gate item as missing evidence rather than continuing with inferred content.

## Runtime contract

ForgeFlow review follows `docs/review-runtime-contract.md`. Load that document before changing review routing, standalone input handling, role output, tool permissions, evidence handling, or adapter behavior.

Contract obligations:
- Adapters are thin: detect input, fetch raw evidence, normalize to `brief / evidence / scope / constraints`, write `input-source.md` and `normalized-input.md`, then invoke canonical review.
- `normalized-input.md` must include stable evidence IDs and a role evidence map so reviewer roles cite only normalized, provenance-visible material.
- Adapter handoff must satisfy the contract's Adapter compliance checklist: source classified, fetch reproduced, normalization complete, limitations visible, and review ownership delegated to the canonical review skill.
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

### Role definitions

Role-specific triggers stay inline so operators can decide which passes to run quickly. The detailed checklist items and role-specific evidence requirements live in `skills/review/references/role-checklists.md`; load that reference before executing any role pass and cite the exact `Checklist version: YYYY-MM-DD` value in `review-report.md` as `Checklist Version`. Before each role begins, the lead reviewer must provide the role input packet required by that reference from `normalized-input.md` only and cite its **role input packet readiness** row; missing, `BLOCKED`, or chat-only packets block that role instead of allowing inferred evidence.

Before running roles, write a compact role routing rationale in `review-report.md`: list `Active roles` and `Skipped roles` explicitly. For every role that runs or is intentionally skipped, cite the route rule, `--type`/`--focus` flag, file-type heuristic, specialist profile, or explicit non-trigger that decided it. A missing skipped-role reason is a routing gap, not a harmless omission. This prevents standalone adapters and parallel reviewers from silently broadening or narrowing review scope after normalization.

In standalone mode, also fill `normalized-input.md` → `Role trigger matrix` before any role begins. Each supported role must have one row marked `run`, `skipped`, or `blocked`, with the normalized evidence ID(s) or explicit non-trigger signal that drove the decision. Do not activate security/ux/perf from chat-only intuition; first normalize the path, diff hunk, artifact, or command output that shows the trigger. If the trigger signal is missing because fetching failed or evidence was truncated away, mark that role `blocked` or `skipped — missing trigger evidence` instead of silently running a weak pass.

#### spec-reviewer

**Trigger**: Always runs in pipeline mode. In standalone mode, runs when a brief/requirement/spec document exists (auto-generated or user-provided).

**Checklist source**: `skills/review/references/role-checklists.md#spec-reviewer` (in addition to the Spec Review rubric).

**Standalone-specific**: When no explicit spec exists, the auto-generated brief becomes the de facto spec. The spec-reviewer checks whether the code/diff does what the brief describes — no more, no less. Flag scope that doesn't trace back to the brief as `major: unexplained scope`.

#### quality-reviewer

**Trigger**: Always runs in both pipeline and standalone mode.

**Checklist source**: `skills/review/references/role-checklists.md#quality-reviewer` (in addition to the Quality Review rubric).

**Standalone-specific**: Without implementation-notes, the quality-reviewer works from the code/diff directly. Apply heuristics without referencing executor claims.

#### security-reviewer

**Trigger**: Runs when `--focus security` is specified, or when in-scope changes touch authentication/authorization, input validation/sanitization, secret/key handling, API/network boundaries, file system operations, or dependency additions.

**Trigger evidence**: cite the role trigger matrix row and normalized evidence IDs for the auth/input/secrets/network/filesystem/dependency signal before opening findings.

**Checklist source**: `skills/review/references/role-checklists.md#security-reviewer`.

#### ux-reviewer

**Trigger**: Runs when `--focus ux` is specified, or when in-scope changes touch UI component files, CSS/styling, user-facing text/labels/messages, route/page definitions, or form handling code.

**Trigger evidence**: cite the role trigger matrix row and normalized evidence IDs for the UI/text/route/form/accessibility signal before opening findings.

**Checklist source**: `skills/review/references/role-checklists.md#ux-reviewer`.

#### perf-reviewer

**Trigger**: Runs when `--focus perf` is specified, or when in-scope changes touch database queries/ORM calls, loops over large collections, caching layers, network call batching, or memory-intensive operations.

**Trigger evidence**: cite the role trigger matrix row and normalized evidence IDs for the query/loop/cache/batching/memory signal before opening findings.

**Checklist source**: `skills/review/references/role-checklists.md#perf-reviewer`.

### Role routing

**Pipeline mode** (route-aware):
- small: quality-reviewer only, using **fast-review** depth (see Route-aware review behavior)
- medium: quality-reviewer only (medium-full may add spec-reviewer)
- high/epic: spec-reviewer (pass 1) → quality-reviewer (pass 2), sequential gates
- Any route: security/ux/perf-reviewer triggered by file-type heuristics above
- Human review is a separate decision-partner gate, not an automated reviewer role. Apply the Human Review Gate below after automated review has produced `review-report.md`.

**Standalone mode**:
- No `--type` flag: quality-reviewer always runs. spec-reviewer runs if brief exists. Other roles triggered by file-type heuristics.
- `--type spec`: spec-reviewer only
- `--type quality`: quality-reviewer only
- `--type security`: security-reviewer only
- `--type ux`: ux-reviewer only
- `--type perf`: perf-reviewer only
- `--type all`: run all 5 roles regardless of file-type heuristics (security, ux, perf included even if no matching files detected)
- `--focus <role>`: alias for `--type <role>`
- **`--type` and `--focus` combined**: `--type` wins. `--focus` is ignored with a warning. Do not run two conflicting role sets.

### Role model hints

When a harness supports role-specific model selection, bind by capability rather than provider name and keep the decision advisory:

- spec-reviewer, security-reviewer, and unresolved cross-role conflict aggregation → strongest reasoning available.
- quality-reviewer → standard reasoning/coding model; upgrade to strongest reasoning for broad refactors, weak verification, or many interacting files.
- ux-reviewer and perf-reviewer → standard reasoning model unless the normalized evidence shows accessibility, query-planning, caching, or large-data risk that needs specialist depth.

Record any non-default role/model assignment in the role-pass record or adapter notes as a hint only. Model choice must never change role routing, evidence requirements, verdict enums, or the human review gate.

In standalone mode, if role/model or specialist profile selection is known before reviewer judgment, record it in `normalized-input.md` → `role capability hints`. Use provider-neutral capability language (`strongest reasoning available`, `standard reasoning/coding model`, or `not_applicable`) and treat the section as audit metadata only. Do not block review because an adapter lacks per-role model selection; block only if a capability hint is used to alter role routing, evidence IDs, evidence levels, verdict enums, approval rules, or human-gate semantics.

### Specialist Profiles

Specialist profiles define focused review lenses tied to the `specialist` field in `brief.md` YAML frontmatter. When review reads `brief.md`, it extracts the specialist primary and secondary values and automatically applies the corresponding assertion sets below. These assertions supplement (not replace) the standard reviewer role checklists.

| Specialist | Focus | Key Assertions |
|---|---|---|
| security | 인증/권한/입력검증 | no hardcoded secrets, input sanitization, auth boundary checks, no eval/exec of untrusted input |
| ux | UI/문구/접근성 | consistent terminology, a11y compliance, clear error messages, loading states for async operations |
| perf | 성능/메모리/지연 | no N+1 queries, lazy load where appropriate, cache strategy documented, pagination/streaming for large datasets |
| correctness | 로직/에러처리/엣지케이스 | edge cases covered, error propagation complete, idempotency where required, no unchecked error paths |
| maintainability | 구조/네이밍/중복/가독성 | DRY adherence, single responsibility, naming convention consistency, no unnecessary abstractions, code intent is clear without comments, consistent abstraction level within a module, short focused functions (≤30 lines recommended), magic values extracted to named constants |

**Specialist assertion application logic**:

1. Read `brief.md` YAML frontmatter `specialist.primary` and `specialist.secondary`.
2. For each non-`none` specialist value, activate the corresponding assertion set from the table above.
3. Assertions from specialist profiles are **mandatory** — every activated assertion must be checked and explicitly recorded in findings.
4. Primary specialist assertions are checked first and carry higher weight in severity classification.
5. Secondary specialist assertions supplement the primary lens; they use the same severity scale but are advisory if they conflict with primary findings.
6. Record activated specialist profile(s) in `review-report.md` → `specialist_profile` frontmatter field, including the count of assertions applied.
7. If `brief.md` has no specialist field or both values are `none`, skip specialist assertions and rely on standard reviewer role checklists only.

### Cross-role conflict handling

When two roles produce conflicting findings:
1. Record both findings in the report with their role label.
2. Add a `⚠ requires human decision` marker in Findings.
3. Do not resolve the conflict by choosing one side. The human final judgment gate handles this.
4. Example: spec-reviewer says "missing error handling for edge case X" (blocker) but quality-reviewer says "error handling would add unnecessary complexity" (minor). Both stay. Report shows conflict with `requires human decision`.

### Role output structure in review-report.md

Each finding includes the reviewer role and evidence classification:
```
- **Role**: spec-reviewer | quality-reviewer | security-reviewer | ux-reviewer | perf-reviewer
- **Evidence Source**: <artifact/diff/command/source label>
- **Evidence Level**: observed | reported | missing
```

The report includes a **Role Summary** section:
```
## Reviewer Role Summary
- spec-reviewer: <verdict>, <N> findings (<blockers> blockers, <majors> major)
- quality-reviewer: <verdict>, <M> findings (<blockers> blockers, <majors> major)
- [other roles if triggered]
- Cross-role conflicts: <count> (marked with ⚠)
```

Each active role must also leave a role-pass record, even when it finds nothing: markdown claim marker (`role=<reviewer> scope=<artifact section/evidence IDs> at=<ISO8601>`), trigger rationale, checklist version used, scope/evidence IDs inspected, observed verification command(s) or explicit no-command rationale, limitations/truncation seen, an Independence Check (`PASS` only when the role used normalized/observed evidence rather than implementer self-report or chat-only claims), finding counts, and role verdict. Do not use chat-only role completion claims as aggregation evidence.

## Human Review Gate

Reference policy: `docs/review-model.md`.

After automated review, classify whether a human decision-partner review is required.

### Mandatory human review triggers

다음 조건 중 하나라도 해당하면 변경 범위와 관계없이 human review가 **필수**이다:

| # | 트리거 | 이유 |
|---|--------|------|
| 1 | 공개 API, CLI 표면, 워크플로우 계약 변경 | 외부 의존성 영향 |
| 2 | 인증/인가/권한/시크릿 변경 | 보안 리스크 |
| 3 | 데이터 영속성(생성/수정/삭제/마이그레이션) 변경 | 데이터 무결성 |
| 4 | 새 의존성 추가 또는 lockfile 변경 | 공급망 리스크 |
| 5 | 환경 변수, 설정 파일, 배포 설정 변경 | 운영 리스크 |
| 6 | 보안 인접 코드 변경 (입력 검증, 에러 처리, 네트워크 경계) | 간접 보안 영향 |
| 7 | 상태 머신, 비즈니스 규칙, 결제/정산 로직 변경 | 비즈니스 로직 리스크 |
| 8 | 크로스 모듈 계약, 인터페이스 시그니처 변경 | 통합 리스크 |

mandatory trigger가 감지되면 review-report.md의 Human Review Gate에 `Decision: required`로 기록하고, 해당 trigger 번호와 이유를 명시한다.

Human review may be skipped only when **all** of these are true:

- Change scope is small/localized and repeats an established pattern.
- Risk is low, rollback is easy, and no state/data/security/permission behavior changes are involved.
- Automated verification is fresh and sufficient.
- Similar prior work repeatedly received LGTM without discussion.
- No cross-role automated-review conflict is present.
- **None of the mandatory human review triggers above are matched.**

Human review is required when any of these are true:

- Public API, CLI surface, workflow contract, or artifact schema changes.
- State, data persistence, deletion, migration, or branch-disposition behavior changes.
- Security, permissions, authentication, secrets, or error-recovery behavior changes.
- Broad impact, difficult rollback, or unclear ownership boundaries.
- Repeated design disagreement or cross-role reviewer conflict.
- Any p1/p2 finding is rejected or marked `risk_accepted` rather than fixed.
- Automated review is blocked, weakly evidenced, or missing required artifacts.

When human review is required, append a **Human Review Packet** section to `review-report.md` with:

- decision needed: concrete question/tradeoff for the human reviewer
- context: design intent and selected tradeoffs
- automated evidence: verdict, blockers, residual risks, verification quality
- recommended discussion prompts: questions rather than edit commands
- handoff target: `ship` only after human decision is recorded, otherwise `execute`

When human review is skipped, record the skip reason in `review-report.md` and make it explicit that automated review is the final review gate for this task.

## Output Artifacts

Write `review-report.md` (schema: review-report/v2, from `templates/review-report.md`) to the active task directory. The report must capture:

- Review Type (spec | quality | security | ux | perf — or list multiple for standalone)
- Verdict (approved | changes_requested | blocked) — never use "passed"
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
- Standalone Input Source (type, original input, fetch status)
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
- Approved verdict with open blockers or safe_for_next_stage=false

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

Automatic fail conditions:
- Avoidable complexity
- Weak verification
- Hidden residual risk
- Shadow-path ownership drift
- Approved verdict with open blockers or safe_for_next_stage=false

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
  1. `/forgeflow:review --type spec` — Create or update `review-report.md`. Set Review Type: spec. Complete Spec Compliance and Evolution Rule Review. Record spec verdict. Do not proceed to quality until spec verdict is approved.
  2. `/forgeflow:review --type quality` — Update the same `review-report.md`. Set Review Type: quality (or note both passes in Findings). Complete Quality Assessment. Final verdict must reflect quality pass.

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

Write `review-report.md` under `.forgeflow/tasks/<task-id>/`. If the task directory is missing, bootstrap or recover it first. A review that leaves no artifact is just vibes with punctuation.

## Strict response constraints

→ `_shared/discipline.md`.

For exact-count list prompts, output numbered lines only. No preamble, heading, fenced block, verdict, or extra commentary.

## Evidence discipline

Review evidence is not fan fiction. Use a blocker-first verdict: unresolved blocker, missing required artifact, failed required verification, or uninspected claimed evidence prevents approval before any quality praise matters.

**Role separation principle**: The implementing session's self-report is input for review, not a substitute. Do not approve work based solely on the implementer's summary. Cross-check claimed evidence against `run-ledger.md` and `implementation-notes.md`. If the implementer says a test passed, verify it independently. The reviewer is an independent role with a separate responsibility boundary.

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

- **Minimum read set**: checkpoint → run-ledger gates + active/completion summary → implementation-notes Reader Summary + Evidence Index → brief Acceptance Criteria → plan Requirements + Verification Plan + implicated task sections only.
- Expand `implementation-notes.md` Decisions/Evidence only when findings or blockers require it.
- Expand `plan.md` beyond Requirements/Verification Plan/implicated tasks only when scope or fulfills traceability demands it.
- For **high/epic**, collect `micro_spec:*` and `micro_quality:*` from Evidence Index or Evidence. Summarize in `review-report.md` → **Execute Micro-Gates**. Treat as **reported evidence** until re-verified.
- Read `.forgeflow/evolution/active/*.md` when project rule consistency is in scope.
- **Perf-review lens**: flag repeated full-artifact read patterns; prefer checkpoint Minimum Read Set.

## Artifact completeness gate

Before approving review, inspect required ForgeFlow artifacts for unresolved template residue. Treat unresolved placeholders as `changes_requested` or `blocked` before quality praise:

- Check `brief.md`, `plan.md`, `implementation-notes.md`, `run-ledger.md`, and any existing `review-report.md`.
- Flag unresolved `TODO`, `TBD`, `FIXME`, template comments such as `<!-- ... -->`, and angle-bracket placeholders such as `<task-id>`, `<branch-name>`, or `<...>` when they are artifact-writing residue.
- Do not flag intentional Markdown checkboxes, code snippets, command output, or literal examples when they are clearly part of the reviewed content rather than unfinished artifact fields.
- If placeholder residue remains in an artifact required for the current route, do not approve. Name the file and the unresolved marker in Findings.
- **Completion checklist completeness**: For medium/high/epic routes, verify `implementation-notes.md` has filled sections for `## 컴포넌트/함수 역할 (Role Descriptions)` and `## 엣지 케이스 (Edge Cases)`. If either section is missing or still contains only template comments, flag as a `major` finding with category `process / artifact-completeness`. Empty sections mean the execute stage did not complete its mandatory checklist.
- **File size gate**: Check `## 지표 (Metrics)` for `oversized_file` entries. If any changed file exceeds the project's line limit (default 300) and no split plan is documented, flag as a `major` finding with category `quality / maintainability`.

## Procedure

### Isolation detection

→ `_shared/isolation.md`.

Detect worktree environment at entry:
- `test -f .git` → worktree environment. Artifact access via symlinked `.forgeflow/` should work.
- `test -d .git` → main repository. Proceed normally.

Review is read-only. It can run in either environment. If running in a worktree, verify the `.forgeflow` symlink resolves and task artifacts are accessible before starting review.

### Step 0 — Mode detection and routing

**Pipeline mode detection**: If `brief.md`, `plan.md`, or `implementation-notes.md` exist in the active task directory (`.forgeflow/tasks/<id>/`), proceed in **pipeline mode** (steps 1-18 below).

**Standalone mode detection**: If only external input is provided (URL, diff, files, repo path), or if the user explicitly requests standalone review, enter **standalone mode** and follow the standalone procedure (steps S1-S10 below).

Do not enter standalone mode if pipeline artifacts exist, even if the user provides a URL. Pipeline artifacts take precedence.

### Pipeline mode procedure (steps 1-18)
1. Read `checkpoint.md` when present, then `_shared/preflight.md` minimum read set. Read `brief.md` Acceptance Criteria and route — not necessarily the full brief unless scope is disputed.
2. Review from artifacts and code, not worker vibes.
3. Check scope coverage and acceptance criteria, including every fulfills, journey, and verification plan target from the plan.
3b. **Scope Boundary Verification** (see Scope Boundary Verification above): Read scope_boundary from brief.md, identify actually modified files, compare planned vs actual, and check route threshold. Record violations in review-report.md frontmatter scope_boundary field. Issue advisory if scope creep detected.
4. Start with blocker elimination: missing artifacts, missing observed evidence, failed verification, or unresolved open blockers force `blocked` or `changes_requested` before minor findings are considered.
5. **Run independent verification** (see Test verification gate and Standard verification checklist above). For small routes, run the fastest relevant observed gate; if tests exist for the changed behavior and are cheap, run those tests. If any selected gate fails, verdict MUST be `changes_requested`.
6. Run or inspect other verification (lint, type check, build) if the user allowed command execution.
7. Separate observed evidence from reported or missing evidence before choosing a verdict.
8. **Review implementation-notes.md**: Check every recorded deviation and open question:
    - Each deviation must be justified. Unjustified deviations are scope drift.
    - Open questions with status `open` are blockers until resolved.
    - Tradeoffs should be evaluated: was the chosen alternative the smallest safe option?
    - If `implementation-notes.md` is missing entirely, note it as a minor finding (the execute stage should have created it).
9. **Cross-check run-ledger.md**: Verify that claimed task completions in implementation-notes match the run-ledger status. If a task is marked `done` in implementation-notes but `running` or `pending` in run-ledger, flag it as an inconsistency. The run-ledger is the execution truth. For high/epic, if a step is `done` but lacks `micro_spec:PASS` (when execute should have run micro-gates), record a **major** spec-compliance finding.
10. **Execute Micro-Gates table** (high/epic): Fill `review-report.md` → Execute Micro-Gates from implementation-notes and run-ledger. Re-run spec/quality checks independently; do not approve because micro-gates passed during execute.
11. **Check active evolution rules**: If `.forgeflow/evolution/active/*.md` exists, verify the work is consistent with active project rules. Do not generate or validate new evolution rules — that is ship's responsibility.
12. Apply the appropriate review rubric (Spec or Quality — see Review Rubrics section above). For quality review, also apply these discipline heuristics:
   - Every changed line should trace directly to the user's request; anything else needs explicit scope approval.
   - Flag drive-by refactors, speculative abstractions, or unrelated cleanup as scope drift unless the plan explicitly authorized them.
   - Was the change the smallest safe change that satisfies the request?
   - **Architectural Depth**: Did the implementation introduce shallow modules (pass-throughs) or miss deepening opportunities? Does the new structure improve locality and leverage?
   - Did the change avoid silent fallback, dual write, and shadow-path ownership drift?
   - Did the implementation follow existing codebase patterns instead of inventing a new local religion?
   - Were assumptions about types, APIs, behavior, and test coverage verified against actual files?
   - If performance was touched, was the bottleneck measured before and after the change?
13. Classify findings by severity: blocker, major, minor, nit.
14. **Write or update `review-report.md`** to the active task directory. For high/epic, spec and quality passes update the same file. The verdict in the file is the only valid verdict.
15. **Verify execute completion checklist**: Before approving, confirm the execute stage produced all required deliverables:
    - ☐ Implementation plan was stated before code changes
    - ☐ All changed files are listed with descriptions
    - ☐ Each component/function role is explained
    - ☐ Edge cases enumerated (medium/high/epic)
    - ☐ Verification commands run and results recorded
    Missing items are `minor` findings for small routes, `major` for medium+, unless the omission is severe enough to block.
16. Return a clear verdict in chat that matches the file. If verdict is `changes_requested` or `blocked`, update `implementation-notes.md` so status reflects the review gate.
17. **다음 단계 안내** — 반드시 사용자에게 출력:
    - If `approved` and `--auto` is active: invoke `/forgeflow:ship` directly (see `_shared/automation.md`).
    - If `approved` (no `--auto`):
      - "리뷰 통과. 출하 준비 완료. `/forgeflow:ship`을 실행해주세요."
      - **Worktree isolation 경고**: If `brief.md` has `isolation: worktree`, append: "주의: 워크트리가 활성 상태입니다. `/forgeflow:ship` 없이 세션을 종료하면 워크트리가 정리되지 않습니다."
      - Update `checkpoint.md`: `Next Action: /forgeflow:ship (worktree cleanup pending)` when worktree isolation is active.
    - If `changes_requested` and ALL findings are artifact-only (scope_files, brief, plan, implementation-notes 등 `.forgeflow/` 메타데이터 수정만 필요): auto-fix scope/brief/plan/notes artifacts, update `checkpoint.md`, then re-invoke `/forgeflow:review` without stopping. 코드 변경이 필요한 finding이 있으면 아래로 fallthrough.
    - If `changes_requested` (code findings exist): **always stop and present findings** (auto-break). "수정이 필요합니다:" + 각 P0/P1 이슈를 `file:line — description` 형태로 나열 + "`/forgeflow:execute`로 수정 후 다시 `/forgeflow:review`를 요청해주세요."
    - Do NOT auto-proceed to ship unless `--auto` is active. 반드시 사용자가 다음 단계를 실행하도록 대기.
18. Do not call `/forgeflow:ship` unless verdict=approved, safe_for_next_stage=yes, and open_blockers=none are all true in the **written** `review-report.md`.

Do not merge spec and quality review passes into a single turn for high/epic work. Use one `review-report.md` with sequential passes.

### Standalone mode procedure (steps S1-S10)

S1. **Detect input type** — Apply input type detection rules (see Standalone Mode → Input type detection). If detection fails, ask the user to clarify. Do not proceed with a guess.

S2. **Bootstrap synthetic task directory** — Create `.forgeflow/tasks/standalone-<YYYYMMDD-HHMMSS>/`. This directory is the task root. If `.forgeflow/` doesn't exist, create it (task directory only, no full workspace init).

S3. **Fetch/extract input and record provenance** — For the detected type, execute the fetch command per Input type detection → per-type instructions. Write `input-source.md` to the synthetic task dir (type, original input, fetch command, result status, timestamp). On fetch failure: write `blocked` status to `input-source.md` and stop.

S4. **Normalize input** — Build the 4-field structure (brief, evidence, scope, constraints) per Input Normalization tables. Write to `normalized-input.md` in the synthetic task dir. If evidence is empty after normalization, write `blocked: input normalization failed` and stop.

S5. **Determine reviewer roles** — Apply role routing (see Reviewer Roles → Role routing). Check `--type`/`--focus` flags. If no flags: quality-reviewer always runs, spec-reviewer runs if brief exists, other roles triggered by file-type heuristics. Record active roles in `normalized-input.md` constraints.

S6. **Run each active reviewer role** — For each active role, in pipeline-mode order (spec → quality → security → ux → perf):
   a. Apply the role's checklist (see Reviewer Roles → Role definitions) AND the applicable review rubric (see Review Rubrics → Spec Review or Quality Review).
   b. Classify each finding: severity, category, confidence level (see Human Final Judgment Gate → Advisory label system).
   c. Record evidence source for each finding (observed/reported/inferred per Evidence discipline rules).
   d. Check for cross-role conflicts with previously run roles. If conflict found, mark both findings with `⚠ requires human decision`.

S7. **Aggregate findings** — Combine all role findings into a single list. Sort by priority (see Human Final Judgment Gate → Priority classification). Compute overall verdict:
   - Any blocker → `blocked`
   - Any unresolved conflict → `changes_requested`
   - Any major → `changes_requested` (unless human accepts risk via override)
   - Only minor/nit → `approved` with findings noted
   - No findings → `approved`

S8. **Write `review-report.md`** — Use `templates/review-report.md` structure. Fill all applicable sections:
   - Fill Standalone Input Source, Reviewer Role Summary, Override Log, Standalone Mode Metadata sections.
   - Set Review Type to the roles that ran. Set Safe for Next Stage based on verdict.
   - Skip inapplicable sections: Execute Micro-Gates, Route Compliance, Evolution Rule Review (see template comments).

S9. **Present verdict to human** — Output a clear summary: verdict, finding count by severity, active roles, conflicts if any. In standalone mode, never auto-proceed to ship. The review report is the end of the standalone flow.

S10. **Handle human response** — Wait for human action: dismiss, escalate, accept risk (see Human Final Judgment Gate → Override process), re-review with updated input, or start a pipeline from the review output. Record any overrides in `review-report.md` → Override Log.

## Human Final Judgment Gate

AI review results are **advisory**, not auto-approval. The review report is a structured recommendation. The human decides what to act on.

### Advisory label system

Every finding carries a confidence level that determines how it should be treated:

- **HIGH confidence** (observed evidence): Finding is based on directly inspected code, command output, or file content. The human should treat this as actionable unless they have context the reviewer doesn't.
- **MEDIUM confidence** (reported evidence): Finding is based on executor claims, CI output, or third-party reports. The human should verify before acting.
- **LOW confidence** (inferred): Finding is based on patterns, heuristics, or assumptions without direct evidence. The human should validate before acting. All evidence-less comments are LOW confidence by definition.
- **CONFLICT**: Two reviewer roles disagree. Marked with `⚠ requires human decision`. The human must resolve — the report records both positions without taking sides.

Record confidence level in each finding:
```
- **Confidence**: HIGH | MEDIUM | LOW | CONFLICT
```

### Priority classification

Findings are surfaced to the human in this priority order:

1. **Blocker** — Must be resolved before any approval. AI will never approve with open blockers.
2. **Major** — Should be resolved. AI may approve with major findings only if human explicitly accepts the risk.
3. **Conflict** (⚠) — Requires human decision regardless of severity.
4. **Minor** — Advisory. Human decides whether to address.
5. **Nit** — Low-priority suggestions. May be evidence-less observations.

### Override process

The human can override any AI finding:

- **Dismiss**: Mark a finding as `dismissed` with a reason. Record in the report: `Overridden by <human>: <reason>`.
- **Escalate**: Promote a minor/nit to major. Record: `Escalated by <human>: <reason>`.
- **Accept risk**: Accept a blocker/major as-is. Record: `Risk accepted by <human>: <reason>`. This is the only way to ship with unresolved major findings.

Overrides are recorded in `review-report.md` → **Override Log** section:
```
## Override Log
- Finding <N>: <action> by <human> — "<reason>"
```

A review with overrides must still be written to the artifact before it counts. Chat overrides without artifact updates are not binding.

### Ship gate

- Pipeline mode: Ship requires explicit human confirmation (`/forgeflow:ship`). AI `approved` verdict enables but does not execute ship unless `--auto` is active.
- Standalone mode: The review report is the final artifact. No ship stage exists unless the user explicitly starts a pipeline from the review output.
- `--auto` mode: AI may proceed to ship after `approved`, but only when all conditions are met (verdict=approved, safe_for_next_stage=yes, open_blockers=none, no unresolved conflicts). `--auto` does not override human judgment — it automates the mechanical step after judgment is complete.

## Output mode examples

If asked:

```text
/forgeflow:review Dry run only. List exactly two review checks. Do not write files. Do not run commands.
```

Return exactly two review checks. Do not add a verdict, extra commentary, or file writes.

## Telemetry

On completion of this stage, record a telemetry event to `.forgeflow/telemetry/<task-id>.md`:
- **event**: `stage_complete` on success, `stage_fail` on error/failure
- **stage**: review
- **outcome**: `success` | `partial` | `failed`
- **failure_type**: on failure, categorize as `assertion_mismatch` | `scope_creep` | `validation_error` | `adapter_error` | `timeout` | `unknown`

On scope boundary violations detected during review, record:
- **event**: `boundary_alert`
- **stage**: review

Follow `skills/_shared/discipline.md` Telemetry Event Recording for format details.
