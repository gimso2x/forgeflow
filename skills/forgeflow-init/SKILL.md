---
name: forgeflow-init
description: Bootstrap a new ForgeFlow task workspace by calling the orchestrator init command without crossing into clarify/plan/run automatically. Use when the user types /forgeflow-init.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must expose scripts/run_orchestrator.py init with task-id, objective, risk, and optional task-dir.
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

If `--objective` is missing, ask the user for it in Korean. Do not ask for `--task-id` unless the user explicitly wants to set one; otherwise, let the system generate it automatically. All communication with the user must be in Korean.

## Action

Run the existing orchestrator bootstrap command from the ForgeFlow repository root:

```bash
python3 scripts/run_orchestrator.py init --task-id <task-id> --objective "<objective>" --risk low|medium|high|critical [--task-dir <path>]
```

This bootstraps a new task workspace without overwriting existing artifacts. The default task directory is `./.forgeflow/tasks/<task-id>` **in the user's active project/workspace**, not inside a Claude/Codex plugin installation cache.

Plugin-cache safety rule: never create task artifacts under a path containing `.claude/plugins/cache`, `.codex/plugins`, or any plugin marketplace/cache directory. If the slash command runtime resolves `.` to the plugin install/cache directory and the user did not provide `--task-dir`, stop and ask for an explicit `--task-dir` instead of writing there. If the user provides `--task-dir`, use that path exactly.

Expected starter artifacts include:

- `brief.json`
- `run-state.json`
- `checkpoint.json`
- `session-state.json`


## Starter blueprint

`init` remains a bootstrap boundary, but the starter artifacts should be useful enough for `/forgeflow:clarify` and `/forgeflow:plan` to continue without hidden chat context. When the objective contains enough context, seed the task workspace with draft hints for:

- initial team/role split (`planning`, `implementation`, `review`, `qa`)
- likely specialist skills or reviewers
- architecture/documentation targets such as `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/QA.md`, `docs/ADR.md`
- a task-local handoff note pointing to `docs/developer-handoff-template.md`

These are drafts, not approval to skip `clarify`. Keep every generated hint inside the task workspace unless the user explicitly asks to write project docs.

## Boundaries

`init` is workspace/bootstrap only. It is not requirement clarification, planning, implementation, review, shipping, or branch disposition.

Do not automatically continue into `/forgeflow:clarify`, `/forgeflow:plan`, or `/forgeflow:execute` after init succeeds. That would make the plugin feel like it secretly crossed a stage boundary. No thanks.

## Exit Condition

- Required starter artifacts exist in the task workspace.
- Existing artifacts were not overwritten.
- The response reports the task directory and created/kept artifacts.
- The final line is exactly a closed approval question for the next stage:

```text
다음 스텝으로 `/forgeflow:clarify`를 진행하시겠습니까? (y/n)
```
