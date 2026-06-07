# Worktree Isolation Protocol

Shared protocol for creating, detecting, and cleaning up git worktrees so multiple ForgeFlow tasks can execute in parallel without source-code conflicts.

## Overview

Each ForgeFlow task (medium/high/epic route) gets its own git worktree on a dedicated branch. The worktree shares the `.git` object store with the main repository but has an independent working tree and branch. Worktree directories and task artifacts live under the resolved global project storage root, not under the project repository root.

```
<project-root>                         ← main branch, clarify runs here
~/.forgeflow/projects/<project-slug>/worktrees/
  ├── feature-auth-a3f/                ← feature-auth-a3f branch
  └── fix-api-bug-c7d/                 ← fix-api-bug-c7d branch
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
BRANCH="<branch-name>"  # Human-readable: <type>/<YYYYMM>-<korean-description>
MAIN_ROOT="$(git rev-parse --show-toplevel)"
STORAGE_ROOT="$(python3 /path/to/forgeflow/scripts/forgeflow_storage.py --project-dir "$MAIN_ROOT" --print storage-root)"
WT_PATH="${STORAGE_ROOT}/worktrees/${TASK_ID}"

# 1. Create branch from current HEAD (main)
git branch "$BRANCH" HEAD

# 2. Create worktree
mkdir -p "${STORAGE_ROOT}/worktrees"
git worktree add "$WT_PATH" "$BRANCH"

# 3. Link resolved ForgeFlow storage artifacts into the worktree only when a
#    tool requires .forgeflow-compatible paths. DO NOT create or inspect
#    <project-root>/.forgeflow/*.
mkdir -p "${WT_PATH}/.forgeflow"
for item in tasks telemetry evolution tmp-assets; do
  if [ -e "${STORAGE_ROOT}/${item}" ]; then
    ln -sf "${STORAGE_ROOT}/${item}" "${WT_PATH}/.forgeflow/${item}"
  fi
done
for file in defaults.md project-draft.md; do
  if [ -f "${STORAGE_ROOT}/${file}" ]; then
    ln -sf "${STORAGE_ROOT}/${file}" "${WT_PATH}/.forgeflow/${file}"
  fi
done

# 4. Verify
test "$(git -C "$WT_PATH" branch --show-current)" = "$BRANCH"
test -d "${WT_PATH}/.forgeflow"
test -L "${WT_PATH}/.forgeflow/tasks"

# 5. Install dependencies (node_modules is gitignored, not copied to worktree)
#    Detect package manager from main repo lockfile and install in worktree.
#    Use frozen-lockfile equivalent to skip resolution (worktree shares the same lockfile).
if   [ -f "${MAIN_ROOT}/pnpm-lock.yaml" ]; then pnpm install --frozen-lockfile --dir "$WT_PATH"
elif [ -f "${MAIN_ROOT}/yarn.lock" ];     then (cd "$WT_PATH" && yarn install --frozen-lockfile)
elif [ -f "${MAIN_ROOT}/package-lock.json" ]; then (cd "$WT_PATH" && npm ci)
elif [ -f "${MAIN_ROOT}/bun.lockb" ];     then (cd "$WT_PATH" && bun install)
elif [ -f "${MAIN_ROOT}/requirements.txt" ] || [ -f "${MAIN_ROOT}/pyproject.toml" ]; then
  # Python: copy or recreate venv if .venv is gitignored
  if [ ! -d "${WT_PATH}/.venv" ] && [ -d "${MAIN_ROOT}/.venv" ]; then
    cp -r "${MAIN_ROOT}/.venv" "${WT_PATH}/.venv"
  fi
fi
```

Record in `brief.md` Task Isolation section:
- `isolation: worktree`
- `worktree_path: ~/.forgeflow/projects/<project-slug>/worktrees/<task-id>/` (or the `FORGEFLOW_HOME` equivalent)
- `branch: <branch-name>`

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

Review is read-only and can run inside the worktree. The worktree-local `.forgeflow/` compatibility directory, when present, points to the global project storage root. No project-root `.forgeflow/` access is required.

