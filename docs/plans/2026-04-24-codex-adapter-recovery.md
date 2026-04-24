# Codex Adapter Recovery Guidance

## Goal

Add Codex-specific recovery guidance so the generated `CODEX.md` steers the CLI away from repeated dead-end tool behavior without pretending Codex supports Claude plugin hooks.

## Constraints

- Keep canonical workflow semantics unchanged.
- Do not add Codex-only behavior to shared policy.
- Keep implementation adapter-local through the existing manifest/generator path.
- Prefer generated instruction guidance over fake hook support; Codex has no Claude-style hook manifest here.

## Acceptance Criteria

1. `adapters/targets/codex/manifest.yaml` names concrete recovery expectations for:
   - edit/write failures,
   - large file or oversized output failures,
   - repeated command/tool failures,
   - `/fast` or speed-mode shortcuts preserving artifact gates.
2. `adapters/generated/codex/CODEX.md` includes those recovery expectations after regeneration.
3. Validation fails if Codex recovery guidance regresses below the required phrases.
4. `make validate` passes.

## Verification

- Run the targeted Codex recovery validation/test first and observe failure before implementation.
- Regenerate adapters.
- Run full validation and smoke checks.
