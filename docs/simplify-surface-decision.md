# Simplify Surface Decision

## Decision

Do **not** add a first-class `/forgeflow:simplify` command now.

Absorb the useful checklist ideas into existing surfaces:

- `skills/review/SKILL.md` covers independent quality review.
- Behavior-preserving cleanup of generated code belongs in the approved plan or a follow-up implementation step.
- Functional QA belongs in the core `review` flow and verification evidence.

A separate simplify command would overlap all three and increase operator ambiguity.

## Source idea

`engineering-discipline/skills/simplify/SKILL.md` reviews changed code through three independent lenses:

1. Code reuse
2. Code quality
3. Efficiency

It requires `git diff` first, limits scope to changed files, and fixes actionable findings directly.

## What to absorb

Keep the changed-code-only rule and the three review lenses as checklist language:

- reuse existing utilities/helpers instead of duplicating new code
- remove unnecessary complexity and abstraction leaks
- flag obvious inefficient work without premature optimization
- never review or refactor untouched code "while here"

## What not to copy

- The parallel 3-agent orchestration requirement
- A new public slash command
- The requirement that review always fixes code directly

ForgeFlow review should remain a gate. Cleanup belongs in the approved plan or a follow-up implementation step.

## Revisit trigger

Create a first-class simplify surface only if users repeatedly need an explicit post-run cleanup stage that is distinct from quality review.
