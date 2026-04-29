# Codex Desktop Usage

Codex can start from the ForgeFlow plugin directly. Treat `/forgeflow:<stage>` prompts as the normal user-facing entrypoints.

`CODEX.md` and project-local presets are optional hardening surfaces when a project needs persistent rules beyond the installed plugin.

## Add ForgeFlow To The Local Plugin Marketplace

From a ForgeFlow checkout:

```bash
python3 scripts/install_codex_plugin.py
```

Windows PowerShell:

```powershell
.\scripts\install_codex_plugin.ps1
```

This creates or updates:

```text
~/plugins/forgeflow/
~/.agents/plugins/marketplace.json
```

Restart Codex Desktop after installing the local plugin entry. Then enable ForgeFlow from the local marketplace if prompted.

Use the plugin with slash-style prompts:

```text
/forgeflow:init --task-id <id> --objective "<objective>" --risk low|medium|high
/forgeflow:clarify <task>
/forgeflow:plan
/forgeflow:run
/forgeflow:review
/forgeflow:ship
/forgeflow:finish
```

Codex plugins expose skills rather than Claude-style native slash command registrations. ForgeFlow skills intentionally accept these slash-style prompts as triggers, so the user-facing flow is the same.

## Optional: Install Into A Project

From a ForgeFlow checkout:

```bash
python3 scripts/install_agent_presets.py --adapter codex --target /path/to/your-project --profile nextjs --install-codex-md
```

This creates:

```text
/path/to/your-project/CODEX.md
/path/to/your-project/.codex/forgeflow/forgeflow-coordinator.md
/path/to/your-project/.codex/forgeflow/forgeflow-nextjs-worker.md
/path/to/your-project/.codex/forgeflow/forgeflow-quality-reviewer.md
/path/to/your-project/.codex/rules/forgeflow-nextjs-worker.mdc
/path/to/your-project/docs/forgeflow-team-init.md
```

If `CODEX.md` already exists, the installer preserves it. Use `--overwrite-codex-md` only when replacing it is intentional.

## Operating Model

- Use the local plugin marketplace entry as the default Codex entrypoint.
- Start new work with `/forgeflow:clarify <task>` or `/forgeflow:init ...`.
- Install `CODEX.md` only when a project needs persistent local rules in addition to the plugin.
- Keep task artifacts under `.forgeflow/tasks/<task-id>/` when artifact-backed state is needed.
- Use `.codex/forgeflow` presets as role prompts, not as a second runtime.
- For real CLI execution through ForgeFlow, use `scripts/run_orchestrator.py ... --adapter codex --real` and confirm the JSON payload reports `"execution_mode": "real"`.

## Small Task Habit

For tiny changes, keep the route small and avoid unnecessary planning artifacts. For medium and high-risk work, require a written plan and independent review before ship.