## Cleanup (ship stage)

Run from the **main repository root** after the worktree branch is merged or discarded.

### Merge + cleanup

```bash
TASK_ID="<task-id>"
BRANCH="<branch-name>"  # From brief.md Task Isolation
MAIN_ROOT="$(git rev-parse --show-toplevel)"
STORAGE_ROOT="$(python3 /path/to/forgeflow/scripts/forgeflow_storage.py --project-dir "$MAIN_ROOT" --print storage-root)"
WT_PATH="${STORAGE_ROOT}/worktrees/${TASK_ID}"

# 0. Move to main repo (session may be inside worktree)
cd "$MAIN_ROOT"

# 1. Merge branch into main
git checkout main
git merge --no-ff "$BRANCH"

# 2. Remove .forgeflow directory (contains individual symlinks, not a symlink itself)
rm -rf "${WT_PATH}/.forgeflow"

# 3. Remove worktree
git worktree remove "$WT_PATH"

# 4. Delete branch
git branch -d "$BRANCH"
```

### Discard + cleanup

```bash
MAIN_ROOT="$(git rev-parse --show-toplevel)"

# 0. Move to main repo (session may be inside worktree)
cd "$MAIN_ROOT"

# 1. Remove .forgeflow directory (contains individual symlinks, not a symlink itself)
rm -rf "${WT_PATH}/.forgeflow"

# 2. Force-remove worktree (discards uncommitted changes)
git worktree remove --force "$WT_PATH"

# 3. Delete branch
git branch -D "$BRANCH"
```

### Keep branch (no cleanup)

If the user selects "keep branch as-is", do not remove the worktree or branch. The user may return to it later.

## Orphan worktree detection and cleanup

Standalone cleanup for worktrees whose task completed (review approved, ship ran or was skipped) but cleanup was never executed. This can happen when the session ends between review approval and ship completion, or when ship exits with `partial` outcome.

### Detection

List worktrees under `<storage-root>/worktrees/` and cross-reference with task state:

```bash
# List candidate worktrees
STORAGE_ROOT="$(python3 /path/to/forgeflow/scripts/forgeflow_storage.py --project-dir "$(git rev-parse --show-toplevel)" --print storage-root)"
ls -1d "${STORAGE_ROOT}"/worktrees/*/ 2>/dev/null
```

For each `<task-id>` directory found:

1. Read `<telemetry-dir>/<task-id>.md`: check if ship stage exists with outcome `success` or `partial`.
2. Read `<task-dir>/checkpoint.md`: check if `Current Stage` is `ship`.
3. Read `<task-dir>/review-report.md`: check if verdict is `approved`.

A worktree is **orphaned** when any of these is true:
- Telemetry shows ship as `partial` or `success` but the worktree directory still exists.
- Checkpoint shows `ship` stage AND review-report shows `approved`.
- No telemetry/checkpoint exists but review-report shows `approved` (session ended abruptly).

A worktree is **active** (not orphaned) when:
- Checkpoint shows a stage before `ship` (execute, review in progress).
- No review-report or review verdict is not `approved`.

### Cleanup procedure

For each orphaned worktree:

```bash
TASK_ID="<task-id>"
STORAGE_ROOT="$(python3 /path/to/forgeflow/scripts/forgeflow_storage.py --project-dir "$(git rev-parse --show-toplevel)" --print storage-root)"
WT_PATH="${STORAGE_ROOT}/worktrees/${TASK_ID}"
BRANCH=$(git -C "$WT_PATH" branch --show-current 2>/dev/null)
BASE_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||' || echo "main")

# 1. Check if branch is already merged
if git branch --merged "$BASE_BRANCH" | grep -q "$BRANCH"; then
  # Safe to clean up
  cd "$(git rev-parse --show-toplevel)"
  rm -rf "${WT_PATH}/.forgeflow"
  git worktree remove "$WT_PATH"
  git branch -d "$BRANCH"
  echo "Orphan cleaned: ${TASK_ID} (branch ${BRANCH} was already merged)"
else
  # Branch not merged — warn only
  echo "WARNING: ${TASK_ID} branch ${BRANCH} is NOT merged into ${BASE_BRANCH}."
  echo "Run /forgeflow:ship to complete branch disposition, or merge manually first."
fi
```

