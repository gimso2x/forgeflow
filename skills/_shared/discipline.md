# Shared Discipline Rules

Common file-write and response discipline shared across ForgeFlow workflow skills.
Each skill links here and adds skill-specific rules inline.

## File write and output discipline (core)

- Default to **artifact-first mode**. Write artifacts under `.forgeflow/tasks/<task-id>/` unless the user explicitly asks for a dry run, exact-output response, or no-write simulation.
- If the task directory is missing, bootstrap or recover it first. Do not proceed to source edits while the workflow state lives nowhere.
- Write only under the current project workspace or the active task directory. Never write inside the plugin installation directory, marketplace cache, extension cache (including `.claude/plugins/cache`, `.codex/plugins`, `.cursor/plugins`, `~/.cursor/plugins/local`, `.gemini/extensions`, or `~/.gemini/extensions`), or `skills/<skill>/`.
- If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.
- When artifacts are mentioned without an explicit path, assume `.forgeflow/tasks/<task-id>/`, not chat-only fallback.

## Strict response constraints (core)

- When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.
- When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.
- For exact-count list prompts, output numbered lines only. No heading, preamble, fenced block, summary, or extra lines.
