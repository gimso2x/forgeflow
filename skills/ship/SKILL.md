---
name: ship
description: "Finalize ForgeFlow work after review: summarize, verify, prepare PR/commit handoff, preserve evidence, extract evolution rules, and handle branch disposition. Use when the user types /ship or /forgeflow:ship. Also use when the user says 'wrap up', 'finalize', 'merge', 'create PR', 'ship it', or 'finish up' after implementation work."
version: 0.4.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must confirm review approval, intended diff scope, and final verification before shipping.
  Must not hide residual risks or unrelated dirty working tree changes.
  Must require fresh verification, git status, git diff, review evidence, and residual risk review before presenting finish options.
  Must present safe outcomes: merge locally, push and create PR, keep branch, or discard work. Worktree isolation may add cleanup-only mode.
  Must never run destructive cleanup, branch deletion, or discard without explicit confirmation.
dependencies:
  - skills/_shared/discipline.md
  - skills/_shared/automation.md
  - skills/_shared/isolation.md
  - skills/_shared/context-resume.md
  - skills/_shared/preflight.md
---

# Ship

Use this skill to prepare the final handoff after review passes, extract reusable evolution rules, and handle branch disposition (merge/PR/keep/discard).

> **Terminology:** "finish" is not a separate stage. It refers to branch disposition within ship (merge, PR, keep, or discard).

## Ship phases

1. **Handoff summary**: Write `ship-summary.md`, extract evolution rules
2. **Branch disposition**: Verify, present options, handle user choice

## Input

- Approved `review-report.md` or equivalent review verdict
- `brief.md` if available
- `plan.md` if available
- `implementation-notes.md` if available
- `implementation-notes.md Decisions` if available (for tracing decisions that may affect evolution rule extraction)
- `eval-record.md` if available (from long-run, high/epic routes)
- Git diff/status
- Verification evidence

## Output Artifacts

Write a `ship-summary.md` in the active task directory using `templates/ship-summary.md` as the structure. The summary must capture:

- Changed files
- Verification commands and results
- Review verdict
- Residual risks
- Handoff action: report completed; branch disposition resolved (merge/PR/keep/discard)
- Quantitative summary (from execute metrics)

Evolution rule artifacts (optional, when reusable patterns are found):

- `~/.forgeflow/evolution/active/<rule-name>.md` for global-advisory scope
- `.forgeflow/evolution/active/<rule-name>.md` for project scope

Post-review harness improvement tickets (optional, when human review surfaced process gaps):

- `<task-dir>/harness-improvement-tickets.md` — ticket candidates extracted from human review discussion and artifacts; these are harness/docs/prompt improvements, not direct product-code edits.

## Exit Condition

- Working tree state is understood
- Final verification is green or failures are explicitly documented
- Review verdict permits shipping
- Final handoff is completed
- User gets a concise final report
- Branch disposition has been resolved (user selected one of: merge, PR, keep, discard) or user explicitly deferred

## Constraints

## File write and output discipline

→ Core rules: `_shared/discipline.md`.

Follow the user language rules there: write user-facing replies and artifact prose in the user's primary language, while preserving canonical English labels, commands, paths, artifact filenames, and enum values.

Ship should preserve the final handoff evidence in the active task directory.

When artifacts such as `review-report.md` or final handoff notes are mentioned without an explicit path, preserve them under the active task directory, not the repository root and not chat-only fallback.

## Strict response constraints

→ `_shared/discipline.md`.

Bad: adding verdicts, extra rationale sections, or warnings after the requested list.
Good: if asked for exactly two checks, return exactly two checks.

Example exact-count response must be plain text lines, not a fenced block:

1. Confirm the approved README badge change is the only intended ship item.
2. Confirm the final handoff summary names the badge change and any residual risk.

No heading. No preamble. No code fence. No third line.

## Status analysis preflight

→ `_shared/preflight.md` (checkpoint-first, section-targeted reads).

→ `_shared/context-resume.md`.

- **Minimum read set**: checkpoint → `review-report.md` Reader Summary + Verdict + Open Blockers → `ship-summary.md` draft if present.
- Expand `plan.md`, full `implementation-notes.md`, or `brief.md` only when handoff, evolution extraction, or verification gaps require it.
- Do not re-read all task artifacts by default before shipping.

## Resume from checkpoint preflight

세션이 중단된 후 ship을 재개할 때, checkpoint.md를 먼저 읽어 자동 복구를 시도한다:

