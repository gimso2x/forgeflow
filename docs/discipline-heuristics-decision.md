# Discipline Heuristics Absorption Note

## Decision

Fold `engineering-discipline`'s `karpathy` and `rob-pike` ideas into ForgeFlow quality review as checklist language. Do **not** add separate `/karpathy` or `/rob-pike` commands.

## Why

The useful behaviors are small and durable:

- make the smallest safe change
- stay inside requested scope
- read existing patterns before inventing new ones
- verify assumptions against files, types, APIs, and tests
- measure before performance optimization
- re-measure after optimization

Those belong inside quality review. A separate command would add ceremony and command sprawl.

## Applied surface

`skills/review/SKILL.md` now asks quality reviewers to check:

1. smallest safe change
2. existing pattern alignment
3. verified assumptions
4. measured performance changes

## Explicitly not copied

- Source repo skill names as public ForgeFlow commands
- Full philosophy text
- Optimization workflow as a separate stage

## Revisit trigger

Add a dedicated performance-review surface only if ForgeFlow starts producing performance-sensitive plans where measurement evidence needs schema support.
