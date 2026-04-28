---
name: design-interface
description: Define a task-local interface contract before implementation when a change touches public JSON, CLI, file, module, plugin, MCP, HTTP, or skill boundaries. Absorbs mattpocock/skills-style interface design as an optional ForgeFlow helper, not a new stage.
---

# design-interface

## Purpose

Force interface decisions before code changes when a task changes an observable boundary.

This skill absorbs the useful part of `mattpocock/skills`: design the interface first, compare real alternatives, then write the chosen contract where later work can verify it.

This optional support skill feeds `contracts.md` and plan artifacts; it creates no separate approval gate, lifecycle state, or persistence lane.

No new canonical `/forgeflow:design` stage. This optional support skill is not a new `/forgeflow:design` stage. Use it only when the boundary matters.

## Trigger

Use when a task touches any of these:

- CLI command, argument, or output shape
- JSON artifact or schema
- markdown contract consumed by another skill
- Python/public module API
- plugin, MCP, tool, or adapter interface
- HTTP endpoint or webhook payload
- compatibility-sensitive file layout

Skip when the change is purely internal and no caller observes the shape.

## Input Artifacts

Read, in this order:

1. `.forgeflow/tasks/<task-id>/brief.json` or equivalent task brief
2. `.forgeflow/tasks/<task-id>/plan.json` if it exists
3. existing `.forgeflow/tasks/<task-id>/contracts.md` if it exists
4. relevant existing schema, tests, docs, and call sites
5. `schemas/interface-spec.schema.json`

## Output Artifacts

Default output is a `contracts.md` section in the task-local contract output:

1. `.forgeflow/tasks/<task-id>/contracts.md`

`interface-spec.json` is optional. Write the machine-checkable output only when the task explicitly needs schema-backed interface design, adapter automation, or durable cross-task traceability:

2. `.forgeflow/tasks/<task-id>/interface-spec.json`

Repository-level contract examples live at:

- `schemas/interface-spec.schema.json`
- `examples/artifacts/interface-spec.sample.json`
- `docs/design-interface-model.md`

## Execution

1. Identify callers.
   - List every known consumer: users, CLI adapters, skills, tests, modules, external callers.
   - If no caller exists, stop and say the helper is unnecessary.

2. Identify the public surface.
   - Name the file/API/command/schema/section.
   - Classify it as `cli`, `file`, `json`, `markdown`, `python`, `http`, `mcp`, or `plugin`.

3. Write invariants.
   - These are things implementation must not violate.
   - Prefer observable statements over vibes.

4. Write compatibility constraints.
   - Mark whether the change is new, compatible extension, breaking change, or internal-only.
   - Default to compatible extension unless the task explicitly accepts breakage.

5. Define error behavior.
   - Missing input, malformed input, unsupported option, partial migration, and empty output should have stated behavior.

6. Define testing surface.
   - Name the test type or exact test file expected to verify the interface.

7. Compare at least two materially different interface options.
   - This is mandatory.
   - Each option must name callers, invariants, compatibility, testing surface, and migration impact.
   - If both options are the same thing with different adjectives, that is fake design. Reject it.

8. Choose one option.
   - Explain why.
   - Record rejected alternatives with reasons.

9. Decide whether JSON is justified.
   - Default to `contracts.md` only.
   - Emit `interface-spec.json` when the boundary needs machine validation, publication/adapter automation, or durable cross-task traceability.
   - If emitted, it must validate against `schemas/interface-spec.schema.json`.

10. Update `contracts.md`.
    - Add or replace only the relevant section.
    - Do not create a parallel design source of truth.
    - The contracts section must match the chosen option.

## Constraints

- No new canonical `/forgeflow:design` stage.
- Do not create a parallel design source of truth.
- Do not publish GitHub issues or PRs from this skill.
- Do not implement the feature inside this skill.
- Do not skip source discovery; inspect existing call sites first.
- Keep task-local output under `.forgeflow/tasks/<task-id>/`.
- If the plan already defines a compatible interface, refine it instead of inventing a second one.

## Exit Condition

Done when:

1. `contracts.md` contains the chosen interface contract.
2. if `interface-spec.json` is emitted, it validates against `schemas/interface-spec.schema.json`.
3. the contract output names callers, public surfaces, invariants, errors, tests, migration concerns, and at least two options.
4. later plan/run/review work can reference the interface without guessing.

## Failure Modes

- one-option design theater
- ungrounded interface invented without checking callers
- contracts.md says one thing and JSON says another
- helper becomes an accidental stage
- public API is changed without migration notes