1. `checkpoint.md`의 `Next Action`에 `/forgeflow:ship`이 포함되어 있고 `ship-summary.md`가 존재하지 않으면 → ship을 실행한다 (별도 확인 불필요).
2. `checkpoint.md`의 `Current Stage`가 `review`이고 `review-report.md`의 verdict가 `approved`이면 → ship을 실행한다.
3. `checkpoint.md`의 `Status`가 `blocked`이면 → blockers를 먼저 확인하고 사용자에게 보고한다.

이 복구 메커니즘은 auto-chain이 중간에 끊긴 경우(예: 컨텍스트 한도, 세션 종료)에 특히 중요하다.

## Evolution rule extraction

Ship is the evolution rule generation point for all routes. Read `skills/ship/references/evolution-extraction.md` before deciding whether to extract reusable rules, choosing global-advisory vs project scope, handling mandatory extraction triggers, or writing active evolution rule files.

Keep generated rules evidence-backed by review-approved task artifacts. Skip small-route extraction unless explicitly requested, and never create rules from vague sentiment, session chatter, or one-off observations.

## SOFT→HARD auto-promotion check

After extracting evolution rules, check if any advisory (soft) rules have reached the promotion threshold:

1. Run `python3 scripts/forgeflow_evolution_promote.py list-failures` to see current failure counts.
2. For each advisory rule extracted in this session, run `python3 scripts/forgeflow_evolution_promote.py check-promote --rule <rule-id>`.
3. If a rule is auto-promoted (exit 2), inform the user:
   - Which rule was promoted
   - The advisory path → hard rule path
   - That Claude Code hooks can now enforce it via `scripts/forgeflow_hook_check.sh`
4. If promotion is premature, the user can manually promote later with `python3 scripts/forgeflow_evolution_promote.py promote --rule <rule-id>`.

When a review or execution failure occurs (verification retry ≥ 2, scope boundary violation, workaround applied), record it:
- `python3 scripts/forgeflow_evolution_promote.py record-fail --rule <rule-id>`

This enables the closed-loop principle: failure → rule extraction → hard enforcement → compound learning.

## Fact Extraction (Memory Bank L4)

After evolution rule extraction and SOFT→HARD promotion, extract structured facts from task artifacts into the ForgeFlow Memory Bank.

**Route-aware extraction:**
- **small**: Skip fact extraction.
- **medium**: Maximum 3 facts. Only high-confidence items.
- **high/epic**: Full extraction. No hard limit.

**Extraction sources:**
- `implementation-notes.md Decisions` → type `decision` (architectural choices, tradeoffs)
- `implementation-notes.md` deviations/workarounds → type `pattern` or `bug_fix`
- `review-report.md` findings → type `constraint` or `discovery`
- User preferences expressed during task → type `preference`

**Quality criteria:**
- Each fact must have a concrete source artifact (not vague sentiment).
- Content must be a self-contained statement reusable in future tasks.
- Assign a domain: auth, api, ui, infra, testing, project, architecture, tooling, general.
- Assign confidence: high (verified by review), medium (observed pattern), low (preliminary).

**Command:**
```bash
python3 scripts/forgeflow_fact_store.py add \
  --content "<fact statement>" \
  --type <decision|constraint|preference|pattern|bug_fix|discovery> \
  --domain <domain> \
  --confidence <high|medium|low> \
  --source-task <task-id> \
  --tags <comma-separated>
```

**Skip when:** No reusable knowledge was produced (trivial fixes, pure formatting, no decisions).

## Procedure

1. Check git status and diff only if command execution is allowed.
2. Run final verification only if command execution is allowed.
3. Ensure review passed; do not ship blocked work.
4. **Human Review Gate preflight**: Inspect `review-report.md` for `Human Review Gate`.
   - If `Decision: required`, do not ship until `Human Decision Status` records the human decision and the handoff target is `ship`.
   - If `Decision: skipped`, require a skip rationale tied to the review gate criteria.
   - If the section is missing on older artifacts, treat this as a review artifact gap and route back to `/forgeflow:ff-review` unless the task is explicitly legacy/no-risk and the reviewer records a skip rationale.
5. Confirm there is no unresolved blocker, and that handoff evidence is preserved in the active task directory before preparing the final summary.

6. **Artifact completeness gate**: Before writing final handoff language, inspect `review-report.md`, `implementation-notes.md`, and the draft/final `ship-summary.md` for unresolved template residue. If `TODO`, `TBD`, `FIXME`, unresolved `<!-- ... -->`, or angle-bracket placeholders such as `<task-id>`, `<branch-name>`, or `<...>` remain as artifact-writing residue, stop and route back to `/forgeflow:execute` or `/forgeflow:ff-review`. Do not preserve unfinished placeholders as ship evidence. Intentional Markdown checkboxes, code snippets, command output, or literal examples are not blockers by themselves.

