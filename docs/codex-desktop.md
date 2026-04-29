# Codex Desktop Usage

Codex uses project-root instructions and project-local presets. Treat `CODEX.md` as the persistent ForgeFlow surface.

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

Restart Codex Desktop after installing the local plugin entry. The global plugin entry is an entry point; project rules still belong in each target project.

## Install Into A Project

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

- Use the local plugin marketplace entry to make ForgeFlow discoverable in Codex.
- Start new work by asking Codex to read `CODEX.md` first.
- Keep task artifacts under `.forgeflow/tasks/<task-id>/`.
- Use `.codex/forgeflow` presets as role prompts, not as a second runtime.
- For real CLI execution through ForgeFlow, use `scripts/run_orchestrator.py ... --adapter codex --real` and confirm the JSON payload reports `"execution_mode": "real"`.

## Small Task Habit

For tiny changes, keep the route small and avoid unnecessary planning artifacts. For medium and high-risk work, require a written plan and independent review before ship.
