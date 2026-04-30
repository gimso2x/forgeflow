# Windows Support

ForgeFlow's Python runtime is cross-platform. The shell surface needs Windows-specific entry points because virtualenv executables live under `.venv\Scripts` instead of `.venv/bin`.

## PowerShell Setup

Run from the ForgeFlow checkout:

```powershell
.\scripts\setup.ps1
.\scripts\validate.ps1
```

`setup.ps1` creates `.venv`, installs `requirements.txt`, and runs the environment check. `validate.ps1` reuses the same virtualenv and runs the core deterministic validation set.

The wrappers discover Python in this order: `$env:PYTHON`, `python`, `py -3`, then `python3`. This lets native Windows use the standard Python launcher while WSL and Git Bash can keep using the Unix-oriented examples.

## Operator CLI

Use the wrapper when you want Windows path handling without remembering the virtualenv path:

```powershell
.\scripts\run_orchestrator.ps1 init --task-id my-task-001 --objective "Update README quickstart" --risk low
.\scripts\run_orchestrator.ps1 status --task-dir .\.forgeflow\tasks\my-task-001
```

The Python runtime executes approved project-local checks through subprocess argument lists, not POSIX shell pipelines. Rule previews should therefore avoid `python3`, `>/dev/null`, `2>&1`, and pipe-only examples unless the command is explicitly Unix-only.

## Codex Plugin Marketplace

To register ForgeFlow as a home-local Codex plugin entry:

```powershell
.\scripts\install_codex_plugin.ps1
```

This writes under `~/plugins/forgeflow` and `~/.agents/plugins/marketplace.json`. Re-run with `--force` only when replacing the existing local plugin copy is intentional.

For checkout-free bootstrap from PowerShell, use:

```powershell
irm https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python -
```

If `python` is not on PATH but the Windows launcher is, clone the repo and use `.\scripts\install_codex_plugin.ps1` so the wrapper can fall back to `py -3`.

## Make

GNU Make remains supported. On Windows, the Makefile resolves the repo-managed Python interpreter as `.venv/Scripts/python` when `OS=Windows_NT`.

## Notes

- Prefer PowerShell wrappers for first-clone setup on native Windows.
- WSL and Git Bash can continue using the documented `make setup`, `make check-env`, and `make validate` flow.
- GitHub Actions runs a `windows-smoke` job with `.\scripts\setup.ps1`, `.\scripts\validate.ps1`, and `.\scripts\run_orchestrator.ps1 init`.
- Do not create task artifacts inside plugin caches. Pass an explicit project task directory when the current directory is under `.codex` or `.claude` plugin cache paths.
