# Gemini CLI tool notes

Gemini reads ForgeFlow as extension context through the repo-root `GEMINI.md`.

## Non-interactive CLI

- Use `gemini --prompt` or `gemini -p` for headless prompts.
- Use `gemini --yolo` or `gemini -y` only when the task explicitly allows auto-approval.
- Validate extension packaging with `gemini extensions validate .` from the ForgeFlow repo root.

## Context includes

The repo-root `GEMINI.md` is intentionally a thin bootstrap. It should include:

- the generated Gemini adapter context
- the ForgeFlow skill index
- `forgeflow-discipline/SKILL.md`
- `forgeflow-discipline/references/gemini-tools.md`
- the active ForgeFlow workflow skills

Do not replace the generated adapter include with duplicated instructions; regenerate adapter files through the repo scripts when adapter content changes.
