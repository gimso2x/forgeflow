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

   # Environment preflight
   git rev-parse --is-inside-work-tree 2>/dev/null && echo "GIT: yes" || echo "GIT: no"
   ls pnpm-lock.yaml package-lock.json yarn.lock bun.lockb 2>/dev/null | head -3
   test -d node_modules && echo "NODE_MODULES: yes" || echo "NODE_MODULES: no"
   test -d .venv && echo "VENV: yes" || echo "VENV: no"
   test -d vendor && echo "VENDOR: yes" || echo "VENDOR: no"
   ```

3. **Environment preflight check** — act on the results from step 2:
   - `git rev-parse --show-toplevel` → confirm the git root matches the target project directory. If a parent directory is the repo root, add `"environment_warnings": ["git_root_mismatch"]` and record `"git_root_detected"` vs `"git_root_expected"`. This prevents executing commits in the wrong repository scope.
   - If `GIT: no`: add `"environment_warnings": ["not_a_git_repo"]` to brief.json.
   - If lockfile exists but no dependency directory (e.g., `pnpm-lock.yaml` present but no `node_modules`): add to `open_questions.blocker_questions`: "종속성이 설치되지 않았습니다. execute 전에 `<install command>`을 실행하시겠습니까?"
   - If neither lockfile nor dependency directory exists: new project, skip silently.
   - Record findings in brief.json under `"environment_preflight": { "git": bool, "git_root": "<path>", "dependencies_installed": bool, "warnings": [] }`.

4. **Analyze objective → extract**:
   - **Domains**: api, frontend, backend, data, auth, infra, testing, security
   - **Tech stack signals**: python, typescript, go, rust
   - **Change type**: feature, bugfix, refactor, migration, security, testing
   - **Work mode**: frontend | backend | devops | full (based on keywords)

5. **Detect project type** from filesystem markers:
   - `package.json` + `"next"` → Next.js (record `appRouter: true` if `app/` dir exists)
   - `package.json` + `"react"` + `"vite"` → React + Vite
   - `package.json` + `"react"` (no `vite`) → React (CRA or custom)
   - `package.json` + `"vue"` → Vue
   - `package.json` + `"svelte"` → Svelte
   - `package.json` + `"nuxt"` → Nuxt
   - `pyproject.toml` + `"fastapi"` → FastAPI
   - `pyproject.toml` + `"flask"` → Flask
   - `manage.py` → Django
   - `go.mod` → Go service
   - `Cargo.toml` → Rust project
   - Generic `pyproject.toml` → Python CLI
   - No framework signals but deliverables/docs only → `documentation-only` (skip build/lint/test gates)
   - **Conflict detection**: If the detected tech stack contradicts the user's request or CLAUDE.md defaults, add to `open_questions.blocker_questions` with the detected vs stated conflict. Do not silently proceed with a wrong stack assumption.

6. **Determine route**:
   - risk=high, or change=migration/refactor/security → `high`
   - risk=medium, or objective has 2+ domains → `medium`
   - risk=low, single domain, change=bugfix/docs/cosmetic → `small`

7. **Write draft documents** under `docs/`:

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

8. **Deploy agents and skills** to project root `.claude/`:

   Based on work mode:
   - frontend: `architect.md`, `frontend-dev.md`, `qa-engineer.md` + `component-patterns` skill
   - backend: `architect.md`, `backend-dev.md`, `qa-engineer.md` + `api-security-checklist` skill
   - devops: `architect.md`, `devops-engineer.md`, `qa-engineer.md`
   - full: all 5 agents + all 3 skills

   Write to `.claude/agents/` and `.claude/skills/` at **project root** (not task dir). Skip if file already exists.

9. **Write CLAUDE.md** in task dir — pointer to brief, PRD, architecture entry point + trigger rules.

10. **Update brief.json**:
   - Add: `domains`, `tech_stack`, `change_type`, `work_mode`, `project_type`, `route`
   - Set `status: "clarified"`

11. **Update run-state.json**: set `current_stage: "clarify"` (next advance goes to plan or run)

12. **Determine next stage**:
    - Route `small`: → `/forgeflow:execute` (skip plan, go straight to execution)
    - Route `medium` or `high`: → `/forgeflow:plan`

13. **Report**:
    - Clarified objective (1 sentence)
    - Detected: domains, project type, work mode
    - Route and next stage
    - Files created
    - **Environment warnings** (if any): "주의: <warning list>"

14. **Handle blocker questions** (if any exist in brief.json):
    - If `open_questions.blocker_questions` is non-empty, you MUST ask the user these questions before proceeding.
    - Present each blocker question with your recommended answer. Wait for user response.
    - After all blockers are resolved, update brief.json with the decided answers and set `ambiguity_score` accordingly.
    - Do NOT proceed to the next stage until all blockers are resolved.

15. **Close the stage**:
    - If no blocker questions remain, end with a closed next-stage question: `요구사항 충분. <route> route입니다. 다음 스텝으로 /forgeflow:<plan|execute>을 진행하시겠습니까? (y/n)`
    - Do NOT auto-proceed to the next stage without user confirmation.

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
