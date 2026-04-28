# Contract Design Model

ForgeFlow contract design is a support model for interface-heavy work. It helps the operator compare interface shapes before execution without adding another lifecycle stage.

## Artifact authority

`contracts.md remains the default source of truth` for human-readable interface, compatibility, and invariant constraints. Plan steps may link to those anchors through existing plan traceability fields.

`schemas/interface-spec.schema.json is an optional structured representation` for projects that need machine-readable interface options, selected decisions, and contract output metadata. The structured artifact is useful for validation and automation, but it does not outrank the markdown contract.

This model does not replace `/forgeflow:plan`. It feeds planning by clarifying boundaries, risks, verification surfaces, and migration expectations before work is decomposed.

There is no parallel design source of truth. If an interface decision matters, it must land in `contracts.md`, an approved plan artifact, or both.

## When to use it

Use contract design when a task touches a boundary that other code, adapters, users, or automation consume:

- CLI or plugin command behavior;
- schema and artifact compatibility;
- runtime module seams;
- adapter inputs or generated outputs;
- migration paths where old artifacts may still exist;
- cross-agent or cross-stage contracts.

Skip it when the change is obviously internal and already covered by existing tests and docs.

## Required reasoning

For non-trivial boundaries, compare at least two materially different interface options. Each option should name:

- affected callers;
- invariants preserved or changed;
- compatibility risks;
- testing surface;
- migration impact;
- why it was selected or rejected.

A good contract decision is boring: it narrows ambiguity, names the compatibility cost, and gives `/forgeflow:plan` enough evidence to produce schema-valid work without inventing new fields.

## Output shape

Default output is a `contracts.md` section with stable headings and anchors. Optional structured output may be written as `interface-spec.json` when automation needs it, but the JSON should point back to `contracts.md` as the target contract artifact.

Do not create a new slash command, approval gate, lifecycle state, persistence lane, or generated adapter surface for contract design unless a separate approved task explicitly changes the ForgeFlow lifecycle.
