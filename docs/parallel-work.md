# Parallel Work Safety

ForgeFlow supports multiple terminals and git worktrees, but only when task boundaries are explicit and artifacts remain the source of truth.

## Core contract

1. **One task, one workspace boundary** — every worker operates inside a single `.forgeflow/tasks/<task-id>/` directory and only edits the files listed in that task's `plan-ledger.tasks[].files`.
2. **Single writer for shared documents** — shared docs such as `README.md`, `INSTALL.md`, `CHANGELOG.md`, architecture docs, and release notes must have exactly one active writer task. Other tasks may read them but must not edit them until the writer task is done.
3. **Worktree or terminal isolation** — parallel implementation workers should use separate git worktrees or clearly separated terminal sessions. A worker must not reuse another task's dirty workspace.
4. **Machine-readable conflict boundary** — `plan-ledger.tasks[].parallel_safe` is the runtime signal. It may be `true` only when the task has no file overlap with other active tasks and does not touch a single-writer shared document.
5. **Merge order is serial** — even if implementation happens in parallel, merge/squash/finalize remains serialized through the owning task and its review evidence.

## Parallel-safe examples

- `frontend-worker` updates `src/components/Button.tsx` while `backend-worker` updates `api/users.py`.
- A docs writer updates `docs/guides/codex.md` while a runtime worker updates `forgeflow_runtime/operator_routing.py`, if no shared index/docs are touched.
- Multiple read-only review tasks inspect the same diff and write separate review artifacts.

## Serial-only examples

- Two workers both editing `README.md` or `INSTALL.md`.
- Release/version updates that touch manifests, changelog, and install docs.
- Schema changes that require synchronized updates across `schemas/`, runtime producers, fixtures, generated adapters, and contract tests.
- Any task whose `files` list overlaps with another active task.

## Operator checklist before spawning parallel workers

- Confirm each worker has a distinct `task_id` or distinct `plan-ledger.tasks[].id`.
- Confirm each worker's `files` list is disjoint.
- Mark shared docs as single-writer and assign them to one task.
- Prefer separate worktrees for mutating workers; use separate terminals only for read-only/review work or clearly disjoint file edits.
- Record conflict decisions in `decision-log.json`; do not rely on chat memory.

## Evidence requirement

A parallel task is not complete until its ledger entry has structured evidence refs for the relevant gates/reviews, for example:

```json
{
  "type": "gate",
  "target": "run-state.json#gate:validator",
  "relation": "validated_by",
  "label": "pytest"
}
```