7. **Final Polish and Simplification Loop**: Analyze the **actually changed code** (`git diff HEAD~1 HEAD` or equivalent) for quality before shipping. This is a read-first analysis: if modifications are needed, hand back to execute rather than editing code during ship.

#### Analysis (read-only)

- **Phase 1: Identification**: Focus exclusively on the diff. Ignore noise from unrelated files.
- **Phase 2: Triple-Lens Analysis**:
    - **Lens 1 (Code Reuse)**: Identify new logic that duplicates existing utils, constants, or types.
    - **Lens 2 (Code Quality)**: Identify stringly-typed code, redundant wrappers, and abstraction boundary violations.
    - **Lens 3 (Efficiency)**: Identify hot-path inefficiencies, missed concurrency, and redundant resource reads.

#### If issues found

If the Triple-Lens analysis identifies meaningful improvements:
- Record each finding in `ship-summary.md` under a "Simplification candidates" section.
- **Always ask the user** (auto-break, even under `--auto`): "품질 개선 후보가 발견되었습니다. `/forgeflow:execute`로 돌아가 수정하시겠습니까? (y/n)"
- Do NOT modify code during ship. Ship is verification + handoff, not implementation.

#### If no issues found

Proceed to the final summary step directly.
If `--auto` is active (see `_shared/automation.md`), proceed to branch disposition automatically after writing `ship-summary.md`.

8. **Extract evolution rules**: Review task artifacts for reusable patterns. For each valid candidate:
   1. Check existing active rules (`~/.forgeflow/evolution/active/` and `.forgeflow/evolution/active/`) for duplicates.
   2. Determine scope: global-advisory (default) or project (project-specific architecture only).
   3. Write the rule in **compact format** (6 lines, no `.md` extension) directly to the matching `active/` directory:
      ```
      # <rule-id>
      <one-line summary>
      Trigger: <when to apply>
      Stage: <clarify | plan | execute | review | multiple>
      Mode: <advisory | required_project_rule>
      Apply: <what to do when trigger matches>
      Skip: <when NOT to apply>
      ```
   4. Global → `~/.forgeflow/evolution/active/<rule-name>`, Project → `.forgeflow/evolution/active/<rule-name>`. Create directories if they do not exist.
   5. Report what rules were created and why.

9. Write `ship-summary.md` to the active task directory. Include the Quantitative Summary section with metrics from `implementation-notes.md` → Metrics.
10. Preserve artifacts/evidence instead of burying them in chat.

## Branch Disposition (final phase)

After writing `ship-summary.md` and evolution rules, handle branch disposition.

### Worktree preflight (before verification)

→ Full protocol: `_shared/isolation.md`.

Detect worktree isolation from `brief.md` Task Isolation section (`isolation: worktree`) or by checking `test -f .git` (worktree) vs `test -d .git` (main repo).

1. **Check for active git worktree**: `git worktree list` to find the worktree location, branch, and dirty state.
2. **Do not remove or discard yet**: Before the user selects a finish option, record the worktree as preserved. `git worktree remove`, branch deletion, reset, and discard remain destructive actions that require the option-specific confirmation below.
3. **If completed worker worktrees need merging**: Treat this as part of the eventual "Merge locally" path, not as an automatic preflight side effect. First verify worker artifacts under `resolved task directory (`~/.forgeflow/projects/<project-slug>/tasks/<id>/` by default)workers/`, then present the merge plan with the exact branch/path.
4. **If the user later chooses "Keep the branch as-is"**: Leave the worktree in place and note it as preserved in the finish report.

### Verify before branch disposition

Run or inspect fresh verification before presenting success language:

```bash
git status --short
git diff --stat
```

If `git status --short` is not empty, stop before offering merge or PR as ready. Uncommitted, staged, or untracked changes require a separate preflight decision first:

1. Show the exact dirty file list and classify intended task files vs unrelated dirty files.
2. Ask whether to prepare a commit, stash/preserve the changes, keep the branch as-is, or discard in scope.
3. If the user chooses commit preparation, show the exact files to stage and exclude unrelated files. Do not run `git add`, commit, merge, push, or PR creation until the user explicitly approves that file list and commit step.
4. If the user chooses discard, follow the exact `discard` confirmation rule below.

