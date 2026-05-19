---
name: clarify
description: Turn a vague request into a scoped ForgeFlow brief and route decision. Use when the user types /forgeflow:clarify, or first for new implementation/refactor/debug requests unless the user already provided a complete brief.
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must return a clear route or brief artifact only when the prompt asks for it.
  Must default to artifact-first behavior and write `brief.md` to the active task directory unless the user explicitly requests dry-run or no-write output.
  Must include WHERE/risk grounding for non-trivial work when artifact writing is allowed.
---

# Clarify

Use this skill to convert a raw request into a ForgeFlow context brief (`brief.md`) and route decision.

## Input

- Raw user request
- Target repository/path if known
- Constraints, acceptance criteria, risk notes if provided
- Existing codebase context if available

## Output Artifacts

Write `brief.md` to the active task directory using `templates/brief.md` as the structure. The brief must capture:

- Objective (one-sentence goal)
- WHERE/context grounding for non-trivial work
- In Scope / Out of Scope boundary
- Constraints
- Acceptance Criteria
- Risk Level
- Assumptions (including bounded assumptions for non-blocking unknowns)
- Open Questions (blocker vs non-blocking)
- Specialists (required, skipped, skip rationale)
- Verification Gates (auto-detected from tech stack)
- Environment Notes (git status, dependency check, tech stack detected)
- Route selection and rationale

## Exit Condition

- The request has a clear goal and scope boundary
- True blocker questions are answered; non-blocking unknowns are recorded as bounded assumptions
- A route is selected and justified
- Next skill is named:
  - `small` -> `/forgeflow:execute` or direct execute path
  - `medium` -> `/forgeflow:plan`
  - `high` -> `/forgeflow:plan` with spec/quality review kept separate
  - `epic` -> `/forgeflow:milestone`

## File write and output discipline

Default to **artifact-first mode**. Write `brief.md` under `.forgeflow/tasks/<task-id>/` unless the user explicitly asks for a dry run, exact-output response, or no-write simulation.

If the task directory is missing, create `.forgeflow/tasks/<task-id>/` first. Do not return a pseudo-brief in chat only when the workflow expects artifacts.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

Write only under the current project workspace or the active task directory. Never write inside `skills/<skill>/`.

## Strict response constraints

When the user requests an exact output (label only, list only, dry run), return exactly that — nothing extra. Exact-output instructions override all other formatting rules. The user asked for precision; give them precision.

- Label-only route: output exactly `small`, `medium`, `high`, or `epic` and stop.
- Exact-count questions: start directly with `1.` — no preamble.
- List questions: list them inline. Do not call interactive tools unless the user asks.
- "Do not run commands": name manual checks as "manual inspection", not as if they ran.

## Evolution preflight

Unless the prompt is exact-output, label-only, dry-run, or says not to inspect files, check evolution rules before route selection:

1. Load project active rules from `.forgeflow/evolution/active/*.md` if the directory exists.
2. Load global advisory rules from `~/.forgeflow/evolution/active/*.md` if available.
3. Match rules by their `Trigger` and `Application Stage` fields.
4. Record matching rules in the brief's `Applied Evolution Rules` section.
5. Project active rules are required constraints for this repository. Global rules are advisory only: they may guide clarify/plan, but they must not block or force hard enforcement.
6. If a project active rule conflicts with the user request, surface it as a blocker question with a recommended resolution.

This is how ForgeFlow learns from prior work: long-run proposes rules, review validates them, active rules are loaded automatically by future clarify/plan/execute stages.

## WHERE grounding

Before routing anything non-trivial, calibrate WHERE so intake is neither too heavy for toys nor too light for dangerous work.

Capture these dimensions in the brief when the user has not already provided them:

- **project_type**: user-facing app, API/service, dev tool/library, or infrastructure
- **situation**: greenfield, brownfield extension, brownfield refactor, or hybrid
- **ambition**: toy/experiment, feature/MVP, or product
- **risk_modifiers**: sensitive data, external exposure, irreversible ops, high scale

Risk escalation rules:

