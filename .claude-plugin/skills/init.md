---
description: Bootstrap a new ForgeFlow task. Creates directory structure and saves raw objective — analysis happens in clarify.
---

# /forgeflow:init

Create the task workspace. Only does scaffold + raw objective storage. No domain analysis, no drafts, no agents.

## Usage

```
/forgeflow:init
/forgeflow:init <objective>
/forgeflow:init <objective> --risk <low|medium|high>
/forgeflow:init <objective> --task-id <custom-id> --risk <high>
```

**모든 인자가 옵셔널이다.** 아무것도 안 주면 프로젝트 컨텍스트에서 자동 추론한다.

## Instructions

> **CRITICAL RULE: NEVER ask the user for missing arguments.**
> If objective, task-id, or risk is not provided, you MUST auto-infer them.
> Do NOT output a form, a question, or a prompt requesting input.
> Go directly to step 1a for auto-inference and proceed immediately.

1. **Parse arguments** — extract optional objective, task-id, and risk from the invocation.

   - `objective`: what to accomplish (optional — auto-inferred if missing, see step 1a)
   - `task-id`: short identifier (optional, auto-generated from objective slug)
   - `risk`: `low`, `medium`, `high` (optional, auto-estimated from objective keywords)
     - High signals: migration, refactor, security, auth, payment, database, breaking
     - Low signals: typo, rename, docs, lint, style, cosmetic
     - Default: medium

1a. **Auto-infer objective** (when not provided):

   Run these commands to gather project context:
   ```bash
   git log --oneline -5 2>/dev/null
   git diff --stat HEAD 2>/dev/null
   cat README.md 2>/dev/null | head -30
   cat AGENTS.md 2>/dev/null | head -30
   ls -la .forgeflow/tasks/ 2>/dev/null
   ```

   From the gathered context, infer a concise objective:
   - If there are uncommitted changes → describe what they seem to be doing
   - If recent commits show a pattern → continue that theme
   - If README describes the project → summarize the next logical step
   - If existing tasks exist → differentiate or extend them
   - Fallback: "Improve project based on current state"

   Keep the inferred objective to one clear sentence.

1b. **Auto-generate task-id** (when not provided):

   Slugify the objective: lowercase, spaces → hyphens, strip special chars, max 40 chars.
   Example: "Add login page with OAuth" → `add-login-page-with-oauth`

2. **Create scaffold**:

   ```bash
   mkdir -p .forgeflow/tasks/<task-id>/{docs,tasks/feature,tasks/qa}
   ```

3. **Write minimal artifacts**:

   Write `brief.json`:
   ```json
   {
     "schema_version": "0.1",
     "task_id": "<task-id>",
     "objective": "<raw objective string>",
     "risk_level": "<low|medium|high>",
     "status": "initialized",
     "route": null
   }
   ```

   Write `run-state.json`:
   ```json
   {
     "schema_version": "0.1",
     "current_stage": "clarify",
     "task_id": "<task-id>"
   }
   ```

   Write empty `checkpoint.json` and `session-state.json` with `schema_version: "0.1"` and `task_id`.

4. **Report results**:
   - task-id
   - objective (raw)
   - risk level
   - next stage: **clarify** (`/forgeflow:clarify`)

## What init creates

```
.forgeflow/tasks/<task-id>/
  brief.json          ← raw objective, no analysis
  run-state.json      ← stage = clarify
  checkpoint.json     ← empty
  session-state.json  ← empty
  docs/               ← empty (clarify fills these)
  tasks/
    feature/          ← empty
    qa/               ← empty
```

**init은 발판만 깐다.** 요구사항 분석, 도메인 감지, PRD/ARCH/QA 초안, 에이전트/스킬 배치는 전부 `/forgeflow:clarify`에서.
