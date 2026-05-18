---
name: clarify
description: Turn a vague request into a scoped ForgeFlow brief and route decision. Use when the user types /forgeflow:clarify, or first for new implementation/refactor/debug requests unless the user already provided a complete brief.
version: 0.1.0
author: gimso2x
validate_prompt: |
  Must preserve exact-output and dry-run constraints when requested.
  Must return a clear route or brief artifact only when the prompt asks for it.
  Must default to artifact-first behavior and write `brief.json` to the active task directory unless the user explicitly requests dry-run or no-write output.
  Must include WHERE/risk grounding for non-trivial work when artifact writing is allowed.
---

# Clarify

Use this skill to convert a raw request into a ForgeFlow `brief.json`-style context brief and route decision.

## Input

- Raw user request
- Target repository/path if known
- Constraints, acceptance criteria, risk notes if provided
- Existing codebase context if available

## Output Artifacts

- `brief.json` or equivalent brief containing:
  - goal
  - where/context grounding for non-trivial work
  - constraints
  - acceptance criteria
  - scope boundary
  - non-goals
  - ambiguity score and ambiguity notes
  - open questions split into blocker questions vs non-blocking unknowns
  - hidden assumptions recorded as bounded assumptions
  - non-blocking unknowns / bounded assumptions
  - complexity score
  - route: `small`, `medium`, `high`, or `epic`
  - required_specialists: list of specialists (security-review, ux-review, perf-review, etc.)
  - skipped_specialists: list of specialists not used
  - skip_rationale: explanation for skipping specialists
  - min_verification: list of required verification steps for the run stage

## Exit Condition

- The request has a clear goal and scope boundary
- True blocker questions are answered; non-blocking unknowns are recorded as bounded assumptions
- A route is selected and justified
- Optional visual artifact is available when useful for design feedback: run `python3 scripts/forgeflow_visual.py clarify <task-dir>/brief.json --format markdown`, or pipe Mermaid output to `node scripts/visual-companion.cjs` via `POST /diagram`.
- Next skill is named:
  - `small` -> `/forgeflow:execute` or direct execute path
  - `medium` -> `/forgeflow:plan`
  - `high` -> `/forgeflow:plan` with spec/quality review kept separate
  - `epic` -> `/forgeflow:milestone`

## File write and output discipline

Default to **artifact-first mode**. Clarify should write `brief.json` under the active task directory unless the user explicitly asks for a dry run, exact-output response, or no-write simulation.

Canonical writable location:

- explicit task directory provided by the user, or
- repo-local `.forgeflow/tasks/<task-id>/` created via `/forgeflow:init` or `python3 scripts/run_orchestrator.py init ...`.

If the task directory is missing, stop pretending chat is state. Bootstrap the workspace first instead of returning a pseudo-brief in chat only.

If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.

When artifacts such as `brief.json` are mentioned without an explicit path, write them to the active task directory, not the repository root and not chat-only fallback.

If writing is allowed, write only under the current project workspace or the active task directory. Never write inside the plugin installation directory, marketplace cache, or `skills/<skill>/`.


## Strict response constraints

Exact-output instructions beat every other rule in this skill. Do not explain first and then append the answer. Do not show scoring. Do not include Markdown. Return exactly what was requested and nothing extra.

If the user asks for a label-only route selection (for example "Return only the selected route label", "label only", or "route label only"), output exactly one of `small`, `medium`, `high`, or `epic` and stop. The entire response must be only that label.

Bad:

```text
This is medium because it touches shared state.
medium
```

Good:

```text
medium
```

Bad: adding verdicts, JSON artifacts, rationale sections, headings, scoring, or extra warnings after the requested label/list.
Good: if asked for exactly two checks, return exactly two checks.

When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.

For exact-count question prompts, start directly with `1.`. Do not explain that you will generate questions, do not mention the skill/procedure, and do not add any preamble before the numbered list.

If the user asks to list questions, list them in the response. Do **not** call an interactive question tool unless the user explicitly asks for an interactive clarification flow.

## WHERE grounding

Before routing anything non-trivial, calibrate WHERE so intake is neither too heavy for toys nor too light for dangerous work.

Capture these fields in `brief.json` when the user has not already provided them:

