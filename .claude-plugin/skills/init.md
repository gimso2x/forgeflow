---
description: Initialize a new ForgeFlow task with task-id, objective, and risk level.
---

# /forgeflow:init

Initialize a ForgeFlow task. Creates the full task workspace: brief, run-state, agents, skills, and domain-aware draft documents.

## Instructions

1. **Resolve arguments** — you MUST have all three before proceeding. If the user invoked `/forgeflow:init` with arguments (e.g. `/forgeflow:init feat-auth "add login page" medium`), use those directly. Only if any argument is missing, ask for just the missing ones — do NOT re-ask for arguments already provided.

   Required:
   - `task-id`: short identifier (e.g. `feat-auth`, `fix-login`)
   - `objective`: one-sentence description of what to accomplish
   - `risk`: `low`, `medium`, or `high` (default: `medium`)

2. **Call the runtime** — invoke the Python API to create the full workspace:

   ```bash
   cd <project-root> && PYTHONPATH=/path/to/forgeflow-repo python3 -c "
   from forgeflow_runtime.orchestrator import init_task
   from forgeflow_runtime.policy_loader import load_runtime_policy
   from pathlib import Path
   import json
   forgeflow_root = '<forgeflow-repo-path>'
   policy = load_runtime_policy(Path(forgeflow_root))
   result = init_task(
       Path('.forgeflow/tasks/<task-id>'),
       policy,
       task_id='<task-id>',
       objective='<objective>',
       risk_level='<risk>',
   )
   for f in sorted(result['created']):
       print(f'  created: {f}')
   "
   ```

   Replace `<forgeflow-repo-path>` with the local ForgeFlow repository path (e.g. `/home/ubuntu/work/forgeflow`). If running inside a session where `forgeflow_runtime` is already importable (same venv / PYTHONPATH), omit the PYTHONPATH prefix.

3. **Report results** — after init completes, show:
   - task-id and route (small/medium/large_high_risk)
   - selected team architecture pattern
   - detected domains and project type (if any)
   - list of generated files
   - next stage (clarify or plan depending on route)

## What init creates

The runtime `init_task()` generates a complete workspace under `.forgeflow/tasks/<task-id>/`:

- `brief.json` — task metadata with schema validation
- `run-state.json` — stage progression state
- `checkpoint.json` — gate checkpoint
- `session-state.json` — session tracking
- `CLAUDE.md` — pointer to key artifacts + trigger rules
- `docs/PRD.md` — domain-aware PRD draft (includes domain analysis, considerations)
- `docs/ARCHITECTURE.md` — architecture draft with domain context
- `docs/QA.md` — QA draft with domain-specific checklists
- `docs/DECISIONS.md` — ADR log
- `tasks/init-summary.md` — generated drafts summary
- `tasks/feature/<slug>.md` — feature breakdown draft
- `tasks/qa/<slug>.md` — QA reproduction/fix/regression draft
- `.claude/agents/` — 4 role-specific agent definitions (planner, implementer, qa, reviewer)
- `.claude/skills/` — 4 stage-specific skill definitions (plan, build, qa-fix, review)

## Notes

- Init will refuse to overwrite existing task directories (RuntimeViolation).
- The runtime auto-detects project type and domain from objective keywords.
- Do NOT manually create brief.json — the runtime handles validation and schema.
