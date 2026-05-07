# 0002. Harness absorption boundary

Date: 2026-05-08
Status: accepted

## Context

A harness absorption memo identified reusable operating ideas that should affect ForgeFlow without importing another harness wholesale:

- manage task instructions, status, and logs in one orchestration surface;
- validate on a sample before broad rollout;
- turn repeated work into templates or modules.

ForgeFlow already has artifact-first stages, gates, and local evidence. The decision here is how to absorb the memo as durable operating contracts rather than as a new workflow stack.

## Decision

ForgeFlow absorbs these ideas as an adapter-neutral orchestration contract:

1. `brief.json`, `plan-ledger.json`, `run-state.json`, review reports, and evidence refs remain the single local source for instructions, status, and logs.
2. Any broad rollout must start with a focused sample smoke or fixture before changing generated adapters, canonical prompts, or installed project scaffolds.
3. Repeated agent instructions should be promoted into reusable skills, templates, runtime modules, or contract tests instead of being copied into one-off prompts.

## Adopted

- One-place orchestration via task artifacts and evidence refs.
- Sample-first verification before full adapter/plugin rollout.
- Template/module extraction for repeated operating procedures.

## Adapted

- The memo's “orchestration rules” become contract tests and documentation around existing artifacts, not a new command router.
- “Logs” means compact evidence refs and review artifacts unless a runtime module explicitly owns richer telemetry.
- “Templates/modules” must remain stdlib-only and adapter-neutral when they enter `forgeflow_runtime/`.

## Rejected

- No parallel workflow engine.
- No hidden chat-memory source of truth.
- No automatic wide rollout without a focused sample validation step.
- No wholesale copy of external harness directory structures.

## Consequences

- Future absorption tasks should cite the exact artifact, skill, template, runtime module, or contract test they change.
- If an idea cannot be verified on a sample, it stays in a plan/task note rather than entering generated adapters.
- Adapter-specific prompts may repeat the contract only after the canonical source is updated and regenerated.

## Validation

- `tests/test_plugin_skill_contracts.py::test_harness_absorption_decision_records_forgeflow_boundary`
- `python3 scripts/validate_structure.py`
