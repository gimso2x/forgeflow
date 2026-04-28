# Cursor Adapter Recovery Guidance

> Archived note: the Cursor adapter surface was removed from the active repo. This plan remains only as historical context for the dropped slice.

## Goal

Document the dropped plan that would have added Cursor-specific recovery guidance so `.cursor/rules/forgeflow.mdc` preserved ForgeFlow gates while handling editor-agent failure loops.

## Constraints

- Keep this as rule-file guidance; do not invent hook support.
- Keep canonical workflow semantics unchanged.
- Cursor runs inside an editor context, so recovery must emphasize file re-read, diff review, and chat summary boundaries.

## Acceptance Criteria

1. `adapters/targets/cursor/manifest.yaml` would include concrete recovery expectations for:
   - failed edits requiring file re-read and diff review,
   - large files or noisy context requiring targeted search/chunked reads,
   - repeated failures requiring a strategy change,
   - chat summaries not replacing artifact gates,
   - Cursor fast/apply shortcuts not bypassing review gates.
2. `adapters/generated/cursor/HARNESS_CURSOR.md` would include the same recovery guidance after regeneration.
3. A regression test would fail before the guidance existed and pass after implementation.
4. `make validate` and `make smoke-claude-plugin` would pass.
