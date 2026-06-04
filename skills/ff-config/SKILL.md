---
name: ff-config
version: 0.6.0
description: Manage ForgeFlow project defaults interactively. Toggle auto-chaining and worktree isolation. Offers init from the config menu with reusable project context generation. Includes prune for orphan worktree cleanup. Use when the user says forgeflow 설정, 워크트리 정리, or 고아 브랜치 cleanup. Not for editing non-ForgeFlow config files like nginx, docker, or env.
validate_prompt: |
  Must present current resolved `defaults.md` values, offer toggle/init/prune actions by number, and write changes back without committing.
  When the user selects full project context init from the config menu, must detect repo type, documentation pointers, architecture/WBS signals, and generate project-draft.md as reusable project context.
  When the user selects prune, must detect orphan worktrees and offer cleanup.
dependencies:
  - skills/_shared/automation.md
  - skills/_shared/isolation.md
---

# Skill: config

Interactive project defaults manager for ForgeFlow. Reads and toggles settings in the resolved ForgeFlow storage root (`~/.forgeflow/projects/<project-slug>/defaults.md` by default; `<repo>/.forgeflow/defaults.md` only for local storage).
The default `/forgeflow:ff-config` flow must offer init as a numbered menu action, including reusable project context generation with auto-detected project structure, documentation pointers, and stable task guidance. Do not require the user to remember a separate manual init command.
Includes prune mode to detect and clean up orphan worktrees (see Mode D).

## Input

| Artifact | Source |
|----------|--------|
| `<storage-root>/defaults.md` | Resolved ForgeFlow storage root (may not exist) |
| Project manifest files | `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod` (read-only detection) |
| Project guidance/docs | `README.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `docs/`, roadmap/WBS/spec/architecture files |

## Output Artifacts

| Artifact | Template | Description |
|----------|----------|-------------|
| `<storage-root>/defaults.md` | N/A | Updated project defaults |
| `<storage-root>/project-draft.md` | `templates/project-draft.md` | Reusable project context and architecture draft (full mode only) |

## Procedure

### Mode A: Interactive config (default)

1. Read `<storage-root>/defaults.md` if it exists. Parse supported fields: `auto`, `isolation`, `storage.mode`, `storage.root`. When the file is missing, use hardcoded defaults: `auto: false`, `isolation: true`, `storage.mode: global`, `storage.root: ~/.forgeflow`.
2. Count orphan worktrees: list directories under `<storage-root>/worktrees/` and apply detection logic from `_shared/isolation.md` → Orphan worktree detection.
3. Present current settings as a numbered menu:

```
ForgeFlow 설정

1. auto (자동 체이닝)       — 현재: 꺼짐   (기본값: 꺼짐)
2. isolation (worktree 격리) — 현재: 켜짐   (기본값: 켜짐)
3. init (기본 scaffolding) — <storage-root>/defaults.md 생성
4. full init (프로젝트 컨텍스트 draft) — <storage-root>/project-draft.md 생성/갱신
5. prune (고아 워크트리 정리) — 현재: N개
6. 종료

번호를 선택하세요:
```

Where `N` is the count of orphaned worktrees from step 2. If `<storage-root>/worktrees/` does not exist, show `0개`.

4. On selection 1 or 2, toggle the value (off→on, on→off). Use Korean labels: 켜짐/꺼짐.
5. On selection 3, run **Mode C: Basic init**.
6. On selection 4, run **Mode B: Full project context init**.
7. On selection 5, run **Mode D: Prune orphan worktrees**.
8. Create or update `<storage-root>/defaults.md` with the new value. File format:

```markdown
# ForgeFlow Defaults

