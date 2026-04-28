# Design Interface Model

`design-interface` is a helper artifact for shaping an implementation boundary before code changes start.

It is not a new ForgeFlow stage. That matters. A separate `/forgeflow:design` stage would be ceremony creep. The useful part from `mattpocock/skills` is smaller: force the agent to compare interface shapes before it starts writing code.

## Artifacts

Default task-local output:

```text
.forgeflow/tasks/<task-id>/contracts.md
```

Optional machine-checkable output, only when the task explicitly needs schema-backed interface design:

```text
.forgeflow/tasks/<task-id>/interface-spec.json
```

Repository sample:

```text
examples/artifacts/interface-spec.sample.json
schemas/interface-spec.schema.json
```

## Purpose

Use this helper when the next implementation changes a public boundary:

- CLI command or flags
- JSON artifact shape
- Markdown contract consumed by another skill
- Python module API
- plugin/MCP/tool interface
- HTTP endpoint
- compatibility-sensitive file layout

If no caller can observe the shape, skip it. Not every pebble needs an architect.

## Required decisions

The artifact requires:

1. caller list
2. public surface list
3. invariants
4. compatibility constraints
5. error behavior
6. testing surface
7. migration concerns
8. at least two materially different interface options
9. chosen option
10. contracts.md output section

The two-option rule is intentional. If there is only one option, the agent is probably just narrating the first idea it had.

## Source of truth

`interface-spec.json` is the optional machine-checkable design artifact. It is not mandatory for every interface decision.

`contracts.md` is the human-facing contract excerpt used by later plan/run/review work.

The helper must not fork truth away from `plan.json`. Plan steps should reference the interface spec, then implementation should satisfy it.

## Non-goals

- no canonical `/forgeflow:design` stage
- no free-floating design docs detached from a task
- no Figma-like UI ideation workflow
- no automatic publishing
- no replacement for `plan.json`

## Validation

A valid sample must pass:

```bash
python3 -m json.tool schemas/interface-spec.schema.json >/dev/null
python3 -m json.tool examples/artifacts/interface-spec.sample.json >/dev/null
python3 scripts/validate_sample_artifacts.py
```