Do not auto-remove unmerged branches. Always warn and let the user decide.

### Integration with config prune

The `/forgeflow:ff-config` prune option (Mode D) uses this detection logic to list orphans and offer batch cleanup. See `skills/ff-config/SKILL.md`.

## Safety rules

1. **`.forgeflow/` in worktrees is only a compatibility directory with individual symlinks to global storage**, not a project-root storage directory and not a single symlink to an entire `.forgeflow/`. This prevents circular references through `worktrees/`. When cleaning up, `rm -rf` is safe because the directory only contains symlinks, not actual data.
2. **Never force-remove a dirty worktree without user confirmation.** If `git status --short` shows changes, ask first.
3. **Branch naming**: use `<task-id>` as the branch name directly (e.g., `fix-area-range-slider-6a3`). This follows the project's commit convention `[브랜치명] 변경 내용 요약` — the branch name becomes the commit prefix. ForgeFlow worktrees are identifiable via `git worktree list` or the `<storage-root>/worktrees/` directory.
4. **One worktree per task**: never share a worktree between tasks.
5. **Main branch protection**: when isolation is active, the execute stage must not edit files on the main branch. If the agent detects it is on main with `isolation: worktree` in brief, warn and stop.
6. **Idempotent creation**: if `<storage-root>/worktrees/<task-id>/` already exists and the branch is correct, skip creation. Do not error or recreate.
7. **Prune stale worktrees**: before creating a new worktree, `git worktree prune` to clean up any stale references.

## Known issues and workarounds

### Vite/Vitest ELOOP preflight for worktrees

worktree에서 Vite 또는 Vitest 프로젝트를 실행할 때, `.forgeflow` symlink가 watcher의 recursive scan을 유발하여 ELOOP(OOM exit 134)가 발생할 수 있다. individual symlink 방식(v1.10+)으로 대부분 해결되었지만, 일부 프레임워크(Nuxt, SvelteKit 등)는 설정 없이 watcher를 시작할 때 여전히 문제가 발생할 수 있다.

**사전 감지 절차** (execute 단계에서 worktree 진입 시):
1. `ls vite.config.* vitest.config.* 2>/dev/null` 실행
2. 설정 파일이 발견되면: dev server(`pnpm dev`, `npm run dev`) 사용 전에 경고 출력
3. Vitest 실행 시 `--exclude '**/.forgeflow/**'` 옵션 필수 추가
4. ESLint 설정에 `.forgeflow/` ignorePatterns 추가 확인

**경고 메시지**:
```
⚠️ Vite/Vitest 프로젝트에서 worktree symlink ELOOP가 발생할 수 있습니다.
pnpm dev 대신 pnpm build && pnpm preview --host 127.0.0.1 을 사용하세요.
```

**Evidence 기록**: 대체 명령 사용 시 implementation-notes에 `dev_server_fallback: build+preview (worktree symlink ELOOP avoidance)` 기록.

### Dev server ELOOP with `.forgeflow` symlink (resolved)

~~The `.forgeflow` symlink causes Vite/webpack dev server file watchers to recursively scan the entire shared `.forgeflow/` directory (including all worktree task artifacts, review reports, and evolution rules). In medium+ projects this can trigger Node OOM crashes (exit 134).~~

**Resolved**: The creation procedure now uses individual symlinks for each subdirectory (`tasks`, `telemetry`, `evolution`, `tmp-assets`) instead of linking the entire `.forgeflow/` directory. This prevents the circular reference through `worktrees/` that caused ELOOP errors. No project-level Vite/webpack config changes are needed.

If the old single-symlink approach was used (pre-v1.10), the workaround below still applies:

