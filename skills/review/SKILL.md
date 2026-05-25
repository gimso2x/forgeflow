---
name: review
description: Perform independent ForgeFlow review. Use as /review or /forgeflow:review — either after execute (pipeline mode) or directly with external input (standalone mode).
version: 0.3.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must separate spec compliance findings from quality findings.
  Must not approve work with unresolved blockers or missing verification evidence.
---

# Review

Use this skill to review completed ForgeFlow work independently.

## Input

- `brief.md` from clarify stage
- `plan.md` from plan stage
- `implementation-notes.md` from execute stage
- `run-ledger.md` from execute stage
- Final codebase state
- Verification commands/results

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

3. **Diff/patch** — Input contains unified diff markers (`--- a/`, `+++ b/`, `@@`) or is provided with `--diff` flag.
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

**input-source.md** records:
- Input type detected
- Original input value (URL, path, diff snippet)
- Fetch command used (if applicable)
- Fetch result status (success/partial/failed)
- Timestamp

**normalized-input.md** records the 4-field structure (see Input Normalization below).

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
| Diff/patch | The raw diff text. Parse into per-file hunks. |
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
| Diff/patch | Files mentioned in diff headers (`---`/`+++`). |
| File bundle | The listed files only. |
| Existing artifact | The artifact itself + any referenced files that exist. |

User can narrow scope with `--scope <pattern>` (glob). Only review files matching the pattern within the detected scope.

### constraints

Review focus areas or restrictions:

- **User-specified**: `--focus security`, `--focus quality`, `--type spec`, `--type quality`. These constrain which reviewer role runs.
- **Inferred from input**:
  - PR with no description → quality review only (no spec to check against).
  - Diff with only test files → test quality review.
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

## Reviewer Roles

Standalone mode and high/epic pipeline mode use role-based review. Each role has its own checklist and produces findings independently. The review report aggregates all role findings.

### Role definitions

#### spec-reviewer

**Trigger**: Always runs in pipeline mode. In standalone mode, runs when a brief/requirement/spec document exists (auto-generated or user-provided).

**Checklist** (in addition to the Spec Review rubric):
- ☐ Every acceptance criterion has a corresponding evidence trace
- ☐ No unexplained additions beyond stated scope
- ☐ No silent removals of existing functionality
- ☐ All referenced files/paths/symbols exist in the reviewed scope
- ☐ Error handling is complete (no unchecked error paths for in-scope code)
- ☐ Public API changes are backward-compatible or explicitly breaking
- ☐ Configuration changes have migration path or are additive

**Standalone-specific**: When no explicit spec exists, the auto-generated brief becomes the de facto spec. The spec-reviewer checks whether the code/diff does what the brief describes — no more, no less. Flag scope that doesn't trace back to the brief as `major: unexplained scope`.

#### quality-reviewer

**Trigger**: Always runs in both pipeline and standalone mode.

**Checklist** (in addition to the Quality Review rubric):
- ☐ No dead code introduced (unreachable branches, unused imports, commented-out blocks)
- ☐ Naming follows existing codebase conventions (compare with nearby files)
- ☐ No magic numbers/strings — constants are named
- ☐ Error messages are actionable (tell the reader what to do, not just what failed)
- ☐ No copy-pasted blocks that should be shared utilities
- ☐ Logging follows project conventions (level, format, structured fields)
- ☐ Thread safety / concurrency issues in shared state (if applicable)

**Standalone-specific**: Without implementation-notes, the quality-reviewer works from the code/diff directly. Apply heuristics without referencing executor claims.

#### security-reviewer

**Trigger**: Runs when `--focus security` is specified, or when in-scope changes touch:
- Authentication/authorization code
- Input validation / sanitization
- Secret/key handling
- API endpoints / network boundaries
- File system operations
- Dependency additions

**Checklist**:
- ☐ No hardcoded secrets, keys, or tokens
- ☐ User input is validated and sanitized before use
- ☐ SQL queries use parameterized statements (no string interpolation)
- ☐ File paths are sanitized (no path traversal)
- ☐ Error responses don't leak internal state or stack traces
- ☐ New dependencies are from trusted sources with reasonable maintenance
- ☐ Authentication checks are present on all entry points that require them
- ☐ No eval/exec/deserialization of untrusted input

#### ux-reviewer

