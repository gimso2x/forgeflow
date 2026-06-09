# Adapter layout

ForgeFlow currently keeps adapter-facing files at the repository root because external tools and marketplaces expect those paths directly:

- `.claude-plugin/` — Claude Code plugin manifest surface
- `.codex-plugin/` — Codex plugin manifest surface
- `.cursor-plugin/` — Cursor local plugin manifest surface
- `.agents/`, `plugins/` — Codex marketplace compatibility surface

## Target direction (deferred — no current plan to execute)

> **Note**: This migration is deferred. Current root-level layout is validated and stable. No `adapters/` migration is planned unless marketplace/tooling requirements change.

Prefer a single managed adapter source tree such as `adapters/` for future cleanup:

```text
adapters/
  claude/
  codex/
  cursor/
```

The root-level compatibility paths should then be generated or symlinked at build/install time instead of hand-maintained independently.

## Migration rules

1. Keep current root-level paths until each supported tool is verified against generated/symlinked surfaces.
2. Add or modify adapter files in one canonical source location first; generated compatibility files must stay byte-for-byte predictable.
3. Install targets should copy or link complete adapter surfaces, not ask users to manually copy individual files.
4. Validation must keep checking the root compatibility paths while they are published entrypoints.
5. Do not move `.agents/plugins/marketplace.json`, `plugins/forgeflow`, `.codex-plugin/plugin.json`, `.claude-plugin/*`, or `.cursor-plugin/plugin.json` without an accompanying install/build target and README update.

This keeps the repository understandable while avoiding a breaking marketplace/layout change before the adapter generation path exists.
