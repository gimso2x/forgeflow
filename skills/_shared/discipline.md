# Shared Discipline Rules

Common file-write and response discipline shared across ForgeFlow workflow skills.
Each skill links here and adds skill-specific rules inline.

## File write and output discipline (core)

- Default to **artifact-first mode**. Write artifacts under `.forgeflow/tasks/<task-id>/` unless the user explicitly asks for a dry run, exact-output response, or no-write simulation.
- If the task directory is missing, bootstrap or recover it first. Do not proceed to source edits while the workflow state lives nowhere.
- Write only under the current project workspace or the active task directory. Never write inside the plugin installation directory, marketplace cache, extension cache (including `.claude/plugins/cache`, `.codex/plugins`, `.cursor/plugins`, `~/.cursor/plugins/local`, `.gemini/extensions`, or `~/.gemini/extensions`), or `skills/<skill>/`.
- If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.
- When artifacts are mentioned without an explicit path, assume `.forgeflow/tasks/<task-id>/`, not chat-only fallback.

## User language and artifact readability (core)

- Detect the user's primary language from the current request and recent conversation. Write user-facing replies and Markdown artifact prose in that language.
- For Korean users, write explanatory prose in `brief.md`, `plan.md`, `implementation-notes.md`, `review-report.md`, `ship-summary.md`, and finish decision reports in natural Korean.
- Keep technical identifiers in English when they are part of the workflow contract: file paths, commands, code identifiers, artifact filenames, frontmatter keys, table keys, route labels (`small`, `medium`, `high`, `epic`), verdict enums (`approved`, `changes_requested`, `blocked`), and gate values (`PASS`, `FAIL`, `skip`, `n/a`).
- Prefer localized section titles with the canonical English label preserved in parentheses, such as `## 검증 계획 (Verification Plan)`, so artifacts stay readable to the user without losing ForgeFlow traceability.
- For long high/epic artifacts, put a short user-language summary near the top before detailed tables or checklists.

## Strict response constraints (core)

- When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.
- When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.
- For exact-count list prompts, output numbered lines only. No heading, preamble, fenced block, summary, or extra lines.
