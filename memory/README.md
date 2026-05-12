# Inspectable local memory

`memory/` is ForgeFlow's project-local, inspectable memory layer.

It is not hidden model memory, chat history, cache, or disposable runtime state. It is a version-controlled project artifact for durable learnings that should survive across agent runs and remain reviewable in Git.

## Contents

- `patterns/` — reusable workflow patterns worth carrying forward
- `decisions/` — durable project-level operating decisions
- `learnings.jsonl` — optional x-learn output containing typed, de-duplicated learnings from completed task artifacts
- `index/` — optional derived search index for local retrieval; regenerate it when possible instead of treating it as source of truth

## Ownership

Maintainers own the content and review it like documentation. Agents may propose entries after completed work, but entries should explain the evidence behind the learning instead of dumping session chatter.

## Retention and Git policy

Commit small, curated memory files that describe stable patterns, decisions, and learnings. Do not commit secrets, personal chat transcripts, temporary scratch files, huge generated indexes, or per-run logs.

If a file can be regenerated from committed artifacts, prefer not to treat it as canonical. The source of truth is the reviewed text/JSONL in this directory plus the task artifacts that justify it.

P0 keeps this layer intentionally simple and local so memory remains reviewable and debuggable.