- Sensitive data -> security and data requirements must be deep.
- External exposure -> security and access requirements must be deep.
- Irreversible ops -> risk and compatibility requirements must be deep.
- High scale -> infrastructure and architecture requirements must be deep.

Situation rules:

- Greenfield: ask enough to define behavior and core architecture, but do not invent enterprise ceremony.
- Brownfield extension: inspect existing code and docs before asking factual questions; ask about decisions and tradeoffs, not facts the repo can answer.
- Brownfield refactor: compatibility, callers, migration path, and rollback are first-class requirements.
- Hybrid: separate new-module behavior from integration constraints.

For exact-count, dry-run, or response-only prompts, do not force the WHERE interview. Obey the requested output exactly.

## Procedure

1. Inspect relevant repo context before inventing scope.
   - Run the Evolution preflight first when allowed, then map matched rules into brief.md.
   - Map Instructions, Tools, Environment, State, and Feedback into brief fields. Use Environment Notes, tech stack, Open Questions, and Verification Gates for missing context instead of creating a separate harness artifact.
   - If an Environment or Tools gap prevents execution, add it to Open Questions as a blocker and ask before routing to plan or execute.
   - Surface confusion instead of guessing. If the request has competing interpretations that materially change scope, say so in the brief.
   - For brownfield refactors or extensions, specifically identify **architectural friction**: where are modules **shallow** (interface as complex as implementation), where is **locality** missing, and where are **pass-throughs** bloating the path?
   - Do not silently pick one interpretation when the ambiguity affects user-visible behavior, data, security, or files to edit.
   - **Environment preflight**: Run these checks and record results in the Environment Notes section of brief.md:
     - `git rev-parse --show-toplevel 2>/dev/null` -> confirm the correct git root matches the target project directory. If mismatched, note the warning.
     - `git rev-parse --is-inside-work-tree 2>/dev/null` -> if not a git repo, note the warning.
     - Check for lockfile + dependency directory mismatch (e.g., `pnpm-lock.yaml` exists but no `node_modules`): add to Open Questions: "종속성이 설치되지 않았습니다. execute 전에 설치를 진행하시겠습니까?"
     - If neither lockfile nor dependency directory exists: new project, skip silently.
   - **Tech stack detection**: Auto-detect the framework/build tool from project files and record in brief.md. Check for:
     - `package.json` -> read dependencies for framework signals (next, react, vue, svelte, nuxt)
     - `pyproject.toml` or `requirements.txt` -> Python (FastAPI/Django/Flask)
     - `Cargo.toml` -> Rust
     - `go.mod` -> Go
     - If detected tech stack contradicts the user's request, add to Open Questions as a blocker.

2. Establish WHERE grounding unless the prompt is an exact-output dry run.

3. Ask up to 5 clarifying questions when they materially improve requirements. Ask 0 if the request is already actionable, and do not pad the list with nice-to-have trivia.
   - Good questions resolve product behavior, user/audience, success criteria, data/source of truth, rollout/risk constraints, or explicit out-of-scope boundaries.
   - Bad questions ask for implementation chores the agent should infer from repo inspection, preferences that do not change the plan, or confirmations that can be recorded as bounded assumptions.

4. Apply Socratic clarification (the "grilling loop") before route selection:
   - Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.
   - For each question asked, provide your recommended answer to reduce user cognitive load.
   - If a question can be answered by exploring the codebase, explore the codebase instead of asking.
   - Name the hidden assumptions the request appears to rely on.
   - Separate true blocker questions from non-blocking unknowns.
   - State explicit non-goals and scope boundaries before planning.
   - Assign an ambiguity score from `0.0` to `1.0`; above `0.2`, either ask blocker questions or record why execution can proceed safely with bounded assumptions.
   - Do not let ambiguity disappear into prose. It must be visible in the brief artifact or response artifact.