**Trigger**: Runs when `--focus ux` is specified, or when in-scope changes touch:
- UI component files (.tsx, .vue, .svelte, etc.)
- CSS/styling files
- User-facing text/labels/messages
- Route/page definitions
- Form handling code

**Checklist**:
- ☐ Text is clear and follows project voice/guidelines
- ☐ Error states are handled with user-facing messages
- ☐ Loading states exist for async operations
- ☐ Interactive elements have appropriate affordances
- ☐ Layout is consistent with adjacent screens
- ☐ Accessibility: ARIA labels, keyboard navigation, color contrast

#### perf-reviewer

**Trigger**: Runs when `--focus perf` is specified, or when in-scope changes touch:
- Database queries / ORM calls
- Loops over large collections
- Caching layers
- Network call batching
- Memory-intensive operations (large allocations, streaming)

**Checklist**:
- ☐ No N+1 queries in loops
- ☐ Large datasets use pagination or streaming
- ☐ Expensive computations are memoized/cached where appropriate
- ☐ No unnecessary re-renders or re-computations in reactive code
- ☐ Database indexes exist for queried columns
- ☐ No blocking I/O in async contexts

### Role routing

**Pipeline mode** (route-aware):
- small: quality-reviewer only
- medium: quality-reviewer only (medium-full may add spec-reviewer)
- high/epic: spec-reviewer (pass 1) → quality-reviewer (pass 2), sequential gates
- Any route: security/ux/perf-reviewer triggered by file-type heuristics above

**Standalone mode**:
- No `--type` flag: quality-reviewer always runs. spec-reviewer runs if brief exists. Other roles triggered by file-type heuristics.
- `--type spec`: spec-reviewer only
- `--type quality`: quality-reviewer only
- `--type security`: security-reviewer only
- `--type ux`: ux-reviewer only
- `--type perf`: perf-reviewer only
- `--type all`: run all applicable roles
- `--focus <role>`: alias for `--type <role>`

### Cross-role conflict handling

When two roles produce conflicting findings:
1. Record both findings in the report with their role label.
2. Add a `⚠ requires human decision` marker in Findings.
3. Do not resolve the conflict by choosing one side. The human final judgment gate handles this.
4. Example: spec-reviewer says "missing error handling for edge case X" (blocker) but quality-reviewer says "error handling would add unnecessary complexity" (minor). Both stay. Report shows conflict with `requires human decision`.

### Role output structure in review-report.md

Each finding includes the reviewer role:
```
- **Role**: spec-reviewer | quality-reviewer | security-reviewer | ux-reviewer | perf-reviewer
```

The report includes a **Role Summary** section:
```
## Reviewer Role Summary
- spec-reviewer: <verdict>, <N> findings (<blockers> blockers, <majors> major)
- quality-reviewer: <verdict>, <M> findings (<blockers> blockers, <majors> major)
- [other roles if triggered]
- Cross-role conflicts: <count> (marked with ⚠)
```

## Output Artifacts

Write `review-report.md` to the active task directory using `templates/review-report.md` as the structure. The report must capture:

- Review Type (spec | quality | security | ux)
- Verdict (approved | changes_requested | blocked) — never use "passed"
- Reviewer (role or identifier)
- Findings with severity (blocker | major | minor | nit) and category (spec-compliance | quality | maintainability | risk | security)
- Spec Compliance checklist (for spec review)
- Quality Assessment checklist (for quality review)
- Open Blockers (list or "none")
- Safe for Next Stage (yes | no)
- Evolution Rule Review (not_applicable — evolution rules are generated by ship)
- Execute Micro-Gates table (high/epic — summarize `micro_spec` / `micro_quality` from execute; re-verify in this pass)
- Next Action
- Approved By (only if verdict is approved)

## Review Rubrics

These rubrics are applied directly during review. Separate spec and quality reviews use their respective rubrics.

### Spec Review

Questions to answer for every spec review:
- Did the output satisfy the brief objective?
- Were acceptance criteria met?
- Did execution stay inside scope?
- Did the change avoid silent fallback, dual write, or shadow-path ownership drift?
- Is evidence sufficient for the claimed completion?

Automatic fail conditions:
- Missing acceptance coverage
- Unapproved scope drift
- Silent fallback or dual-write drift
- Evidence-free completion claim
- Approved verdict with open blockers or safe_for_next_stage=false

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

