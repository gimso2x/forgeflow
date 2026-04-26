# FF-MAINT-004: Add Script Thinness Guard

Priority: P1
Status: Landed in local review stack
Type: structure/contract validation
Primary area: `scripts/*.py`, `forgeflow_runtime/*`

## Problem

ForgeFlow's contract map says scripts should be thin command-line and validation entrypoints, while reusable behavior belongs in `forgeflow_runtime/`. This is the right rule, but right now it is mostly a convention.

As command surfaces grow, policy and runtime behavior can creep back into `scripts/`, especially around evolution commands and orchestrator CLI behavior.

## Goal

Add a small guard that makes script/runtime boundary drift visible during tests or structure validation.

## Non-goals

- Do not build a complex static analyzer.
- Do not forbid normal argparse/printing/exit-code logic.
- Do not move script behavior in the same commit unless the guard reveals one tiny obvious violation.
- Do not make brittle line-count policing the main rule.

## Proposed guard

Add a simple test or validation check that asserts key boundary expectations, for example:

- `docs/contract-map.md` names the script/runtime boundary.
- known CLI scripts import and call runtime modules for reusable behavior.
- high-risk policy commands remain backed by `forgeflow_runtime.evolution_*` modules.
- scripts do not become the canonical home for generated adapter, evolution, route, or artifact policy.

A light AST check is acceptable if it is simple and stable. Text assertions in `tests/test_validate_structure.py` may be enough for the first slice.

## Suggested implementation steps

1. Inspect current script entrypoints and runtime imports.
2. Pick one high-value, low-brittleness assertion.
3. Add the failing test first.
4. Update structure/docs/runtime import boundary only as needed.
5. Keep the check boring. If it feels clever, it is probably too clever.

## Acceptance criteria

- A regression test or validation check fails if the script/runtime boundary silently disappears.
- Scripts remain usable CLI wrappers.
- No major refactor is included.
- The guard is understandable to future maintainers.

## Suggested narrow validation

```bash
python -m pytest tests/test_validate_structure.py -q
python -m pytest tests/evolution tests/runtime -q
make validate
python -m pytest -q
git diff --check
git status --short
```

## Commit message

```text
test: guard script runtime boundary
```
