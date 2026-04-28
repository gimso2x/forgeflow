# Shared Recovery Contract

## Goal

Centralize ForgeFlow recovery behavior into a canonical contract and make all generated adapters consume it, while preserving adapter-specific delivery mechanisms.

## Constraints

- Do not change stage semantics or artifact gates.
- Do not pretend every adapter supports hooks.
- Keep adapter-specific delivery notes in manifests.
- Generated adapter files must be regenerated, not hand-edited.

## Acceptance Criteria

1. A canonical recovery contract exists under `policy/canonical/`.
2. Generated adapters include a `## Recovery contract` section from the canonical source.
3. Claude and Codex generated adapters all include the same shared recovery rules.
4. Adapter-specific recovery delivery notes remain in each manifest/generator output.
5. Regression tests read the canonical contract instead of hardcoding three divergent phrase lists.
6. `make validate` and `make smoke-claude-plugin` pass.
