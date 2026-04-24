# 2026-04-24 Team Pattern Contract

## Goal

Absorb the useful part of `revfactory/harness`: an adapter-neutral vocabulary for choosing orchestration shape without importing Claude-specific runtime primitives.

## Scope

- Add `policy/canonical/team-patterns.yaml`.
- Include team pattern guidance in generated adapters.
- Add tests that ensure the contract exists, stays adapter-neutral, and is generated into every adapter surface.
- Wire the smoke test into `make validate`.

## Non-goals

- Do not add Claude-only `TeamCreate`, `SendMessage`, or `TaskCreate` to canonical policy.
- Do not generate `.claude/agents` or `.claude/skills` from ForgeFlow.
- Do not change the existing stage/gate semantics.

## Acceptance criteria

- `pytest tests/test_team_pattern_contract.py -q` passes.
- `make validate` passes.
- Generated Claude/Codex/Cursor adapter docs include `## Team pattern guidance`.
