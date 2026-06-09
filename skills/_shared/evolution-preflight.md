# Evolution Rule Loading Protocol

Shared protocol for loading evolution rules during clarify, plan, execute, and ship stages.

## Paths

- **Project active rules**: `<storage-root>/evolution/active/*.md` (resolved via `forgeflow_storage.py`)
- **Global advisory rules**: `~/.forgeflow/evolution/active/*.md`

## Loading procedure

1. Resolve `<storage-root>` via `forgeflow_storage.py` (or use the already-resolved path).
2. Load project active rules from `<storage-root>/evolution/active/*.md` if the directory exists. Do **not** create this directory if it does not exist. Read-only check.
3. Load global advisory rules from `~/.forgeflow/evolution/active/*.md` if available.
4. Match rules by their `Trigger` and `Application Stage` fields against the current stage.
5. Record matching rules in the relevant artifact's `Applied Evolution Rules` section.

## Enforcement levels

- **Project active rules**: Required constraints for this repository. Must be followed.
- **Global advisory rules**: Advisory only — they may guide decisions, but they must not block or force hard enforcement.

## Conflict handling

If a project active rule conflicts with the user request, surface it as a blocker question with a recommended resolution. Do not silently override either the rule or the request.