- Requirements/acceptance criteria are checked against actual files
- Tests/build/lint are considered or run where appropriate
- Critical/major findings block ship
- `review-report.md` has been written to the active task directory **before** the exit summary
- Approved review has no open blockers and is safe for next stage
- Next step is `/forgeflow:ship` only if review passes

A review that leaves no `review-report.md` is incomplete. The verdict exists only in the artifact, not in chat sentiment.

### Route-aware review behavior

All routes write a **single** `review-report.md` using `templates/review-report.md`.

- **small** route: Single quality review. Set Review Type: quality. Complete Quality Assessment; Spec Compliance may be not_applicable.
- **medium** route: Single quality review. Set Review Type: quality. Complete Quality Assessment.
  - **medium-light** (brief sub-band): Verify task coverage and verification gates; Contracts/Journeys in plan are optional unless present.
  - **medium-full** (brief sub-band): Verify contract-first traceability — every acceptance criterion maps to plan tasks; Contracts and Verification Plan targets must be checked if present in `plan.md`.
- **high/epic** route: Two separate review **passes** are **required** (same file, sequential gates):
  1. `/forgeflow:review --type spec` — Create or update `review-report.md`. Set Review Type: spec. Complete Spec Compliance and Evolution Rule Review. Record spec verdict. Do not proceed to quality until spec verdict is approved.
  2. `/forgeflow:review --type quality` — Update the same `review-report.md`. Set Review Type: quality (or note both passes in Findings). Complete Quality Assessment. Final verdict must reflect quality pass.

  For high/epic, if Spec Compliance is missing, incomplete, or spec verdict != approved, do not proceed to the quality pass. Each pass is an independent gate; do not merge both passes into one review turn.

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

Review MUST independently verify test results before approving. This is a hard gate:

1. **Run the test suite yourself.** Do not trust worker-reported pass/fail counts. Execute `npm test`, `pytest`, `make test`, or whatever test command is appropriate for the project.
2. **Parse the output.** If any test fails, the review verdict MUST be `changes_requested` — never `approved`.
3. **Record evidence.** Include the test command, total count, pass count, and fail count in findings.
4. **Flaky test disclaimer.** If tests are flaky and fail intermittently, run them once more. If they still fail, they fail. A flaky test failure is still a failure for review purposes.
5. **No test command found.** If no test command exists or tests cannot be run, record this as `reported evidence: no test command found` and note it as a minor finding. Do not treat this as a blocker, but do not claim tests pass.

This gate applies regardless of route size. Even small-route reviews must run tests if a test command is available.

### Standard verification checklist

When reviewing, run the **independent verification suite** (all that apply, minimum 1):

| Gate | Command pattern | Required when |
|------|----------------|---------------|
| build | `pnpm build` / `npm run build` / `cargo build` | All code tasks |
| lint | `pnpm lint` / `npm run lint` / `ruff check` | Lint config exists |
| type_check | `tsc --noEmit` / `mypy` / `cargo check` | Typed codebase |
| test | `pnpm test` / `npm test` / `pytest` | Tests exist for changed files |

Small routes: minimum 1 gate (build preferred). Medium+: minimum 2 gates (build + 1 other). High/epic: all applicable gates.
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

→ Compact/resume rules: `_shared/context-resume.md`.

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

## Procedure

### Step 0 — Mode detection and routing

**Pipeline mode detection**: If `brief.md`, `plan.md`, or `implementation-notes.md` exist in the active task directory (`.forgeflow/tasks/<id>/`), proceed in **pipeline mode** (steps 1-18 below).

**Standalone mode detection**: If only external input is provided (URL, diff, files, repo path), or if the user explicitly requests standalone review, enter **standalone mode** and follow the standalone procedure (steps S1-S10 below).

Do not enter standalone mode if pipeline artifacts exist, even if the user provides a URL. Pipeline artifacts take precedence.

### Pipeline mode procedure (steps 1-18)
1. Read `checkpoint.md` when present, then `_shared/preflight.md` minimum read set. Read `brief.md` Acceptance Criteria and route — not necessarily the full brief unless scope is disputed.
2. Review from artifacts and code, not worker vibes.
3. Check scope coverage and acceptance criteria, including every fulfills, journey, and verification plan target from the plan.
4. Start with blocker elimination: missing artifacts, missing observed evidence, failed verification, or unresolved open blockers force `blocked` or `changes_requested` before minor findings are considered.
5. **Run the test suite** (see Test verification gate above). If any test fails, verdict MUST be `changes_requested`.
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
    - If `approved` (no `--auto`): "리뷰 통과. 출하 준비 완료. `/forgeflow:ship`을 실행해주세요."
    - If `changes_requested`: **always stop and present findings** (auto-break). "수정이 필요합니다:" + 각 P0/P1 이슈를 `file:line — description` 형태로 나열 + "`/forgeflow:execute`로 수정 후 다시 `/forgeflow:review`를 요청해주세요."
    - Do NOT auto-proceed to ship unless `--auto` is active. 반드시 사용자가 다음 단계를 실행하도록 대기.
