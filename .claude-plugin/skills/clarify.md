---
description: Analyze requirements from raw objective. Produces domain-aware PRD, architecture, QA drafts, and deploys project-specific agents/skills.
---

# /forgeflow:clarify

The heavy analysis stage. Takes the raw objective from init and produces everything needed for planning: domain analysis, project type detection, PRD/ARCH/QA drafts, and agent/skill deployment.

## Instructions

1. **Read brief.json** from `.forgeflow/tasks/<task-id>/` to get the raw objective and risk level.

2. **Gather project context**:

   ```bash
   # Project type detection
   cat package.json 2>/dev/null | head -40
   cat pyproject.toml 2>/dev/null | head -40
   cat Cargo.toml 2>/dev/null | head -20
   cat go.mod 2>/dev/null | head -10

   # Existing codebase structure
   find . -maxdepth 2 -type f \( -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.go" \) | head -30

   # Recent changes
   git log --oneline -5 2>/dev/null
   git diff --stat HEAD 2>/dev/null

   # Existing ForgeFlow tasks
   ls .forgeflow/tasks/ 2>/dev/null
   ```

3. **Analyze objective → extract**:
   - **Domains**: api, frontend, backend, data, auth, infra, testing, security
   - **Tech stack signals**: python, typescript, go, rust
   - **Change type**: feature, bugfix, refactor, migration, security, testing
   - **Work mode**: frontend | backend | devops | full (based on keywords)

4. **Detect project type** from filesystem markers:
   - `package.json` + `"next"` → Next.js
   - `package.json` + `"react"` → React
   - `pyproject.toml` + `"fastapi"` → FastAPI
   - `pyproject.toml` + `"flask"` → Flask
   - `manage.py` → Django
   - `go.mod` → Go service
   - `Cargo.toml` → Rust project
   - Generic `pyproject.toml` → Python CLI

5. **Determine route**:
   - risk=high, or change=migration/refactor/security → `large`
   - risk=medium, or objective has 2+ domains → `medium`
   - risk=low, single domain, change=bugfix/docs/cosmetic → `small`

6. **Write draft documents** under `docs/`:

   - `docs/PRD.md` — Product Requirements Document:
     - Objective (clarified, testable)
     - Domain analysis + domain-specific considerations
     - Project context (type, framework, language)
     - Constraints and non-goals

   - `docs/ARCHITECTURE.md` — Architecture draft:
     - Project context + architecture considerations
     - Affected components/files (best guess from codebase scan)
     - Proposed approach (not full plan — that's plan stage)

   - `docs/QA.md` — QA checklist:
     - Domain-specific QA checklist
     - Project-specific QA notes
     - Acceptance criteria outline

   - `docs/DECISIONS.md` — ADR template (empty, for plan/execute stages)

7. **Deploy agents and skills** to project root `.claude/`:

   Based on work mode:
   - frontend: `architect.md`, `frontend-dev.md`, `qa-engineer.md` + `component-patterns` skill
   - backend: `architect.md`, `backend-dev.md`, `qa-engineer.md` + `api-security-checklist` skill
   - devops: `architect.md`, `devops-engineer.md`, `qa-engineer.md`
   - full: all 5 agents + all 3 skills

   Write to `.claude/agents/` and `.claude/skills/` at **project root** (not task dir). Skip if file already exists.

8. **Write CLAUDE.md** in task dir — pointer to brief, PRD, architecture entry point + trigger rules.

9. **Update brief.json**:
   - Add: `domains`, `tech_stack`, `change_type`, `work_mode`, `project_type`, `route`
   - Set `status: "clarified"`

10. **Update run-state.json**: set `current_stage: "clarify"` (next advance goes to plan or run)

11. **Determine next stage**:
    - Route `small`: → `/forgeflow:run` (skip plan, go straight to execution)
    - Route `medium` or `large`: → `/forgeflow:plan`

12. **Report**:
    - Clarified objective (1 sentence)
    - Detected: domains, project type, work mode
    - Route and next stage
    - Files created
    - Any open questions / ambiguities that need user input

## What clarify creates

```
.forgeflow/tasks/<task-id>/
  brief.json              ← updated with analysis
  run-state.json          ← stage updated
  docs/
    PRD.md                ← domain-aware PRD
    ARCHITECTURE.md       ← architecture draft
    QA.md                 ← QA checklist
    DECISIONS.md          ← empty ADR template
  tasks/
    init-summary.md       ← what was analyzed
  CLAUDE.md               ← pointer + triggers

<project-root>/.claude/
  agents/                 ← domain-specific agents
  skills/                 ← domain-specific skills
```

**init은 발판, clarify는 분석.** clarify가 끝나면 요구사항이 명확하고 다음 단계로 갈 준비가 되어 있어야 한다.
