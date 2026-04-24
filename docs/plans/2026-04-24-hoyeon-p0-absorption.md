# Hoyeon P0 Absorption Implementation Plan

> **For Hermes:** Execute this plan task-by-task. Keep ForgeFlow multi-adapter; do not copy Hoyeon's Claude-only runtime wholesale.

**Goal:** Absorb Hoyeon's strongest requirements-first planning mechanics into ForgeFlow: contract-first plan metadata, verify-plan/journey traceability, WHERE grounding, and a lightweight plan mutation CLI.

**Architecture:** Keep ForgeFlow's compact command surface. Translate Hoyeon concepts into ForgeFlow-native schema, skills, fixtures, and validation scripts. Upstream Hoyeon content can be mirrored as reference, but runtime changes must be small, testable, and adapter-neutral.

**Tech Stack:** Python validation/runtime scripts, JSON Schema, Markdown skills/docs, Makefile validation, Claude plugin smoke tests.

---

## Acceptance Criteria

- `make validate` passes after every implementation slice.
- `make smoke-claude-plugin` passes after skill/prompt-facing changes.
- Hoyeon upstream P0 reference files are mirrored with drift validation, like engineering-discipline.
- ForgeFlow `plan.json` supports optional `contracts`, `journeys`, and `verify_plan` fields without breaking existing minimal plans.
- Sample artifact validation rejects inconsistent `fulfills`/`verify_plan`, `journeys`/`verify_plan`, and dependency references.
- `skills/specify/SKILL.md` includes WHERE grounding and brownfield research guidance.
- A lightweight Python plan CLI exists for `validate`, `list`, and `task --status` state mutation.

---

## Task 1: Mirror Hoyeon P0 upstream references

**Objective:** Vendor the Hoyeon files needed for future comparison without expanding ForgeFlow's command surface.

**Files:**
- Create: `docs/upstream/hoyeon/README.md`
- Create: `docs/upstream/hoyeon/skills/specify.md`
- Create: `docs/upstream/hoyeon/skills/blueprint.md`
- Create: `docs/upstream/hoyeon/skills/execute.md`
- Create: `docs/upstream/hoyeon/skills/compound.md`
- Create: `docs/upstream/hoyeon/cli/plan.js`
- Create: `docs/upstream/hoyeon/hooks/hooks.json`
- Create: `scripts/validate_hoyeon_import.py`
- Modify: `Makefile`

**Steps:**
1. Copy the selected source files from `/tmp/hoyeon-analysis` into `docs/upstream/hoyeon/`.
2. Generate `docs/upstream/hoyeon/README.md` with source path, SHA-256, and bytes.
3. Add `scripts/validate_hoyeon_import.py` to compare mirror hashes against `/tmp/hoyeon-analysis` or `/home/ubuntu/hoyeon` if present.
4. Add `validate-hoyeon-import` target to `Makefile` and include it in `validate`.
5. Run `make validate-hoyeon-import && make validate`.
6. Commit: `docs: vendor hoyeon p0 references`.

---

## Task 2: Extend plan schema for contracts, journeys, and verify_plan

**Objective:** Add Hoyeon's traceability model as optional ForgeFlow plan metadata while preserving existing plans.

**Files:**
- Modify: `schemas/plan.schema.json`
- Modify: `skills/plan/SKILL.md`
- Modify: `skills/run/SKILL.md`
- Modify: `examples/runtime-fixtures/*/plan.json` only if needed by validation

**Schema additions:**
- Optional `contracts` object:
  - `artifact`: string or null
  - `interfaces`: string array
  - `invariants`: string array
- Optional `journeys` array:
  - each item requires `id`, `description`, `composes`
- Optional `verify_plan` array:
  - each item requires `target`, `type`, `gates`
  - `type`: `sub_req`, `journey`, or `step`
  - `gates`: array of integers or strings
- Optional step field `fulfills`: string array
- Optional step field `status`: `pending`, `in_progress`, `completed`, `failed`, `blocked`

