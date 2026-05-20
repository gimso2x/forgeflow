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

## File write and output discipline

→ Core rules: `_shared/discipline.md`.

Use `.forgeflow/tasks/<task-id>/` for any task-local finish evidence unless the user provides another project-local artifact directory.

## Status analysis preflight

→ `_shared/preflight.md`.

Finish-specific additions: Cross-check `run-ledger.md`: all tasks must be `done` or explicitly `blocked` (with documented rationale). If any task is still `running` or `pending`, flag it as incomplete before presenting finish options. The run-ledger is the execution truth.

## Procedure

### 0. Worktree cleanup (before verification)

If the task used worktree isolation (check `brief.md` for worktree references or look for a `.worktree` marker file in the task directory):

1. **Check for active git worktree**: `git worktree list` to find the worktree location.
2. **Merge completed worker worktrees**: If worker artifacts under `.forgeflow/tasks/<id>/workers/` show completed workers, merge the worktree branch back to the main working directory:
   ```bash
   cd <main-repo>
   git merge <worktree-branch>
   ```
3. **Verify merge succeeded**: After merge, check that the original repo has the expected changes:
   ```bash
   git diff --stat
   git status --short
   ```
4. **Remove worktree**: After successful merge (or if user chose "discard"), clean up the git worktree:
   ```bash
   git worktree remove <worktree-path>
   ```
5. **If user chose "keep"**: Leave the worktree in place but note it as preserved in the task directory.

### 1. Verify before finishing

Run or inspect fresh verification before presenting success language:

```bash
git status --short
git diff --stat
```

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

### 4. Present exactly four options

Use this wording unless the user requested a stricter format:

```text
Implementation complete. What would you like to do?

1. Merge locally into <base-branch>
2. Push and create a Pull Request
3. Keep the branch as-is
4. Discard this work

Which option?
```

The option labels must remain recognizable:

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

Discard is destructive. Require exact confirmation:

```text
This will permanently discard:
- Branch: <branch-name>
- Commits not on <base-branch>: <commit-list>
- Worktree path, if any: <path>
- Uncommitted changes in scope: <file-list>

Type 'discard' to confirm.
```

Never delete a branch, remove a worktree, reset hard, clean files, or discard commits unless the user types exactly:

```text
discard
```

Never delete unrelated dirty working tree files. If unrelated dirty working tree changes exist, stop and ask for a narrower cleanup plan.

## Safety rules

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