Then run the project-specific check, for example:

```bash
pnpm test
pnpm lint
npm test
pytest -q
make validate
```

If verification fails, stop. Do not offer merge/PR as if the branch is ready.

### Confirm review and scope

Check:

- `review-report.md` approved if this workflow requires review
- For **high/epic** routes: `review-report.md` must show both Spec Compliance and Quality Assessment completed with no open blockers from either pass
- Intended files changed
- Generated artifacts updated if relevant
- Residual risks are named
- Unrelated dirty working tree changes are preserved and not swept into the finish action

### Determine base branch

Prefer the repo default branch when obvious:

```bash
git symbolic-ref refs/remotes/origin/HEAD
```

Fallback candidates:

```text
main
master
```

If the base branch is ambiguous, ask before merging or opening a PR.

Base branch is ambiguous when any of these are true:

- `origin/HEAD` is not set or cannot be resolved.
- Both `main` and `master` exist and neither is clearly the repository default.
- The current branch is `main` or `master`, but another default-like branch also exists.
- The user, brief, or review artifacts name a different base branch than the repository signals.

When ambiguous, stop and ask the user to choose the exact base branch. Do not present `Merge locally` or `Push and create a Pull Request` as ready-to-run options until the base branch is confirmed. `Keep the branch as-is` remains safe to offer.

### Cleanup-only mode (`--cleanup-only`)

When `--cleanup-only` is passed, skip summary writing, evolution rules, and branch disposition choice. Only clean up a worktree whose branch is already merged. Use this to resume a `partial` ship or clean up orphaned worktrees.

Prerequisites:
- `brief.md` Task Isolation section must have `isolation: worktree` and `branch`/`worktree_path`.
- The feature branch must already be merged into the base branch (`git branch --merged <base-branch>`).

Procedure:
```bash
MAIN_ROOT="$(git rev-parse --show-toplevel)"
WT_PATH="<worktree-path from brief.md>"
BRANCH="<branch from brief.md>"

# 1. Move to main repo
cd "$MAIN_ROOT"

# 2. Verify branch is merged
if git branch --merged HEAD | grep -q "$BRANCH"; then
  # 3. Remove symlink
  rm -rf "${WT_PATH}/.forgeflow"
  # 4. Remove worktree
  git worktree remove "$WT_PATH"
  # 5. Delete branch
  git branch -d "$BRANCH"
  echo "Cleanup complete: worktree and branch removed."
else
  echo "Branch $BRANCH is not merged. Cannot cleanup-only. Use full ship for branch disposition."
fi
```

If the branch is not merged, stop and suggest running full `/forgeflow:ship` instead.

### Present disposition options

Branch disposition differs by isolation mode.

#### Worktree isolation (`isolation: worktree`)

Under `--auto`: proceed directly to **Merge locally** without prompting. Execute merge + worktree cleanup automatically.

Without `--auto`: present the 4-option choice.

```text
구현과 검증이 끝났습니다. 브랜치를 어떻게 처리할지 결정해주세요.

1. 로컬에서 <base-branch>로 병합 (Merge locally)
2. 원격에 push하고 Pull Request 생성 (Push and create a Pull Request)
3. 현재 브랜치를 그대로 유지 (Keep the branch as-is)
4. 이번 작업 폐기 (Discard this work)

어떤 방식으로 마무리할까요?
```

#### Non-worktree (small route / `--no-isolation` / working directly on main)

No branch disposition needed — changes are already on the current branch. Skip the 4-option prompt entirely and proceed to finish report:

1. Verify all changes are committed. If dirty files exist, commit them first (under `--auto`, commit automatically; otherwise ask).
2. Output finish report directly. No merge, no cleanup, no PR needed.

```text
구현과 검증이 끝났습니다. 변경사항이 <branch-name>에 커밋되었습니다.
```

The option labels must remain recognizable, either as the visible label or the parenthesized canonical label:

- Merge locally
- Push and create a Pull Request
- Keep the branch as-is
- Discard this work

Do not add a fifth path. That is how branches become archaeology.

## Option handling

### 1. Merge locally

Only after explicit choice (or implicit under --auto):

```bash
git checkout <base-branch>
git pull --ff-only
git merge <feature-branch>
<fresh verification command>
```

If verification passes after merge, offer branch cleanup. Do not delete the branch automatically unless the user asked for cleanup.

