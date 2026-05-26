# ForgeFlow Advisory Guidelines

> **Last updated**: 2026-05-21 | **Status**: advisory only — does not hard-block execution.

ForgeFlow stays markdown-only and no-runtime. These guidelines are advisory checklists for `clarify`, `plan`, and `review`; they do not hard-block execution.

## Route Budget Guide

```yaml
budget:
  small: "Single localized change, usually 1-2 files, low rollback risk."
    # score < 10
  medium: "Coordinated work across a few file groups; plan required."
    # score 10–24.9
  high: "Multi-component or risky work; separate spec and quality review."
    # score 25–49.9
  epic: "Milestone-scale work; plan with epic decomposition, roadmap and milestone review required."
    # score ≥ 50
```

### Score Ranges

| Route | Score Range |
|-------|------------|
| small | < 10 |
| medium | 10 – 24.9 |
| high | 25 – 49.9 |
| epic | ≥ 50 |

### Medium Sub-bands

`mid_threshold = 17.0`

- **medium-light**: score 10.0 – 16.9 → lighter coordination, plan may omit full step-by-step if scope is straightforward.
- **medium-full**: score 17.0 – 24.9 → full plan with step-by-step breakdown required.

### WHERE Calibration

Ambition and situational context (e.g. hotfix urgency, learning-mode exploration) may shift the effective route up or down one band. Record the calibration reason in the `Budget Note` inside `brief.md`. For full calibration criteria, see `skills/clarify/SKILL.md`.

## How to use

- `clarify`: record a `Budget Note` in `brief.md` when scope or risk is non-trivial.
- `plan`: align the `Execution Pattern` with the selected route.
- `review`: treat budget overruns as findings only when they changed risk, scope, or evidence quality.
- Operators may override the guide with explicit task constraints, but must record the reason in artifacts.

## Non-goals

- No token counter, quota runtime, or subprocess manager.
- No automatic skill injection engine.
- No vendor-specific configuration generator.
