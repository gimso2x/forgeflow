# Generic Adapter Target

This directory contains a **reference template** for integrating ForgeFlow with agents that don't have a dedicated adapter (Gemini CLI, Cursor, Aider, Windsurf, etc.).

## What this is

- A manifest (`manifest.yaml`) that follows the same schema as Claude/Codex/Antigravity targets.
- A generated instruction file (`FORGEFLOW.md`) that any agent can consume as project context.

## What this is NOT

- A runtime adapter with hook support, CLI integration, or agent-specific tooling.
- A substitute for building a dedicated adapter when your agent needs deeper integration.

## How to use

### 1. Generate the adapter

```bash
python3 scripts/generate_adapters.py
```

This produces `adapters/generated/generic/FORGEFLOW.md`.

### 2. Copy to your project

```bash
cp adapters/generated/generic/FORGEFLOW.md /your/project/FORGEFLOW.md
```

### 3. Map ForgeFlow concepts to your agent

| ForgeFlow concept | Your agent equivalent |
|---|---|
| `plan.md` | Task list / todo file your agent reads |
| `work-report.json` | Commit message, PR description, or chat summary |
| `review-report.json` | Code review output in your agent's format |
| `.forgeflow/tasks/<id>/` | Your agent's workspace for tracking state |
| Stage gates (plan→work→review→done) | Your agent's workflow checkpoints |

### 4. Agent-specific tips

**Gemini CLI / Antigravity:**
- Include FORGEFLOW.md content in `AGENTS.md` at the project root.
- Gemini reads `AGENTS.md` as project context automatically.

**Cursor:**
- Add FORGEFLOW.md content to `.cursor/rules/` or reference it from `.cursorrules`.
- Cursor rules are injected into every conversation.

**Aider:**
- Use `--file FORGEFLOW.md` to include it in the chat context.
- Or add it to `.aider.conf.yml` under `read` files.

**Windsurf / other IDE agents:**
- Place in the project root and reference from your agent's instruction config.

## Key constraints

Regardless of which agent you use:

1. **Artifact-first**: All outputs must produce the standard ForgeFlow artifact files. Chat-only summaries don't count.
2. **Schema fidelity**: Preserve all keys and enums from canonical schemas. Don't rename, omit, or add fields.
3. **No hallucinated commands**: Only use commands your agent actually supports. Don't invent CLI flags or hooks.
4. **Verification required**: Agent self-report is never sufficient. Check artifacts exist and pass schema validation.
5. **Stage gates are mandatory**: Don't skip plan→work→review→done. Each transition requires the preceding artifact.

## Building a dedicated adapter

If your agent needs deeper integration (hooks, subagent orchestration, custom recovery), create a new directory under `adapters/targets/<your-agent>/` with:

- `manifest.yaml` — following `adapters/manifest.schema.json`
- Agent-specific files (hooks, rules, agent presets)

Then run `scripts/generate_adapters.py` to validate and generate.
