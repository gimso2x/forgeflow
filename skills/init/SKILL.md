---
name: init
description: Bootstrap a new ForgeFlow task workspace by calling the orchestrator init command without crossing into clarify/plan/run automatically.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must expose scripts/run_orchestrator.py init with task-id, objective, risk, and optional task-dir.
  Must not overwrite existing task artifacts.
  Must stop at the stage boundary with a closed approval question before clarify.
---

# Init

Use this skill when the user asks for `/forgeflow:init`, `forgeflow init`, or wants to bootstrap a new task workspace before clarification or planning.

## Input

- `--task-id`: stable task identifier, such as `add-init-plugin-command`
- `--objective`: one-sentence task objective
- `--risk low|medium|high`: initial risk estimate
- Optional `--task-dir`: explicit task workspace directory

If any required input is missing, ask only for the missing fields. Do not invent a task id or objective when the user has not provided enough signal.

## Action

Run the existing orchestrator bootstrap command from the ForgeFlow repository root:

```bash
python3 scripts/run_orchestrator.py init --task-id <task-id> --objective "<objective>" --risk low|medium|high [--task-dir <path>]
```

This bootstraps a new task workspace without overwriting existing artifacts. The default task directory is `./.forgeflow/tasks/<task-id>`.

Expected starter artifacts include:

- `brief.json`
- `run-state.json`
- `checkpoint.json`
- `session-state.json`

## Boundaries

`init` is workspace/bootstrap only. It is not requirement clarification, planning, implementation, review, shipping, or branch disposition.

Do not automatically continue into `/forgeflow:clarify`, `/forgeflow:plan`, or `/forgeflow:run` after init succeeds. That would make the plugin feel like it secretly crossed a stage boundary. No thanks.

## Exit Condition

- Required starter artifacts exist in the task workspace.
- Existing artifacts were not overwritten.
- The response reports the task directory and created/kept artifacts.
- The final line is exactly a closed approval question for the next stage:

```text
다음 스텝으로 `/forgeflow:clarify`를 진행하시겠습니까? (y/n)
```
