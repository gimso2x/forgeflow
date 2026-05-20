---
name: forgeflow-init
description: Bootstrap a new ForgeFlow task workspace with a minimal brief.md stub. Does not cross into clarify/plan/execute automatically. Use when the user types /forgeflow-init.
version: 0.2.0
author: gimso2x
validate_prompt: |
  Must create .forgeflow/tasks/<task-id>/ directory and write a minimal brief.md stub.
  Must not overwrite existing task artifacts.
  Must stop at the stage boundary with a closed approval question before clarify.
---

# Init

Use this skill when the user asks for `/forgeflow-init`, `forgeflow init`, or wants to bootstrap a new task workspace before clarification or planning.

## Input

- `--task-id`: stable task identifier (optional; auto-generated if omitted)
- `--objective`: one-sentence task objective
- `--risk low|medium|high|critical`: initial risk estimate (optional; defaults to medium). These map to route labels `small|medium|high|epic`.
- Optional `--task-dir`: explicit task workspace directory

If `--objective` is missing, ask the user for it. Do not ask for `--task-id` unless the user explicitly wants to set one; otherwise, generate it automatically. All communication with the user must be in Korean.

## Task ID generation

When `--task-id` is not provided, generate one using this pattern:

```
<type>-<short-slug>-<3-char-hash>
```

- `type`: feature, fix, refactor, docs, or task
- `short-slug`: 2-4 word kebab-case slug derived from the objective
- `3-char-hash`: first 3 characters of a timestamp-based hex string

Example: `feature-auth-redir-a3f`

Check that `.forgeflow/tasks/<task-id>/` does not already exist. If it does, append a numeric suffix.

## Output Artifacts

| Artifact | Template | Description |
|----------|----------|-------------|
| `brief.md` | `templates/brief.md` | Minimal stub with Objective and Risk Level filled; other sections left as placeholders |

## Procedure

1. Create the task directory:

```bash
mkdir -p .forgeflow/tasks/<task-id>
```

This must be **in the user's active project/workspace**, not inside a plugin installation cache.

Plugin-cache/extension-cache safety rule: never create task artifacts under a path containing `.claude/plugins/cache`, `.codex/plugins`, `.cursor/plugins`, `~/.cursor/plugins/local`, `.gemini/extensions`, `~/.gemini/extensions`, or any plugin marketplace/cache/extension directory. If the working directory resolves to a plugin install/cache/extension directory and the user did not provide `--task-dir`, stop and ask for an explicit `--task-dir` instead of writing there. If the user provides `--task-dir`, use that path exactly.

2. Write a minimal `brief.md` stub using `templates/brief.md` as the format. Fill in `Objective` and `Risk Level` from the input arguments. Leave all other sections as placeholders for `/forgeflow:clarify` to fill.

3. Do not overwrite if `brief.md` already exists. Report that it was kept as-is.

## Constraints

- `init` is workspace/bootstrap only — not clarification, planning, implementation, review, shipping, or branch disposition.
- Do not automatically continue into `/forgeflow:clarify`, `/forgeflow:plan`, or `/forgeflow:execute` after init succeeds.

## Exit Condition

- `.forgeflow/tasks/<task-id>/` directory exists
- `brief.md` stub exists in the task directory
- Existing artifacts were not overwritten
- The response reports the task directory and created/kept artifacts
- The final line is exactly a closed approval question for the next stage:

```text
다음 스텝으로 `/forgeflow:clarify`를 진행하시겠습니까? (y/n)
```
