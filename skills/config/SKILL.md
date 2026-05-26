---
name: config
version: "1.4"
description: Manage ForgeFlow project defaults interactively. Toggle auto-chaining and worktree isolation. Supports init with reusable project context generation.
validate_prompt: |
  Must present current .forgeflow/defaults.md values, offer toggle by number, and write changes back without committing.
  When invoked with init --mode=full, must detect repo type, documentation pointers, architecture/WBS signals, and generate project-draft.md as reusable project context.
dependencies:
  - skills/_shared/automation.md
---

# Skill: config

Interactive project defaults manager for ForgeFlow. Reads and toggles settings in `.forgeflow/defaults.md`.
Supports `init --mode=full` for reusable project context generation with auto-detected project structure, documentation pointers, and stable task guidance.

## Input

| Artifact | Source |
|----------|--------|
| `.forgeflow/defaults.md` | Project root (may not exist) |
| Project manifest files | `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod` (read-only detection) |
| Project guidance/docs | `README.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `docs/`, roadmap/WBS/spec/architecture files |

## Output Artifacts

| Artifact | Template | Description |
|----------|----------|-------------|
| `.forgeflow/defaults.md` | N/A | Updated project defaults |
| `.forgeflow/project-draft.md` | `templates/project-draft.md` | Reusable project context and architecture draft (full mode only) |

## Procedure

### Mode A: Interactive config (default)

1. Read `.forgeflow/defaults.md` if it exists. Parse supported fields: `auto`, `isolation`. When the file is missing, use hardcoded defaults: `auto: false`, `isolation: true`.
2. Present current settings as a numbered menu:

```
ForgeFlow 설정

1. auto (자동 체이닝)       — 현재: 꺼짐   (기본값: 꺼짐)
2. isolation (worktree 격리) — 현재: 켜짐   (기본값: 켜짐)
3. 종료

번호를 선택하세요:
```

3. On selection, toggle the value (off→on, on→off). Use Korean labels: 켜짐/꺼짐.
4. Create or update `.forgeflow/defaults.md` with the new value. File format:

```markdown
# ForgeFlow Defaults

auto: true
isolation: true
```

5. Confirm the change to the user. Loop back to step 2 until user selects 종료.
6. Do **not** commit `.forgeflow/defaults.md` to git — let the user decide.

### Mode B: init --mode=full (reusable project context generation)

When the user invokes `init --mode=full`, generate `.forgeflow/project-draft.md` as a reusable project context and architecture draft alongside standard scaffolding.

1. **Standard init first**: Create `.forgeflow/` directory structure and `defaults.md` if they do not exist (same as basic init).
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
6. **Detect reusable project context pointers**: Look for stable project guidance and planning sources, including `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/`, `spec*`, `prd*`, `architecture*`, `roadmap*`, `wbs*`, `milestone*`, and ADR/decision-log files. Prefer repo-relative paths and short decision labels over long copied prose.
7. **Generate `.forgeflow/project-draft.md`** using `templates/project-draft.md` as the template, filling in all detected values. Set `generated` to the current ISO date. Set `schema` to `project-draft/v1`.
8. **Redact sensitive values**: Never copy token, API key, credential, private key, or secret values into `.forgeflow/project-draft.md`. It is acceptable to point to the policy or env var name without the value.
9. **Present the draft** to the user and ask them to review, correct stale assumptions, and add missing planning/architecture/WBS pointers before proceeding.
10. Do **not** commit the draft — let the user decide.

### Mode C: Basic init (default for init without --mode)

1. Create `.forgeflow/` directory if it does not exist.
2. Create `.forgeflow/defaults.md` with hardcoded defaults if it does not exist.
3. Report completion. No draft generation.

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

- **Mode A**: User selects 종료 (exit) from the menu. `.forgeflow/defaults.md` reflects all toggled values.
- **Mode B**: `.forgeflow/project-draft.md` is generated as reusable project context and presented to the user.
- **Mode C**: `.forgeflow/defaults.md` exists with default values.

## Constraints

- Only modify `.forgeflow/defaults.md` and `.forgeflow/project-draft.md` — no other files.
- Never auto-commit any generated files.
- Supported config fields only: `auto`, `isolation`. Ignore unknown fields.
- Shared file-write rules: `_shared/discipline.md`.
- Detection logic is prompt-based. Do not invent or assume project properties — read actual files.
