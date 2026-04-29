# Windows Support

ForgeFlow's Python runtime is cross-platform. The shell surface needs Windows-specific entry points because virtualenv executables live under `.venv\Scripts` instead of `.venv/bin`.

## PowerShell Setup

Run from the ForgeFlow checkout:

```powershell
.\scripts\setup.ps1
.\scripts\validate.ps1
```

`setup.ps1` creates `.venv`, installs `requirements.txt`, and runs the environment check. `validate.ps1` reuses the same virtualenv and runs the core deterministic validation set.

## Operator CLI

Use the wrapper when you want Windows path handling without remembering the virtualenv path:

```powershell
.\scripts\run_orchestrator.ps1 init --task-id my-task-001 --objective "Update README quickstart" --risk low
.\scripts\run_orchestrator.ps1 status --task-dir .\.forgeflow\tasks\my-task-001
```

## Codex Plugin Marketplace

To register ForgeFlow as a home-local Codex plugin entry:

```powershell
.\scripts\install_codex_plugin.ps1
```

This writes under `~/plugins/forgeflow` and `~/.agents/plugins/marketplace.json`. Re-run with `--force` only when replacing the existing local plugin copy is intentional.

## Make

GNU Make remains supported. On Windows, the Makefile resolves the repo-managed Python interpreter as `.venv/Scripts/python` when `OS=Windows_NT`.

## Notes

- Prefer PowerShell wrappers for first-clone setup on native Windows.
- WSL and Git Bash can continue using the documented `make setup`, `make check-env`, and `make validate` flow.
- Do not create task artifacts inside plugin caches. Pass an explicit project task directory when the current directory is under `.codex` or `.claude` plugin cache paths.
