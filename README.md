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
- `examples/artifacts/` — sample artifact fixtures
- `scripts/` — validation and generation utilities

## Quick start
```bash
make validate
make generate
make regen
```

## Current status
This repo is a **P0 seed**.
It already includes:
- design docs
- canonical policy files
- JSON schemas for core artifacts
- generated adapters for Claude / Codex / Cursor
- validation scripts
- sample artifact fixtures

It does **not** yet include a full runtime orchestrator.
That is deliberate.

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
- sample artifact validation

## Naming
The name is **ForgeFlow** because the point is to forge messy agent work into a flow with gates, evidence, and review.
Not because everything needs a dramatic fantasy backstory.
