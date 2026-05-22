# Dogfooding fixtures

Some `.forgeflow/tasks/*` directories in this repository are **intentionally tracked** as validation fixtures and workflow smoke examples. They demonstrate real artifact output from ForgeFlow development tasks (e.g. `forgeflow-context-efficiency`, `validate-skill-frontmatter`).

Normal consumer projects should keep `.forgeflow/` gitignored. This repo tracks selected task folders to:

- Exercise `make validate` eval file references
- Preserve evidence from contract changes
- Serve as reference implementations for artifact structure

Do not treat tracked task folders as runtime state for the ForgeFlow plugin itself.

## Cleanup safety

Do not run broad cleanup commands such as `git clean -fdX` in this repository. Ignored paths can include local operator state such as `.venv/`, `.claude/`, `.omx/`, Gemini extension/cache directories, and Hermes learning files in addition to disposable caches.

When a maintenance run needs cleanup, inspect `git status --short --ignored` first, then remove only named generated caches that are safe for the current run (for example `.pytest_cache/` or `__pycache__/`). Preserve tracked `.forgeflow/tasks/*` fixtures and any untracked task/spec artifacts unless the current run created them and is intentionally deleting them.