Vite (`vite.config.ts`):
```ts
server: {
  watch: {
    ignored: ['**/.forgeflow/**'],
  },
},
```

Webpack (`webpack.config.js`):
```js
watchOptions: {
  ignored: /node_modules|\.forgeflow/,
},
```

If modifying the project config is undesirable or the project uses a framework that wraps Vite, fall back to the workaround below.

**Fallback workaround**: Use production build + static preview instead:

```bash
pnpm build
pnpm preview --host 127.0.0.1
```

Record the fallback in `implementation-notes.md` Evidence as:
```
dev_server_fallback: build+preview (worktree symlink OOM avoidance)
```

### Lint and test duplication from symlink scan

Lint tools and test runners may discover files through the `.forgeflow` symlink, causing duplicate warnings or spurious test discovery.

**Workaround**: Exclude `.forgeflow/` from tool scanning:

| Tool | Exclusion |
|------|-----------|
| Vitest | `--exclude '**/.forgeflow/**'` |
| Jest | `--testPathIgnorePatterns .forgeflow` |
| ESLint | Add `.forgeflow/` to `ignorePatterns` in eslint config or `.eslintignore` |

The execute stage (`skills/execute/SKILL.md`) reinforces these exclusions when running verification inside a worktree.

### Unrelated dirty files and scope creep

When a worktree accumulates changes outside the plan scope (e.g., config files, unrelated components), ship correctly detects and blocks automatic branch disposition. To minimize this:

1. **Execute discipline**: If implementation requires editing a file not listed in `plan.md`, record it immediately in `implementation-notes.md` → Deviations from Plan.
2. **Scope boundary check**: After all plan steps complete, compare `git diff --name-only` against the plan's file scope. Flag any unplanned files before proceeding to review.
3. **If unplanned changes are substantial**: Consider whether to expand the plan scope (return to clarify) or revert the out-of-scope edits.

## Configuration

| Setting | Location | Default | Effect |
|---------|----------|---------|--------|
| `isolation` | `<storage-root>/defaults.md` | `true` | Enable worktree isolation for medium+/high/epic |
| `--no-isolation` | CLI flag | — | Disable worktree isolation for this run |

When `isolation: false` or `--no-isolation` is set, all stages run in the main repository working directory with no worktree. The user is responsible for avoiding concurrent edits.

## Gitignore

No project `.gitignore` entry is required for ForgeFlow worktrees because they live outside the repository under the resolved global storage root. If a legacy repo-local `.forgeflow/worktrees/` directory exists, treat it as stale local state and do not recreate it.

## Worktree Metrics Logging

각 워크트리 이벤트(생성, merge, cleanup) 시 `<task-dir>/worktree-metrics.jsonl`에 한 줄씩 JSON append.

### Event Schema

```json
{
  "event": "created|merged|discarded|kept|cleanup_failed",
  "timestamp": "ISO8601",
  "route": "small|medium|high|epic",
  "disposition": "merge|discard|keep",
  "success": true,
  "fallback_used": null,
  "error_category": null
}
```

### Error Categories
- `oom`: 메모리 부족
- `dependency_install_failed`: 의존성 설치 실패
- `merge_conflict`: merge 충돌
- `symlink_error`: symlink 문제
- `timeout`: 시간 초과

### Reporting
ship-summary.md의 Worktree Metrics 섹션에서 worktree-metrics.jsonl을 요약하여 기록.

### Telemetry Integration

Worktree lifecycle events should also be recorded as telemetry events in `<telemetry-dir>/<task-id>.md` using `templates/telemetry-event.md` format:

- `created` event → emit `stage_start` telemetry event with stage=execute and boundary_alert if fallback workaround is needed.
- `merged` or `discarded` event → emit `stage_complete` telemetry event with stage=ship, including duration_seconds from worktree creation to cleanup.
- `cleanup_failed` event → emit `stage_fail` telemetry event with failure_type from the error_category field.

This allows the periodic metrics-dashboard summary to include worktree stability metrics alongside stage duration and failure distribution.
