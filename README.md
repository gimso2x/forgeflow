# ForgeFlow

ForgeFlow is an artifact-first delivery harness for AI coding agents.

It is **not** an agent OS and it is **not** a prompt zoo.
It is a repo seed for running work through explicit stages, artifacts, gates, and independent review.

## What ForgeFlow does
- models work as a stage machine
- keeps state in artifacts instead of chat memory
- separates worker and reviewer roles to reduce self-approval
- isolates runtime differences behind generated adapters
- keeps small tasks light and high-risk tasks strict

## Core workflow
1. `clarify`
2. `plan`
3. `execute`
4. `spec-review`
5. `quality-review`
6. `finalize`
7. `long-run`

## Complexity routing
- **small** → `clarify -> execute -> quality-review -> finalize`
- **medium** → `clarify -> plan -> execute -> quality-review -> finalize`
- **large/high-risk** → `clarify -> plan -> execute -> spec-review -> quality-review -> finalize -> long-run`

## Why this exists
Most agent repos do at least one of these badly:
- treat chat history as state
- let the implementer implicitly approve their own work
- copy host-specific rules everywhere
- grow into a weird little religion

ForgeFlow tries not to do that.

## Repo map
- `docs/` — human-readable design docs
- `policy/canonical/` — workflow semantics, gates, review order, routing
- `schemas/` — artifact contracts
- `prompts/canonical/` — canonical role prompts
- `adapters/targets/` — target manifests
- `adapters/generated/` — generated runtime surfaces
- `runtime/` — scaffold-level runtime surfaces for orchestrator, ledger, gates, recovery
- `forgeflow_runtime/` — executable Python runtime implementation used by the local CLI
- `memory/` — inspectable local memory scaffold for reusable patterns and decisions
- `examples/artifacts/` — sample artifact fixtures
- `scripts/` — validation and generation utilities

## Quick start
```bash
make validate
make adherence-evals
make generate
make regen
make runtime-sample
```

## Runtime sample
```bash
python3 scripts/run_orchestrator.py run --task-dir examples/runtime-fixtures/small-doc-task --route small
```

이 명령은 local artifact 디렉터리를 기준으로 `small` route를 끝까지 실행하고 `run-state.json`, `decision-log.json`을 쓴다.

## Current status
This repo is a **P0 seed**.
It already includes:
- design docs
- canonical policy files
- JSON schemas for core artifacts
- generated adapters for Claude / Codex / Cursor
- target-specific installation guidance captured in manifest metadata and rendered into generated adapters
- validation scripts
- sample artifact fixtures

It now includes a **minimal local runtime orchestrator CLI** for artifact-directory execution plus the explicit `runtime/` and `memory/` scaffold surfaces promised by the design docs.
The local runtime can also resume from a validated `run-state.json` checkpoint instead of replaying already-completed stages.
It still does **not** include provider-specific integrations or a full hosted runtime.
That boundary is deliberate.

## Design lineage
ForgeFlow borrows its best bones from four places:
- `engineering-discipline` — workflow skeleton, complexity routing, worker/validator split
- `hoyeon` — artifact contracts, schema discipline, bounded recovery
- `gstack` — canonical policy → generated adapters
- `superpowers` — adversarial review, spec-review before quality-review

## Validation
```bash
make validate
```

This runs:
- structure validation
- policy validation
- generated adapter validation
- JSON Schema sample artifact validation for positive and negative fixtures
- executable adherence evals across small/medium/large and negative runtime fixtures

## Naming
The name is **ForgeFlow** because the point is to forge messy agent work into a flow with gates, evidence, and review.
Not because everything needs a dramatic fantasy backstory.