5. Score complexity using the documented weighted model:
   ```text
   raw_score = file_count*1.0 + estimated_lines*0.1 + requirement_count*2.0 + dependency_count*1.5 + risk_keywords*3.0
   ```
   - `< 10`: `small` — one localized change, usually 1-2 files, low ambiguity, no cross-cutting behavior.
   - `10-16.9`: `medium-light` — several coordinated files/components, scoped state/layout/navigation, moderate test/update surface, but no security/data migration/infra rollback risk.
   - `17-24.9`: `medium-full` — cross-module or service-level changes that still avoid high-risk auth/security/data/infra boundaries.
   - `25-49.9`: `high` — auth/security, data migration, payments, production infra, irreversible data changes, broad architecture migration, or many contracts/journeys requiring separate spec and quality review.
   - `>= 50`: `epic` — massive scope, hierarchical milestone breakdown, multi-week effort.

   Return route label `medium` for both `medium-light` and `medium-full`; record the sub-band in route rationale. The `17.0` mid threshold exists to decide how deep the plan/review detail should be inside the medium route, not to create a separate slash route.

6. Select specialists based on task nature:
   - Auth/Encryption/External Input -> `security-review`
   - UI/Accessibility/User Flow -> `ux-review`
   - Response time/Memory/Large data -> `perf-review`
   - Frontend focused -> `frontend-execute`
   - Backend/API/DB -> `backend-execute`
   - Infra/Deployment/IaC -> `infra-execute`
   - List skipped specialists and provide a skip rationale.

7. Set verification gates in the brief:
   - `small`: at least one of `build`, `lint`, or `type_check` — whichever is available and fastest.
   - `medium`: at least `lint` and `type_check`, plus `test` if tests exist for changed files.
   - `high`: full verification suite — `build`, `lint`, `type_check`, and `test`.
   - `epic`: full verification suite, plus milestone-level integration tests.

8. State the route and why, unless an exact-output/label-only instruction applies.

9. Produce `brief.md` using `templates/brief.md` as the structure, unless an exact-output/label-only instruction applies.

10. If the request is actionable, record remaining non-blocking unknowns as bounded assumptions and make the next stage obvious without asking the user to do your planning work, unless an exact-output/label-only instruction applies.

Do not implement here. Clarify is the intake gate, not the coding phase.

## Contract-first traceability for medium/high/epic or brownfield work

For non-trivial work, identify cross-module contracts before route selection:

1. Identify interfaces, invariants, data shapes, and compatibility constraints that parallel workers must not break.
2. If any contract exists, note it in the brief's Constraints section.
3. Record `fulfills` targets for traceability.
4. Identify journeys (multi-step user or system flows that require end-to-end verification).
5. Preserve non-goals and bounded assumptions when they affect execution boundaries.

Small documentation-only tasks may omit these.

## Auto-detectable verification gates

When constructing verification gates, prefer automated gates over manual review wherever possible.

| Gate | Description | Applicable when |
|------|-------------|-----------------|
| `scope_boundary_check` | Verify no unintended files changed via git diff | All tasks |
| `contract_check` | Verify step output against stated contracts | Tasks with cross-module contracts |
| `version_consistency_check` | Verify version strings match across artifacts | Tasks referencing package versions |
| `build` | Build passes | Code tasks |
| `lint` | Linter passes | Code tasks |
| `type_check` | Type checker passes | Typed code tasks |
| `test` | Test suite passes | Code tasks with tests |

## UX guardrails

The goal is to gather just enough information to route correctly — not to run an interrogation. The user came to build something, not to fill out forms.

- Inspect the repo before saying the scope is unclear. Most factual questions can be answered by reading code.
- Don't manufacture open questions to prolong intake. Non-blocking unknowns go into the brief as bounded assumptions.
- Don't ask the user to write the plan for you. That's your job.
- If the request is already actionable, skip directly to route selection and brief output.
- Stop at the stage boundary. Do not proceed to plan/execute without user confirmation.

**Blocker handling**: If brief.md has unresolved blockers, present each one to the user with your recommended answer. Wait for their response. Update the brief. Only then close the stage.

When all blockers are resolved, end with:
```
요구사항 충분. <route> route입니다. 다음 스텝으로 /forgeflow:<plan|execute>을 진행하시겠습니까? (y/n)
```

## Output mode examples

For label-only requests like `/forgeflow:clarify Add a README badge. Return only the selected route label.`:
Return exactly one of `small`, `medium`, `high`, or `epic`. No explanation, no file writes.