**Steps:**
1. Update schema with optional fields only.
2. Update `skills/plan/SKILL.md` to add contract-first planning guidance for medium/large and brownfield work.
3. Update `skills/run/SKILL.md` to treat `contracts` and `verify_plan` as execution constraints when present.
4. Run `make validate`.
5. Commit: `feat: add contract traceability to plan schema`.

---

## Task 3: Add artifact validation for plan traceability

**Objective:** Make traceability mechanical, not vibes.

**Files:**
- Modify: `scripts/validate_sample_artifacts.py`
- Modify: `scripts/run_adherence_evals.py`
- Create fixtures under `examples/runtime-fixtures/negative/` as needed

**Validation rules:**
1. Every `steps[].dependencies[]` must reference an existing step ID.
2. Every `steps[].fulfills[]` must have a `verify_plan` entry of `type=sub_req` or `type=step` targeting it.
3. Every `journeys[].composes[]` must have a `verify_plan` entry of `type=sub_req` or `type=step` targeting it.
4. Every `journeys[].id` must have a `verify_plan` entry of `type=journey`.
5. Every `verify_plan` entry of `type=journey` must reference an existing journey.
6. If `contracts.artifact` is non-null, that file must exist beside `plan.json`.

**Steps:**
1. Add helper validation function for plan traceability.
2. Add negative fixture for missing verify target.
3. Add negative fixture for missing contracts artifact.
4. Add negative fixture for stale journey verify target.
5. Run `make validate`.
6. Commit: `test: validate plan traceability metadata`.

---

## Task 4: Add WHERE grounding to specify

**Objective:** Bring Hoyeon's scope/risk calibration into ForgeFlow's specify stage.

**Files:**
- Modify: `skills/specify/SKILL.md`
- Optionally modify: `scripts/smoke_claude_plugin.py` if exact-output prompts become flaky

**Content to add:**
- WHERE fields: `project_type`, `situation`, `ambition`, `risk_modifiers`
- Risk escalation matrix:
  - sensitive data → security/data deep
  - external exposure → security/access deep
  - irreversible ops → risk/compat deep
  - high scale → infra/architecture deep
- Brownfield rule: inspect repo facts before asking factual questions.
- Output discipline: WHERE can be summarized in requirements, but exact-output dry runs must stay exact.

**Steps:**
1. Patch `skills/specify/SKILL.md` with WHERE section before Procedure.
2. Keep response-only and exact-output constraints intact.
3. Run `make validate && make smoke-claude-plugin`.
4. Commit: `docs: add where grounding to specify`.

---

## Task 5: Add lightweight ForgeFlow plan CLI

**Objective:** Provide a small local CLI for plan validation/list/status mutation without importing Hoyeon's npm CLI.

**Files:**
- Create: `scripts/forgeflow_plan.py`
- Modify: `Makefile`
- Create/update: `examples/runtime-fixtures/plan-cli-task/plan.json` if useful

**Commands:**
```bash
python3 scripts/forgeflow_plan.py validate <task_dir>
python3 scripts/forgeflow_plan.py list <task_dir> [--status completed]
python3 scripts/forgeflow_plan.py task <task_dir> --status step-1=completed [--summary '...']
```

**Rules:**
- Mutate only `plan.json` in the given task directory.
- Status values: `pending`, `in_progress`, `completed`, `failed`, `blocked`.
- Re-setting the same status is idempotent.
- A completed step cannot transition backward.
- Validate schema and traceability after mutation.

**Steps:**
1. Implement CLI using Python stdlib only.
2. Add `plan-cli-smoke` target to `Makefile`.
3. Add smoke coverage for validate/list/task transition/idempotence/backward-block.
4. Run `make validate && make plan-cli-smoke`.
5. Commit: `feat: add forgeflow plan cli`.

---

## Task 6: Final integration verification

**Objective:** Prove all absorbed pieces are stable together.

**Files:**
- Modify: docs only if final notes are needed

**Steps:**
1. Run `make validate`.
2. Run `make smoke-claude-plugin`.
3. Run `git status --short` and confirm clean.
4. Summarize commits and residual P1/P2 items.
