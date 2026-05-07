# Harness Absorption Reflection Task

Date: 2026-05-08
Owner: ForgeFlow
Status: completed

## Source Memo

- Obsidian: `Inbox/2026-05-08 [개발전] 하네스 흡수 반영.md`

## Goal

Reflect the reusable harness ideas into ForgeFlow as durable contracts while keeping the runtime thin and artifact-first.

## Absorbed Into ForgeFlow

1. **One orchestration surface**
   - Canonical source: `.forgeflow/tasks/<task-id>/` artifacts.
   - Durable decision: `docs/decisions/0002-harness-absorption-boundary.md`.
   - Contract: task instructions, status, and evidence stay in `brief.json`, `plan-ledger.json`, `run-state.json`, review reports, and evidence refs.
2. **Sample-first rollout**
   - Any broad adapter/plugin/prompt change must be validated on a focused sample smoke or fixture first.
   - Full rollout follows only after the sample behavior is understood.
3. **Template/module extraction**
   - Repeated operating procedures should become skills, templates, runtime modules, or contract tests.
   - One-off prompt copy-paste is not a durable absorption path.

## Non-goals

- No new workflow engine.
- No full external harness scaffold import.
- No new installed hook.
- No hidden memory/log source outside task artifacts for this slice.

## Verification

- Added a contract test so the decision cannot silently disappear:
  - `tests/test_plugin_skill_contracts.py::test_harness_absorption_decision_records_forgeflow_boundary`
- Ran focused test:
  - `python3 -m pytest tests/test_plugin_skill_contracts.py::test_harness_absorption_decision_records_forgeflow_boundary -q`
- Ran structure validation:
  - `python3 scripts/validate_structure.py`

## Hermes Follow-up Boundary

The memo also names Hermes runtime/capability/safety/context ideas. Those belong in the Hermes Agent repo, but that worktree already has unrelated dirty changes. Do not mix this ForgeFlow absorption with the existing Hermes worktree state; handle Hermes in a separate clean slice or after the active changes are resolved.
