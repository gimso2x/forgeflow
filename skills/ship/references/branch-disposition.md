# Branch Disposition

> Reference for ship's branch disposition phase. Extracted from ship SKILL.md.

## Worktree preflight (before verification)

→ Full protocol: `_shared/isolation.md`.

Detect worktree isolation from `brief.md` Task Isolation section (`isolation: worktree`) or by checking `test -f .git` (worktree) vs `test -d .git` (main repo).

1. **Check for active git worktree**: `git worktree list` to find the worktree location, branch, and dirty state.
2. **Do not remove or discard yet**: Before the user selects a finish option, record the worktree as preserved. `git worktree remove`, branch deletion, reset, and discard remain destructive actions that require the option-specific confirmation below.
3. **If completed worker worktrees need merging**: Treat this as part of the eventual "Merge locally" path, not as an automatic preflight side effect. First verify worker artifacts under the resolved task directory (`~/.forgeflow/projects/<project-slug>/tasks/<id>/` by default, `workers/` subdirectory), then present the merge plan with the exact branch/path.
4. **If the user later chooses "Keep the branch as-is"**: Leave the worktree in place and note it as preserved in the finish report.

## Verify before branch disposition

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

## Confirm review and scope

Check:

- `review-report.md` approved if this workflow requires review
- For **high/epic** routes: `review-report.md` must show both Spec Compliance and Quality Assessment completed with no open blockers from either pass
- Intended files changed
- Generated artifacts updated if relevant
- Residual risks are named
- Unrelated dirty working tree changes are preserved and not swept into the finish action

## Determine base branch

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

## Cleanup-only mode (`--cleanup-only`)

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

## Present disposition options

Branch disposition differs by isolation mode.

### Worktree isolation (`isolation: worktree`)

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

### Non-worktree (small route / `--no-isolation` / working directly on main)

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