- `project_type`: user-facing app, API/service, dev tool/library, or infrastructure
- `situation`: greenfield, brownfield extension, brownfield refactor, or hybrid
- `ambition`: toy/experiment, feature/MVP, or product
- `risk_modifiers`: sensitive data, external exposure, irreversible ops, high scale

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
   - Surface confusion instead of guessing. If the request has competing interpretations that materially change scope, say so in the brief.
   - For brownfield refactors or extensions, specifically identify **architectural friction**: where are modules **shallow** (interface as complex as implementation), where is **locality** missing, and where are **pass-throughs** bloating the path? (See `docs/refactor-planning-decision.md`).
   - Do not silently pick one interpretation when the ambiguity affects user-visible behavior, data, security, or files to edit.
   - **Environment preflight**: Run these checks and record results in brief.json under `"environment_preflight"`:
     - `git rev-parse --is-inside-work-tree 2>/dev/null` → if not a git repo, add `"environment_warnings": ["not_a_git_repo"]`
     - Check for lockfile + dependency directory mismatch (e.g., `pnpm-lock.yaml` exists but no `node_modules`): add to `open_questions.blocker_questions`: "종속성이 설치되지 않았습니다. execute 전에 설치를 진행하시겠습니까?"
     - If neither lockfile nor dependency directory exists: new project, skip silently.
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
5. Score complexity:
   - 5-8: `small` — one localized change, usually 1-2 files, low ambiguity, no cross-cutting behavior.
   - 9-12: `medium` — several coordinated files/components, shared state/layout/navigation, moderate test/update surface, but no security/data migration/infra rollback risk.
   - 13-15: `high` — auth/security, data migration, payments, production infra, irreversible data changes, broad architecture migration, or many contracts/journeys requiring separate spec and quality review.
   - 16+: `epic` — massive scope, hierarchical milestone breakdown, multi-week effort.
6. Select specialists based on task nature:
   - Auth/Encryption/External Input -> `security-review`
   - UI/Accessibility/User Flow -> `ux-review`
   - Response time/Memory/Large data -> `perf-review`
   - Frontend focused -> `frontend-execute`
   - Backend/API/DB -> `backend-execute`
   - Infra/Deployment/IaC -> `infra-execute`
   - List skipped specialists and provide a `skip_rationale`.
7. Set `min_verification` in the brief:
   - `small`: at least one of `build`, `lint`, or `type_check` — whichever is available and fastest.
   - `medium`: at least `lint` and `type_check`, plus `test` if tests exist for changed files.
   - `high`: full verification suite — `build`, `lint`, `type_check`, and `test`.
   - `epic`: full verification suite, plus milestone-level integration tests.
8. State the route and why, unless an exact-output/label-only instruction applies.
9. Produce the brief in a structured form the next skill can consume, unless an exact-output/label-only instruction applies.
10. If the request is actionable, record remaining non-blocking unknowns as bounded assumptions and make the next stage obvious without asking the user to do your planning work, unless an exact-output/label-only instruction applies.

Do not implement here. Clarify is the intake gate, not the coding phase.

## UX guardrails

- Do repo inspection before saying the scope is unclear.
- Do not manufacture open questions just to prolong intake; `non-blocking unknowns` are artifact notes, not questions the user must answer.
- Do not ask the user to write the plan for you.
- Do not ask the user to approve the brief content again when the request is already sufficient.
- Do stop at the stage boundary before starting `/forgeflow:plan` or `/forgeflow:execute`.
- **If brief.json has blocker_questions, you MUST ask the user those questions interactively before closing the stage.** Present each blocker with your recommended answer. Wait for user response. Update the brief with decided answers afterward. Do NOT skip this step and do NOT embed questions only in the file.
- When the request is already sufficient and all blockers are resolved, end with a closed next-stage question: `요구사항 충분. <route> route입니다. 다음 스텝으로 /forgeflow:<plan|execute>을 진행하시겠습니까? (y/n)`
- Bad: writing blocker questions to brief.json and immediately reporting "next stage: plan" without asking.
- Good: presenting blocker questions to the user, getting answers, updating the brief, then asking to proceed.

## Output mode examples

If asked:

```text
/forgeflow:clarify Add a README badge. Return only the selected route label. Do not write files.
```

Return only one of:

```text
small
medium
high
```

No explanation. No JSON. No file writes.
h
```

No explanation. No JSON. No file writes.