18. Do not call `/forgeflow:ship` unless verdict=approved, safe_for_next_stage=yes, and open_blockers=none are all true in the **written** `review-report.md`.

Do not merge spec and quality review passes into a single turn for high/epic work. Use one `review-report.md` with sequential passes.

### Standalone mode procedure (steps S1-S10)

S1. **Detect input type** — Apply input type detection (see Standalone Mode → Input type detection). If detection fails, ask the user to clarify. Do not proceed with a guess.

S2. **Fetch/extract input** — Execute the appropriate fetch command for the detected type:
   - URL: Run `gh pr diff`, `gh api`, `web_extract`, or `curl` as appropriate.
   - Repo path: Run `git diff`, `git log`, `git show` as appropriate.
   - Diff/patch: Parse hunks directly from input.
   - File bundle: Read each file.
   - Existing artifact: Read artifact content.
   - Record fetch result in `input-source.md` (success/partial/failed + what was retrieved).

S3. **Normalize input** — Generate the 4-field normalized structure (brief, evidence, scope, constraints) using the Input Normalization rules. Write to `normalized-input.md`. If normalization produces empty evidence, block: `blocked: input normalization failed — no evidence extracted`.

S4. **Bootstrap synthetic task directory** — Create `.forgeflow/tasks/standalone-<YYYYMMDD-HHMMSS>/` with `input-source.md` and `normalized-input.md`. This directory is the task root for the rest of the procedure.

S5. **Determine reviewer roles** — Apply role routing (see Reviewer Roles → Role routing):
   - Check `--type` flag if present.
   - If no flag: quality-reviewer always runs. spec-reviewer runs if brief exists. security/ux/perf triggered by file-type heuristics.
   - Record active roles in `normalized-input.md` constraints.

S6. **Run each active reviewer role** — For each active role:
   a. Apply the role's checklist against the normalized evidence.
   b. Classify each finding: severity, category, confidence level.
   c. Record evidence source for each finding (observed/reported/inferred).
   d. Check for cross-role conflicts with previously run roles.
   e. If conflict found, mark both findings with `⚠ requires human decision`.

S7. **Aggregate findings** — Combine all role findings into a single list. Sort by priority:
   1. Blockers (all roles)
   2. Conflicts (⚠)
   3. Major findings
   4. Minor findings
   5. Nits
   Compute overall verdict:
   - Any blocker → `blocked`
   - Any unresolved conflict → `changes_requested`
   - Any major → `changes_requested` (unless human accepts risk via override)
   - Only minor/nit → `approved` with findings noted
   - No findings → `approved`

S8. **Write `review-report.md`** — Use `templates/review-report.md` structure. Fill all sections:
   - Set Review Type to the primary role that ran, or list all roles.
   - Include **Reviewer Role Summary** section (see Reviewer Roles → Role output structure).
   - Skip sections that don't apply: Execute Micro-Gates, Evolution Rule Review, Route Compliance.
   - Add **Standalone Input Source** section at the top with input type, original input, and fetch status.
   - Set Safe for Next Stage based on verdict (yes only if approved with no open blockers/conflicts).

S9. **Present verdict to human** — Output a clear summary:
   - Verdict, finding count by severity, active roles, conflicts if any.
   - If `blocked` or `changes_requested`: list blockers/conflicts/majors with `file:line — description`.
   - If `approved`: note minor/nit findings, state that the review report is the final artifact.
   - In standalone mode, never auto-proceed to ship. The review report is the end of the standalone flow.

S10. **Handle human response** — Wait for human action:
   - Human may dismiss, escalate, or accept risk on any finding (see Override process).
   - Human may request re-review after changes: start a new standalone review with updated input.
   - Human may start a pipeline from the review output: `/forgeflow:clarify` with the review report as input.
   - Record any overrides in `review-report.md` → Override Log.

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