auto: true
isolation: true
storage.mode: global
storage.root: ~/.forgeflow
```

9. Confirm the change or generated artifact to the user. Loop back to step 2 until user selects 종료.
10. Do **not** commit generated storage files unless the user explicitly opts into local/team-shared storage to git — let the user decide.

### Mode B: Full project context init

When the user selects **full init (프로젝트 컨텍스트 draft)** from the `/forgeflow:ff-config` menu, generate `<storage-root>/project-draft.md` as a reusable project context and architecture draft alongside standard scaffolding.

1. **Standard init first**: Create the resolved storage root directory structure and `defaults.md` if they do not exist (same as basic init).
2. **Detect project context** by reading project manifest files (prompt-based, agent reads and judges):

| File detected | repo_type | Recommended adapter | Specialist presets |
|---------------|-----------|---------------------|-------------------|
| `package.json` | node | claude or cursor | ux (frontend), security (auth) |
| `pyproject.toml` or `setup.py` or `requirements.txt` | python | codex or claude | security (data), perf (ML) |
| `Cargo.toml` | rust | claude | perf, security |
| `go.mod` | go | codex or claude | perf, security |
| None of the above | other | claude | (none) |

3. **Detect structure**: Check for monorepo indicators (`packages/`, `apps/`, `workspaces` in `package.json`, `members` in `Cargo.toml`), library indicators (`lib/`, `src/lib`), CLI indicators (`bin/`, `cli/`), or default to `single-package`.
4. **Detect test framework**: Based on repo_type, check for test configuration files:
   - Node: `jest.config.*`, `vitest.config.*`, `mocha` in dependencies
   - Python: `pytest.ini`, `pyproject.toml` with pytest, `unittest`
   - Rust: built-in `cargo test`
   - Go: built-in `go test`
5. **Detect team structure**: Look for `CONTRIBUTING.md`, `CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md` to infer roles and review policy.
6. **Detect reusable project context pointers**: Look for stable project guidance and planning sources, including `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/`, `spec*`, `prd*`, `architecture*`, `roadmap*`, `wbs*`, `milestone*`, and ADR/implementation-notes files. Prefer repo-relative paths and short decision labels over long copied prose.
7. **Generate `<storage-root>/project-draft.md`** using `templates/project-draft.md` as the template, filling in all detected values. Set `generated` to the current ISO date. Set `schema` to `project-draft/v1`.
8. **Redact sensitive values**: Never copy token, API key, credential, private key, or secret values into `<storage-root>/project-draft.md`. It is acceptable to point to the policy or env var name without the value.
9. **Present the draft** to the user and ask them to review, correct stale assumptions, and add missing planning/architecture/WBS pointers before proceeding.
10. Do **not** commit the draft — let the user decide.

### Mode C: Basic init (default for init without --mode)

1. Create the resolved storage root if it does not exist.
2. Create `<storage-root>/defaults.md` with hardcoded defaults if it does not exist.
3. **Copy templates** to `<storage-root>/templates/` if the directory does not exist or is empty:
   - Resolve the plugin `templates/` directory using the template resolution logic from the main `forgeflow` skill (check `<workspace>/templates/`, then `~/.claude/plugins/cache/forgeflow/**/templates/`, then `~/.cursor/plugins/**/forgeflow/templates/`).
   - Copy all `*.md` files from the resolved plugin `templates/` directory to `<storage-root>/templates/`.
   - This ensures all ForgeFlow skills can resolve templates locally without depending on plugin cache paths.
4. Report completion. No draft generation.

### Mode D: Prune orphan worktrees

Detect and clean up worktrees that were left behind after review approval or partial ship. Uses detection logic from `_shared/isolation.md` → Orphan worktree detection.

1. **Scan**: List directories under `<storage-root>/worktrees/`. If none exist, report "정리할 워크트리가 없습니다." and return to menu.
2. **Classify**: For each `<task-id>` directory, apply orphan detection rules:
   - Read `<telemetry-dir>/<task-id>.md` for ship stage outcome.
   - Read `<task-dir>/checkpoint.md` for current stage.
   - Read `<task-dir>/review-report.md` for verdict.
   - Classify as `orphaned` (ship partial/success + worktree exists), `active` (pre-ship stage), or `unknown` (no artifacts found).
3. **Present**: Show classification result:
   ```
   워크트리 정리 대상:

   [고아] feature-map-ui-shell-b4c — ship 완료, 정리 안됨 (브랜치: 이미 병합됨)
   [활성] feature-auth-redir-a3f  — 아직 작업 중
   [미확인] feature-old-task-x1z  — 작업 산출물 없음

   정리할 항목의 번호를 선택하세요 (전체: a, 취소: q):
   ```
4. **Cleanup**: For each selected orphaned worktree:
   - Check if branch is already merged: `git branch --merged <base-branch>`.
   - If merged: remove symlink → `git worktree remove` → `git branch -d`.
   - If not merged: warn and skip. Suggest running `/forgeflow:ship` for full branch disposition.
5. **Report**: Show cleanup results. Return to menu.

## Auto-Detection Logic (Prompt-Based)

The detection is entirely prompt-driven. The agent reads files and makes judgments — no runtime code is involved.

### Detection sequence

1. Check for `package.json` in the project root → Node.js ecosystem.
2. Check for `pyproject.toml`, `setup.py`, or `requirements.txt` → Python ecosystem.
3. Check for `Cargo.toml` → Rust ecosystem.
4. Check for `go.mod` → Go ecosystem.
5. If none matched → `other` (manual configuration required).

### Adapter recommendation logic

Based on the detected repo type, recommend an adapter preset:

- **node**: `claude` for full-stack or frontend-heavy projects; `cursor` if the team prefers IDE-integrated workflow.
- **python**: `codex` for data/ML projects; `claude` for general Python.
- **rust**: `claude` (strongest reasoning for ownership/borrowing analysis).
- **go**: `codex` for infrastructure tooling; `claude` for complex service design.
- **other**: `claude` as the default general-purpose adapter.

### Specialist preset recommendations

Based on detected patterns in the project:

- **security**: Projects with authentication, encryption, API endpoints, or user data handling.
- **ux**: Frontend-heavy projects with UI components, design systems, or accessibility requirements.
- **perf**: Projects with ML pipelines, high-throughput APIs, real-time processing, or large datasets.

## Exit Condition

- **Mode A**: User selects 종료 (exit) from the menu. `<storage-root>/defaults.md` reflects all toggled values.
- **Mode B**: `<storage-root>/project-draft.md` is generated as reusable project context and presented to the user.
- **Mode C**: `<storage-root>/defaults.md` exists with default values.
- **Mode D**: Orphan worktrees are listed, user-selected cleanups executed, and results reported.

## Constraints

- Only modify `<storage-root>/defaults.md` and `<storage-root>/project-draft.md` — no other files (except worktree cleanup in Mode D which removes worktree directories and branches).
- Never auto-commit any generated files.
- Never remove unmerged branches in prune mode — warn only.
- Supported config fields only: `auto`, `isolation`, `storage.mode`, `storage.root`. Ignore unknown fields.
- Shared file-write rules: `_shared/discipline.md`.
- Detection logic is prompt-based. Do not invent or assume project properties — read actual files.
