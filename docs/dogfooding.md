# Dogfooding fixtures

Some `.forgeflow/tasks/*` directories in this repository are **intentionally tracked** as validation fixtures and workflow smoke examples. They demonstrate real artifact output from ForgeFlow development tasks (e.g. `forgeflow-context-efficiency`, `validate-skill-frontmatter`).

Normal consumer projects should keep `.forgeflow/` gitignored. This repo tracks selected task folders to:

- Exercise `make validate` eval file references
- Preserve evidence from contract changes
- Serve as reference implementations for artifact structure

Do not treat tracked task folders as runtime state for the ForgeFlow plugin itself.
