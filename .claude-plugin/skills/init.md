---
description: Initialize a new ForgeFlow task. All arguments optional — auto-infers objective, task-id, and risk from project context.
---

# /forgeflow:init

Initialize a ForgeFlow task. Creates the full workspace: brief, run-state, agents, skills, and domain-aware draft documents.

## Usage

```
/forgeflow:init
/forgeflow:init <objective>
/forgeflow:init <objective> --risk <low|medium|high>
/forgeflow:init <objective> --task-id <custom-id> --risk <high>
```

**모든 인자가 옵셔널이다.** 아무것도 안 주면 프로젝트 컨텍스트에서 자동 추론한다.

## Instructions

1. **Parse arguments** — extract optional objective, task-id, and risk from the invocation.

   - `objective`: what to accomplish (optional — auto-inferred if missing, see step 1a)
   - `task-id`: short identifier (optional, auto-generated from objective)
   - `risk`: `low`, `medium`, `high` (optional, auto-estimated from objective keywords)
     - High signals: migration, refactor, security, auth, payment, database, breaking
     - Low signals: typo, rename, docs, lint, style, cosmetic
     - Default: medium

   **If any argument is missing, do NOT ask the user.** Proceed with auto-inference.

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

2. **Call the runtime**:

   ```bash
   cd <project-root> && PYTHONPATH=/path/to/forgeflow-repo python3 -c "
   from forgeflow_runtime.orchestrator import init_task
   from forgeflow_runtime.policy_loader import load_runtime_policy
   from pathlib import Path
   import json
   forgeflow_root = '<forgeflow-repo-path>'
   policy = load_runtime_policy(Path(forgeflow_root))
   kwargs = dict(
       task_dir=Path('.forgeflow/tasks/<task-id or auto>'),
       policy=policy,
       objective='<objective>',
   )
   if '<task-id>' != 'auto':
       kwargs['task_id'] = '<task-id>'
   if '<risk>' != 'auto':
       kwargs['risk_level'] = '<risk>'
   result = init_task(**kwargs)
   for f in sorted(result['created']):
       print(f'  created: {f}')
   print(f'task-id: {result[\"task_id\"]}')
   print(f'route: {result[\"route\"]}  risk: {result[\"risk_level\"]}')
   print(f'architecture: {result[\"selected_architecture\"]}')
   "
   ```

   Replace `<forgeflow-repo-path>` with the local ForgeFlow repository path. If `forgeflow_runtime` is already importable, omit PYTHONPATH.

3. **Report results** — after init completes, show:
   - task-id (auto-inferred or explicit)
   - route and risk level
   - selected team architecture pattern
   - detected domains and project type (if any)
   - next stage

## What init creates

20 files under `.forgeflow/tasks/<task-id>/`:

- `brief.json` — task metadata
- `run-state.json`, `checkpoint.json`, `session-state.json` — state tracking
- `CLAUDE.md` — pointer to key artifacts + trigger rules
- `docs/PRD.md` — domain-aware PRD draft
- `docs/ARCHITECTURE.md` — architecture draft with domain context
- `docs/QA.md` — QA draft with domain-specific checklists
- `docs/DECISIONS.md` — ADR log
- `tasks/init-summary.md`, `tasks/feature/`, `tasks/qa/`
- `.claude/agents/` — 4 role-specific agent definitions
- `.claude/skills/` — 4 stage-specific skill definitions
