# CI Smoke Strategy

ForgeFlow uses a two-tier smoke strategy so CI stays deterministic while real plugin execution remains available on demand.

## Tier 1 — CI (always runs, deterministic)

- Triggered on every push/PR via `plugin-smoke-matrix`.
- Verifies:
  - packaging integrity
  - preset install structure
  - doctor script output
  - non-mutating guard (`git status` stays clean after smoke)
- Does **not** require Claude/Codex CLI login.
- Safe to run in any environment.

GitHub Actions runners do not have real Claude or Codex CLI installed. A green CI badge means the plugin package and preset surfaces are structurally valid; it does **not** prove actual slash skill execution, real model invocation, or the plugin enable flow.

## Tier 2 — Local end-to-end smoke (on-demand)

- Run manually:

```bash
make smoke-claude-plugin
```

- Requires: `claude login` with valid quota.
- Verifies:
  - actual slash skill invocation
  - plugin enable flow
  - real CLI response
- Affected by:
  - Claude CLI login state
  - quota limits
  - plugin cache

## When to run Tier 2

- Before a new release tag.
- After changes to `.claude-plugin/plugin.json` or any skill file.
- When troubleshooting "plugin installed but slash command not working".
