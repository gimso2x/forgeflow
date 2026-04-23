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
python3 scripts/run_orchestrator.py execute --task-dir examples/runtime-fixtures/small-doc-task --route small --adapter codex
python3 scripts/run_orchestrator.py advance --task-dir examples/runtime-fixtures/small-doc-task --route small --current-stage clarify
python3 scripts/run_orchestrator.py advance --task-dir examples/runtime-fixtures/small-doc-task --route small --current-stage clarify --execute --adapter cursor
python3 scripts/run_orchestrator.py retry --task-dir examples/runtime-fixtures/small-doc-task --stage execute --max-retries 2
python3 scripts/run_orchestrator.py step-back --task-dir examples/runtime-fixtures/small-doc-task --route small --current-stage quality-review
python3 scripts/run_orchestrator.py escalate --task-dir examples/runtime-fixtures/small-doc-task --from-route small
```

이 CLI는 local artifact 디렉터리를 기준으로 route 실행과 recovery helper를 노출한다. `run`은 artifact/gate 기준으로 route 상태를 진행하는 orchestration 명령이고, `execute`는 현재 stage를 어댑터로 실행한다. `advance --execute`는 다음 stage로 넘긴 뒤 바로 실행까지 붙이되, 실행이 실패하면 stage pointer를 커밋하지 않는다. medium/large route에서는 `advance`/`run` 모두 `plan-ledger.json`이 있어야 하고, `step-back`은 되감는 stage에 해당하는 review approval/evidence만 지운다. 정책 위반이나 잘못된 route가 들어오면 traceback 대신 `ERROR:` 형식의 명시적 runtime 오류를 반환한다.

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
The local runtime resumes from validated checkpoints, using `run-state.json` for stage position and `plan-ledger.json` as the gate/retry/task-progress truth source on medium/large routes.
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
