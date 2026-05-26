---
name: config
description: Manage ForgeFlow project defaults interactively. Toggle auto-chaining, worktree isolation, and other settings.
validate_prompt: |
  Must present current .forgeflow/defaults.md values, offer toggle by number, and write changes back without committing.
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

1. Read `.forgeflow/defaults.md` if it exists. Parse supported fields: `auto`, `isolation`, `subagent_per_task`. Missing file means all defaults are `false`.
2. Present current settings as a numbered menu:

```
ForgeFlow 설정

1. auto (자동 체이닝)       — 현재: 꺼짐
2. isolation (worktree 격리) — 현재: 켜짐
3. subagent_per_task         — 현재: 꺼짐
4. 종료

번호를 선택하세요:
```

3. On selection, toggle the value (off→on, on→off). Use Korean labels: 켜짐/꺼짐.
4. Create or update `.forgeflow/defaults.md` with the new value. File format:

```markdown
# ForgeFlow Defaults

auto: true
isolation: false
subagent_per_task: false
```

5. Confirm the change to the user. Loop back to step 2 until user selects 종료.
6. Do **not** commit `.forgeflow/defaults.md` to git — let the user decide.

## Exit Condition

- User selects 종료 (exit) from the menu.
- `.forgeflow/defaults.md` reflects all toggled values.

## Constraints

- Only modify `.forgeflow/defaults.md` — no other files.
- Never auto-commit the defaults file.
- Supported fields only: `auto`, `isolation`, `subagent_per_task`. Ignore unknown fields.
