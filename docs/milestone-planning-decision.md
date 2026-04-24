# Milestone Planning Absorption Decision

## Decision

Adopt the `engineering-discipline` milestone-planning idea **partially now**, and defer full 5-reviewer ultraplan orchestration.

ForgeFlow should not copy the source repo's command as-is. The useful part is the planning pressure: large/high-risk work needs independent views of feasibility, architecture, risk, dependencies, and verification before execution starts.

## Source idea

`engineering-discipline/skills/milestone-planning/SKILL.md` decomposes multi-day tasks by running five independent reviewers:

1. Feasibility analyst
2. Architecture analyst
3. Risk analyst
4. Dependency analyst
5. Verification analyst

Then it synthesizes a milestone dependency DAG where every milestone has measurable success criteria.

## ForgeFlow fit

ForgeFlow already has stronger primitives than the source repo:

- canonical `large_high_risk` route
- `plan.json`
- `plan-ledger.json`
- checkpoint/session-state artifacts
- long-run model docs
- schema validation and adherence evals

So the right absorption is not another slash command. The right absorption is a stricter planning rule for large/high-risk plans.

## Adopt now

For `/forgeflow:plan` large/high-risk work, the plan should include milestone pressure from five angles before execution:

- feasibility risks
- architecture/interface boundaries
- dependency ordering
- regression and recovery risks
- verification strategy

This can be documented as required planning content without adding a new runtime stage yet.

## Defer

Do not implement parallel reviewer orchestration yet.

Reasons:

- It would require agent orchestration semantics outside current ForgeFlow schema.
- Prompt-only multi-agent orchestration is easy to fake and hard to validate.
- The immediate value is better milestone content, not another command.

## Revisit trigger

Build first-class reviewer orchestration only if at least one becomes true:

- `plan-ledger.json` grows explicit reviewer evidence fields.
- Long-run execution starts failing because milestone boundaries are weak.
- The Claude plugin needs a dedicated `/forgeflow:milestones` surface.
- We can test reviewer synthesis mechanically instead of trusting chat output.

## Current rule

Large/high-risk plans must not be a flat task list pretending to be a milestone plan. They need a dependency-aware milestone structure with measurable verification and explicit risk/dependency notes.