**Worktree cleanup** (when `isolation: worktree`): after merge succeeds, clean up:
```bash
# 1. Move to main repo before removing worktree
cd <main-repo-root>

# 2. Remove .forgeflow directory (individual symlinks, safe to rm -rf)
rm -rf <worktree-path>/.forgeflow
git worktree remove <worktree-path>
git branch -d <feature-branch>
```
After cleanup, the current working directory is the main repo root. Inform the user that the worktree has been removed and the session is now on `<base-branch>`.
If the feature branch is the `<task-id>` worktree branch, remove the worktree and branch together.

### 2. Push and create a Pull Request

Only after explicit choice:

```bash
git push -u origin <feature-branch>
gh pr create --base <base-branch> --head <feature-branch>
```

PR body must include:

- Summary
- Verification evidence
- Review evidence
- Residual risks
- Related issue/plan if available

### 3. Keep the branch as-is

Report:

```text
Keeping branch <branch-name> as-is.
No merge, push, cleanup, or discard performed.
```

This is often the safest option when the working tree contains unrelated dirty files.

### 4. Discard this work

Discard is destructive. Explain the scope in the user's primary language, but keep the exact confirmation token `discard`. For Korean users:

```text
다음 작업을 영구적으로 폐기합니다:
- Branch: <branch-name>
- Commits not on <base-branch>: <commit-list>
- Worktree path, if any: <path>
- Uncommitted changes in scope: <file-list>

정말 폐기하려면 `discard`를 정확히 입력하세요.
Type 'discard' to confirm.
```

Never delete a branch, remove a worktree, reset hard, clean files, or discard commits unless the user types exactly:

```text
discard
```

Never delete unrelated dirty working tree files. If unrelated dirty working tree changes exist, stop and ask for a narrower cleanup plan.

**Worktree discard** (when `isolation: worktree`): after `discard` confirmation:
```bash
rm -rf <worktree-path>/.forgeflow    # directory with individual symlinks
git worktree remove --force <worktree-path>
git branch -D <feature-branch>
```

## Safety rules

- **`--auto` branch disposition by isolation mode**:
  - **Worktree**: merge + cleanup automatically. No 4-option prompt.
  - **Non-worktree**: changes are already on the current branch. Commit if needed, then finish report. No merge needed.
  - The `discard` confirmation always requires exact `discard` input regardless of auto mode.
- **`--auto` must complete cleanup**: Under `--auto`, the chain must not end at `partial` ship. If merge succeeds but cleanup cannot complete (e.g. dirty worktree), record the blocker in `checkpoint.md` with `Status: blocked` and `Next Action: /forgeflow:ship --cleanup-only` so it can be resumed. Do not silently leave the worktree in place.
- **Partial ship resume**: When resuming a session where ship was `partial`, read `checkpoint.md` first. If `Next Action` contains `cleanup pending`, run cleanup-only logic without re-running the full ship flow.
- Never run `git reset --hard` as a shortcut for finishing.
- Never run `git clean -fd` unless the user explicitly named the exact disposable paths.
- Never force-push as part of ship unless explicitly requested.
- Never include unrelated dirty working tree changes in a commit or PR.
- Never infer discard approval from "ok", "sure", "go", or "yes". Require the exact word `discard`.

## Blocked branch disposition examples

```text
Cannot finish yet: verification failed.
Command: pytest -q
Exit code: 1
Next action: fix failing tests before merge or PR.
```

```text
Cannot finish yet: unrelated dirty working tree changes exist.
Files:
- package-lock.json
- download.html
Next action: commit/stash/preserve those separately, or choose Keep the branch as-is.
```

## Output mode examples

If asked:

```text
/forgeflow:ship Dry run only. List exactly two ship checks. Do not write files. Do not run commands.
```

Return exactly two ship checks. Do not add command equivalents, git actions, artifact writes, or a final verdict unless requested.

## Telemetry

On completion of this stage, record a telemetry event to `<telemetry-dir>/<task-id>.md`:
- **event**: `stage_complete` on success, `stage_fail` on error/failure
- **stage**: ship
- **outcome**: `success` | `partial` | `failed`
- **failure_type**: on failure, categorize as `merge_conflict` | `ci_failure` | `scope_exceeded` | `validation_error` | `adapter_error` | `timeout` | `unknown`

After successful ship completion, run telemetry aggregation:
```
python3 scripts/telemetry_aggregate.py
```
This refreshes `~/.forgeflow/projects/<project-slug>/telemetry/summary.md` (default resolved telemetry summary) with updated metrics.

Follow `skills/_shared/discipline.md` Telemetry Event Recording for format details.
