---
name: config
version: "1.3"
description: Manage ForgeFlow project defaults interactively. Toggle auto-chaining and worktree isolation.
validate_prompt: |
  Must present current .forgeflow/defaults.md values, offer toggle by number, and write changes back without committing.
dependencies:
  - skills/_shared/automation.md
---

# Skill: config

Interactive project defaults manager for ForgeFlow. Reads and toggles settings in `.forgeflow/defaults.md`.

## Input

| Artifact | Source |
|----------|--------|
| `.forgeflow/defaults.md` | Project root (may not exist) |

## Output Artifacts

| Artifact | Template | Description |
|----------|----------|-------------|
| `.forgeflow/defaults.md` | N/A | Updated project defaults |

## Procedure

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

## Exit Condition

- User selects 종료 (exit) from the menu.
- `.forgeflow/defaults.md` reflects all toggled values.

## Constraints

- Only modify `.forgeflow/defaults.md` — no other files.
- Never auto-commit the defaults file.
- Supported fields only: `auto`, `isolation`. Ignore unknown fields.
- Shared file-write rules: `_shared/discipline.md`.
