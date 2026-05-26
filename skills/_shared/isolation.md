# Worktree Isolation Protocol

Shared protocol for creating, detecting, and cleaning up git worktrees so multiple ForgeFlow tasks can execute in parallel without source-code conflicts.

## Overview

Each ForgeFlow task (medium/high/epic route) gets its own git worktree on a dedicated branch. The worktree shares the `.git` object store with the main repository but has an independent working tree and branch. Task artifacts under `.forgeflow/` are shared via symlink so review/ship stages can access all task state from either location.

```
<project-root>                         ← main branch, clarify runs here
<project-root>/.forgeflow/worktrees/
  ├── feature-auth-a3f/                ← ff/feature-auth-a3f branch
  └── fix-api-bug-c7d/                 ← ff/fix-api-bug-c7d branch
```

## When to create

- **clarify** stage exit, when route is medium, high, or epic.
- **Not** for small route (overhead exceeds benefit for 1-2 file changes).
- **Not** when `--no-isolation` flag is set or `defaults.md` has `isolation: false`.
- Skip if the worktree already exists (idempotent — check first).

## Creation procedure

Run from the **main repository root** (`git rev-parse --show-toplevel`).

```bash
TASK_ID="<task-id>"
BRANCH="ff/${TASK_ID}"
WT_PATH=".forgeflow/worktrees/${TASK_ID}"
MAIN_ROOT="$(git rev-parse --show-toplevel)"

# 1. Create branch from current HEAD (main)
git branch "$BRANCH" HEAD

# 2. Create worktree
mkdir -p .forgeflow/worktrees
git worktree add "$WT_PATH" "$BRANCH"

# 3. Symlink .forgeflow so artifacts are shared
#    (worktree checkout won't have .forgeflow since it's gitignored)
rm -rf "${WT_PATH}/.forgeflow"
ln -s "${MAIN_ROOT}/.forgeflow" "${WT_PATH}/.forgeflow"

# 4. Verify
test "$(git -C "$WT_PATH" branch --show-current)" = "$BRANCH"
test -L "${WT_PATH}/.forgeflow"
```

Record in `brief.md` Task Isolation section:
- `isolation: worktree`
- `worktree_path: .forgeflow/worktrees/<task-id>/`
- `branch: ff/<task-id>`

## Detection

Any stage that needs to know whether it is running inside a worktree:

```bash
# .git is a file (containing "gitdir: ...") → worktree
# .git is a directory → main repository
if [ -f .git ]; then
  # worktree environment
  BRANCH=$(git branch --show-current)
  MAIN_GITDIR=$(cat .git | sed 's|gitdir: ||' | xargs dirname | xargs dirname)
  MAIN_ROOT=$(dirname "$MAIN_GITDIR")
else
  # main repository
  MAIN_ROOT=$(git rev-parse --show-toplevel)
fi
```

### Finding the main repo from a worktree

The `.git` file inside a worktree contains `gitdir: <path-to-main-repo>/.git/worktrees/<name>`. The main repo root is two directories up from that path.

## Review in a worktree

Review is read-only and can run inside the worktree. The symlinked `.forgeflow/` gives access to all task artifacts. No special handling needed beyond detecting the worktree environment.

## Cleanup (ship stage)

Run from the **main repository root** after the worktree branch is merged or discarded.

### Merge + cleanup

```bash
TASK_ID="<task-id>"
BRANCH="ff/${TASK_ID}"
WT_PATH=".forgeflow/worktrees/${TASK_ID}"

# 1. Merge branch into main
git checkout main
git merge --no-ff "$BRANCH"

# 2. Remove symlink before worktree removal
rm -f "${WT_PATH}/.forgeflow"

# 3. Remove worktree
git worktree remove "$WT_PATH"

# 4. Delete branch
git branch -d "$BRANCH"
```

### Discard + cleanup

```bash
# 1. Remove symlink
rm -f "${WT_PATH}/.forgeflow"

# 2. Force-remove worktree (discards uncommitted changes)
git worktree remove --force "$WT_PATH"

# 3. Delete branch
git branch -D "$BRANCH"
```

### Keep branch (no cleanup)

If the user selects "keep branch as-is", do not remove the worktree or branch. The user may return to it later.

## Safety rules

1. **Never `rm -rf` the `.forgeflow/` symlink inside a worktree** — use `rm -f` (no `-r`) to remove the symlink only.
2. **Never force-remove a dirty worktree without user confirmation.** If `git status --short` shows changes, ask first.
3. **Branch naming**: always prefix with `ff/` so ForgeFlow worktrees are identifiable via `git branch --list 'ff/*'` and `git worktree list`.
4. **One worktree per task**: never share a worktree between tasks.
5. **Main branch protection**: when isolation is active, the execute stage must not edit files on the main branch. If the agent detects it is on main with `isolation: worktree` in brief, warn and stop.
6. **Idempotent creation**: if `.forgeflow/worktrees/<task-id>/` already exists and the branch is correct, skip creation. Do not error or recreate.
7. **Prune stale worktrees**: before creating a new worktree, `git worktree prune` to clean up any stale references.

## Configuration

| Setting | Location | Default | Effect |
|---------|----------|---------|--------|
| `isolation` | `.forgeflow/defaults.md` | `true` | Enable worktree isolation for medium+/high/epic |
| `--no-isolation` | CLI flag | — | Disable worktree isolation for this run |

When `isolation: false` or `--no-isolation` is set, all stages run in the main repository working directory with no worktree. The user is responsible for avoiding concurrent edits.

## .gitignore

Add to project `.gitignore`:

```
.forgeflow/worktrees/
```

Worktrees are local-only and should not be shared via git.
