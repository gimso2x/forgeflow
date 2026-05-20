# ForgeFlow Advisory Guidelines

ForgeFlow stays markdown-only and no-runtime. These guidelines are advisory checklists for `clarify`, `plan`, and `review`; they do not hard-block execution.

## Route Budget Guide

```yaml
budget:
  small: "Single localized change, usually 1-2 files, low rollback risk."
  medium: "Coordinated work across a few file groups; plan required."
  high: "Multi-component or risky work; separate spec and quality review."
  epic: "Milestone-scale work; roadmap and milestone review required."
```

## How to use

- `clarify`: record a `Budget Note` in `brief.md` when scope or risk is non-trivial.
- `plan`: align the `Execution Pattern` with the selected route.
- `review`: treat budget overruns as findings only when they changed risk, scope, or evidence quality.
- Operators may override the guide with explicit task constraints, but must record the reason in artifacts.

## Non-goals

- No token counter, quota runtime, or subprocess manager.
- No automatic skill injection engine.
- No vendor-specific configuration generator.
