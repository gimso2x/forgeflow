---
name: finish
description: Finish a ForgeFlow development branch safely after implementation and review by verifying evidence, presenting merge/PR/keep/discard options, and protecting destructive actions. Use when the user types /finish or /forgeflow:finish.
version: 0.2.0
author: gimso2x
validate_prompt: |
  Must require fresh verification, git status, git diff, review evidence, and residual risk review before presenting finish options.
  Must present exactly four safe outcomes: merge locally, push and create PR, keep branch, or discard work.
  Must never run destructive cleanup, branch deletion, or discard without explicit confirmation.
---

# Finish

Use this skill when implementation is complete and the remaining question is how to end the branch/worktree cleanly.

This is not the same as `ship`:

- `ship` prepares the final handoff summary.
- `finish` decides branch disposition: merge, PR, keep, or discard, and requires explicit user direction.

Explain this distinction in the user's primary language before asking for a branch disposition choice.

## Input

- Current branch name
- Base branch candidate
- `git status` output
- `git diff` / `git diff --stat` scope
- Fresh verification evidence
- Approved `review-report.md` or equivalent review verdict, if required
- Residual risks and unrelated dirty working tree changes
- User preference for local merge vs PR vs keep

## Output Artifacts

Present a finish decision report containing:

- Branch and base branch
- Verification command and result
- Review status
- Diff scope summary
- Unrelated dirty working tree notes
- Residual risks
- Selected finish option
- Exact next command sequence, or confirmation prompt for destructive actions

## Exit Condition

- Fresh verification has passed, or blocked/failed verification is stated plainly
- Review status is understood
- Diff scope is understood
- The user has chosen one finish option
- No destructive action runs without explicit confirmation

## Constraints

## File write and output discipline

→ Core rules: `_shared/discipline.md`.

Follow the user language rules there: write user-facing replies and finish decision reports in the user's primary language, while preserving canonical English option labels, commands, paths, artifact filenames, and enum values.

Use `.forgeflow/tasks/<task-id>/` for any task-local finish evidence unless the user provides another project-local artifact directory.

## Status analysis preflight

→ `_shared/preflight.md`.

Finish-specific additions: Cross-check `run-ledger.md`: all tasks must be `done` or explicitly `blocked` (with documented rationale). If any task is still `running` or `pending`, flag it as incomplete before presenting finish options. The run-ledger is the execution truth.

## Procedure

### 0. Worktree preflight (before verification)

If the task used worktree isolation (check `brief.md` for worktree references or look for a `.worktree` marker file in the task directory):

1. **Check for active git worktree**: `git worktree list` to find the worktree location, branch, and dirty state.
2. **Do not remove or discard yet**: Before the user selects a finish option, record the worktree as preserved. `git worktree remove`, branch deletion, reset, and discard remain destructive actions that require the option-specific confirmation below.
3. **If completed worker worktrees need merging**: Treat this as part of the eventual "Merge locally" path, not as an automatic preflight side effect. First verify worker artifacts under `.forgeflow/tasks/<id>/workers/`, then present the merge plan with the exact branch/path.
4. **If the user later chooses "Keep the branch as-is"**: Leave the worktree in place and note it as preserved in the finish report.

### 1. Verify before finishing

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

### 2. Confirm review and scope

Check:

- `review-report.md` approved if this workflow requires review
- For **high/epic** routes: `review-report.md` must show both Spec Compliance and Quality Assessment completed with no open blockers from either pass
- Intended files changed
- Generated artifacts updated if relevant
- Residual risks are named
- Unrelated dirty working tree changes are preserved and not swept into the finish action

### 3. Determine base branch

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

### 4. Present exactly four options

Use the user's primary language for the prompt while preserving the canonical English option label in parentheses. For Korean users, use this wording unless the user requested a stricter format:

```text
구현과 검증이 끝났습니다. `ship`은 인수인계 요약이고, `finish`는 현재 브랜치를 어떻게 처리할지 결정하는 단계입니다.

1. 로컬에서 <base-branch>로 병합 (Merge locally)
2. 원격에 push하고 Pull Request 생성 (Push and create a Pull Request)
3. 현재 브랜치를 그대로 유지 (Keep the branch as-is)
4. 이번 작업 폐기 (Discard this work)

어떤 방식으로 마무리할까요?
```

The option labels must remain recognizable, either as the visible label or the parenthesized canonical label:

- Merge locally
- Push and create a Pull Request
- Keep the branch as-is
- Discard this work

Do not add a fifth path. That is how branches become archaeology.

## Option handling

### 1. Merge locally

Only after explicit choice:

```bash
git checkout <base-branch>
git pull --ff-only
git merge <feature-branch>
<fresh verification command>
```

If verification passes after merge, offer branch cleanup. Do not delete the branch automatically unless the user asked for cleanup.

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

## Safety rules

- **`--auto` does not skip any finish confirmations.** The 4-option choice (merge/PR/keep/discard) and the exact `discard` confirmation always require explicit user input, even when `--auto` is active (see `_shared/automation.md`). `--auto` only ensures finish is invoked automatically after ship.
- Never run `git reset --hard` as a shortcut for finishing.
- Never run `git clean -fd` unless the user explicitly named the exact disposable paths.
- Never force-push as part of finish unless explicitly requested.
- Never include unrelated dirty working tree changes in a commit or PR.
- Never infer discard approval from "ok", "sure", "go", or "yes". Require the exact word `discard`.

## Blocked finish examples

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
