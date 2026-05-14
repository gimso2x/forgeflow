# Refactor planning decision

Status: accepted

ForgeFlow handles refactors as a branch inside the existing `plan` stage, not as a new command, lifecycle state, or required artifact. Refactors are risky because they can accidentally change behavior while pretending to be structural work, so the plan must make preservation and rollback explicit.

## Entry criteria

Use refactor mode when the request is primarily one of these:

- behavior-preserving structural change across an existing public surface
- migration-sensitive internal reorganization
- test-sensitive decomposition work
- removal or replacement of implementation machinery while preserving user-visible behavior

Do not use refactor mode for ordinary feature work or tiny local edits that already fit the normal plan contract.

## Representation

Refactor-specific requirements must map onto existing plan artifacts:

- preserved public behavior: `requirements` in the sibling plan note, `steps[].objective`, `steps[].fulfills`, and `verify_plan`
- explicit non-goals: sibling plan note section named `Non-goals`
- migration boundary: sibling plan note section named `Migration boundary`, or `contracts.interfaces` / `contracts.invariants` when the boundary is cross-module
- rollback or escape hatch: `steps[].rollback_note`, with an explicit not-applicable note allowed only for contained internal refactors
- tiny always-green implementation steps: `steps[]` decomposition and DAG dependencies
- regression verification strategy: `steps[].verification` and top-level `verify_plan`
- existing test coverage note: sibling plan note section named `Existing coverage`

`schemas/plan.schema.json` is unchanged. If a future refactor needs data that cannot be represented by these fields or named markdown sections, stop and create a schema/decision note first.

## Architecture Glossary

Use these terms to identify deepening opportunities during refactoring and planning:

- **Module**: anything with an interface and an implementation (function, class, package, slice).
- **Interface**: everything a caller must know to use the module: types, invariants, error modes, ordering, config.
- **Implementation**: the code inside.
- **Depth**: leverage at the interface. **Deep** = lot of behavior behind a small interface. **Shallow** = interface nearly as complex as the implementation.
- **Seam**: where an interface lives; a place behavior can be altered without editing in place.
- **Adapter**: a concrete thing satisfying an interface at a seam.
- **Leverage**: what callers get from depth.
- **Locality**: what maintainers get from depth: change, bugs, and knowledge concentrated in one place.
- **Deletion test**: imagine deleting the module. If complexity vanishes, it was a pass-through (shallow). If complexity reappears across callers, it was earning its keep (deep).

## Policy

A refactor plan should prefer public-behavior verification over implementation-detail assertions. Tests may cover internals only when the affected surface is genuinely internal and the plan says so.

The refactor branch strengthens `/forgeflow:plan`; it does not create `/forgeflow:refactor-plan`, a separate approval gate, or a new required planning artifact.
