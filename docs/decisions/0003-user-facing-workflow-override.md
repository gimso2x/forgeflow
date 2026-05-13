# 0003. User-facing workflow override boundary

Date: 2026-05-13
Status: accepted

## Context

Phase 3 added `forgeflow_runtime.workflow_engine` and a `RuntimePolicy` → `WorkflowDefinition` bridge. The runtime can now resolve routes and roles through the workflow model while still using the canonical policy files as the source of truth.

The tempting next step is to expose `.forgeflow/workflow.yaml` directly to users. That is useful, but dangerous if it silently replaces canonical gates, stage requirements, evidence references, or route semantics. ForgeFlow's value is not “arbitrary YAML goes brrr”; it is artifact-first execution with review and gate contracts that stay inspectable.

## Decision

User-facing workflow override will be introduced as a constrained overlay, not as a replacement policy stack.

1. Canonical policy remains the source of truth for gates, required artifacts, review order, route names, and evidence contracts.
2. `.forgeflow/workflow.yaml` may override route step ordering and step role/lens metadata only inside known stages/routes unless explicitly marked experimental.
3. Runtime must load the canonical `RuntimePolicy` first, derive its canonical `WorkflowDefinition`, then apply and validate the project override against that canonical workflow.
4. Any conflict with canonical gates or required entry artifacts is a hard failure, not a warning.
5. The first product surface should be validation-only before execution uses the override.

## Adopted

- Project-local file path: `.forgeflow/workflow.yaml`.
- JSON support may come for tests or machine generation, but YAML is the user-facing default.
- Override semantics are “overlay + validate,” not “replace.”
- Validation command comes before runtime execution integration.

## Adapted

- `load_workflow(path)` remains a low-level parser for full workflow definitions.
- Phase 4 should add a separate overlay loader/resolver instead of changing `load_workflow()` into a magical canonical-aware function.
- `workflow_from_runtime_policy(policy)` remains the canonical bridge and should be the base for override validation.

## Rejected

- No silent precedence of `.forgeflow/workflow.yaml` over canonical policy.
- No user-defined new gates in Phase 4.
- No user-defined new required artifacts in Phase 4.
- No unknown stage IDs in normal mode.
- No automatic execution with override until validation-only behavior has tests and docs.

## Phase 4 implementation plan

### Task 1: Add overlay contract tests

Files:
- Create: `tests/runtime/test_workflow_override.py`

Test behaviors:
- Missing `.forgeflow/workflow.yaml` returns canonical workflow unchanged.
- A valid override can reorder known route stages when every referenced stage exists in canonical workflow.
- A valid override can change `role` metadata for a known step.
- Override that removes a canonical gate from a gated step fails.
- Override that changes `required_for_entry` for a canonical step fails.
- Override that references an unknown step fails.
- Override that references an unknown route fails.

### Task 2: Add overlay resolver

Files:
- Create: `forgeflow_runtime/workflow_override.py`

Suggested API:

```python
def resolve_project_workflow(
    root: Path,
    policy: RuntimePolicy,
    *,
    override_path: Path | None = None,
) -> WorkflowDefinition:
    """Return canonical workflow with a validated project overlay applied."""
```

Rules:
- Default path: `root / ".forgeflow" / "workflow.yaml"`.
- If no override exists, return `workflow_from_runtime_policy(policy)`.
- Parse override as a partial mapping, not necessarily a full workflow definition.
- Allow only known route IDs and known step IDs.
- Preserve canonical `gate` and `required_for_entry` values.
- Raise `RuntimeViolation` on conflict.

### Task 3: Add validation CLI surface

Files:
- Modify the current CLI entrypoint module after locating its parser.
- Update: `docs/reference/cli.md`.

Command:

```bash
forgeflow validate-workflow [--root <path>] [--workflow <path>]
```

Expected behavior:
- Exit `0` and print resolved route/step summary when override is valid or absent.
- Exit non-zero with a clear `RuntimeViolation` message when invalid.
- Do not execute stages.
- Do not mutate task artifacts.

### Task 4: Wire execution only after validation-only command passes

Files:
- `forgeflow_runtime/orchestrator.py`
- stage transition / operator routing call sites as needed

Rule:
- Execution may use the project workflow only through the same resolver tested by `validate-workflow`.
- If the resolver fails, task execution fails before stage dispatch.

### Task 5: Regenerate docs/adapters and verify

Commands:

```bash
source .venv/bin/activate
python scripts/generate_adapters.py
pytest tests/runtime/test_workflow_override.py -q
pytest tests/runtime/test_workflow_engine.py tests/runtime/test_stage_transition.py tests/runtime/test_operator_routing.py tests/runtime/test_orchestrator_lifecycle.py -q
pytest -q
```

## Consequences

- Phase 4 stays safe: users can experiment with route overlays without punching holes through gates.
- Canonical policy and project overrides have a clear hierarchy.
- The runtime avoids a second source of truth.
- Later phases can explicitly add experimental extension points for new stages/gates if there is a real need.

## Validation

This decision is documentation-only. Validate by:

```bash
python scripts/validate_structure.py
pytest tests/runtime/test_workflow_engine.py tests/runtime/test_stage_transition.py tests/runtime/test_operator_routing.py -q
```
