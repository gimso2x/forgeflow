# ForgeFlow Runtime Package Split Plan

## Overview

As of v0.10.x, `forgeflow_runtime/` contains approximately 50 modules in its root directory. While functional, this flat structure makes it difficult for new contributors to distinguish between the core workflow contract, optional extensions, and operator-facing tooling.

This document evaluates a potential package split and recommends a staged migration path.

## Current State Evaluation

- **Public API:** `forgeflow_runtime.__all__` correctly encapsulates the stable entry points.
- **Subpackages:** `evolution/`, `experiment/`, and `orchestra/` are already isolated.
- **Coupling:** High fan-in modules like `errors.py`, `executor.py`, and `artifact_validation.py` are imported across the entire codebase.
- **Recommendation:** **Docs-only layering is sufficient for v0.10.x.** A physical file move should be staged for v0.11.0 to avoid breaking existing imports in custom scripts or adapters that do not yet use the public API exclusively.

## Proposed Structure (v0.11.0+)

### 1. `forgeflow_runtime/core/`
The essential pipeline modules required for the artifact-first workflow contract.

- `orchestrator.py`
- `engine.py`
- `executor.py`
- `artifact_validation.py`
- `artifact_migrations.py`
- `schema_versions.py`
- `gate_evaluation.py`
- `gate_ralf.py`
- `enforcement_config.py`
- `policy_loader.py`
- `stage_transition.py`
- `workflow_engine.py`
- `route_execution.py`
- `operator_routing.py`
- `task_identity.py`
- `resume_validation.py`
- `errors.py`
- `execute_context.py`
- `adapter_registry.py`
- `generator.py`
- `complexity.py`

### 2. `forgeflow_runtime/extensions/`
Higher-order behaviors, heuristics, and optional guardrails.

- `evolution/` (subpackage)
- `experiment/` (subpackage)
- `orchestra/` (subpackage)
- `adversarial_review.py`
- `anti_rationalization.py`
- `constraint_checker.py`
- `context_freshness.py`
- `evidence_qa.py`
- `stuck_detector.py`
- `lightweight_mode.py`
- `verify_pipeline.py`
- `signal_pipeline.py`

### 3. `forgeflow_runtime/tools/`
Operator-facing diagnostics, monitoring, and generation helpers.

- `natural_language_plan.py`
- `profiling.py`
- `cost.py`
- `telemetry.py`
- `progress_tracker.py`
- `progressive_output.py`
- `output_compression.py`
- `stale_recovery.py`
- `profile_detector.py`
- `harness_profiles.py`
- `ears_parser.py`
- `worktree.py`
- `plan_ledger.py`
- `preset_resolver.py`
- `workflow_override.py`
- `coordination.py`
- `crystallization.py`
- `feedback_router.py`
- `versioning.py`

## Migration Path

### Stage 1: Compatibility Shims
Move files to their new subpackages but keep a compatibility shim in the root or update `forgeflow_runtime/__init__.py` to import from the new locations.

```python
# forgeflow_runtime/__init__.py example
from .core.orchestrator import init_task, clarify_task, ...
```

### Stage 2: Internal Refactor
Update all internal imports within `forgeflow_runtime/` to use the new subpackage paths.

### Stage 3: Validation
- Run `python3 scripts/validate_structure.py` to ensure no version drift.
- Run `python3 -m pytest tests/test_runtime_package_boundaries.py` to verify the new boundaries.
- Ensure `__all__` remains the single source of truth for public API users.

## Conclusion

The physical split provides better architectural signal but carries the risk of import churn. By following a staged approach and preserving the `__all__` boundary, we can deepen the package structure without breaking the ecosystem.
