# forgeflow_runtime Package Split Plan

## Decision

Keep the current flat `forgeflow_runtime/` layout for v0.11.x and document the logical core/extensions/tools boundaries instead of moving files immediately.

Reason: the public API is exported from `forgeflow_runtime.__all__`, while tests, scripts, plugin adapters, and generated prompts still import many internal modules directly. A broad package move would create high compatibility risk for little runtime benefit unless it is staged with shims.

## Current public API surface

The external import contract is `forgeflow_runtime.__all__`:

- Execution/adapter: `execute_stage`, `dispatch`, `list_adapters`, `RunTaskRequest`, `RunTaskResult`, `ExecutorError`
- Prompt generation: `generate_prompt`, `PromptContext`, `GeneratedPrompt`, `GenerationError`
- Runtime orchestration: `RuntimePolicy`, `RuntimeViolation`, `advance_to_next_stage`, `clarify_task`, `escalate_route`, `init_task`, `load_runtime_policy`, `resume_task`, `retry_stage`, `run_route`, `start_task`, `status_summary`, `step_back`
- Profiling: `PipelineProfile`, `ProfilingCollector`, `StageProfile`, `compare_profiles`, `detect_bottlenecks`, `format_comparison`, `format_summary`

Any package split must preserve those imports from the top-level package.

## Logical target layout

If a physical split is later approved, use this staged shape:

```text
forgeflow_runtime/
  __init__.py              # top-level compatibility exports stay here
  core/
    artifact_validation.py
    schema_versions.py
    artifact_migrations.py
    policy_loader.py
    enforcement_config.py
    gate_evaluation.py
    gate_ralf.py
    verify_pipeline.py
    complexity.py
    operator_routing.py
    orchestrator.py
    orchestrator_execution.py
    route_execution.py
    stage_transition.py
    workflow_engine.py
    engine.py
    executor.py
    generator.py
    adapter_registry.py
    plan_ledger.py
    task_identity.py
    resume_validation.py
  extensions/
    orchestra/
    adversarial_review.py
    experiment/
    evolution/
    anti_rationalization.py
    constraint_checker.py
    context_freshness.py
    evidence_qa.py
    stuck_detector.py
    lightweight_mode.py
  tools/
    natural_language_plan.py
    profiling.py
    cost.py
    telemetry.py
    profile_detector.py
    harness_profiles.py
    progress_tracker.py
    progressive_output.py
    output_compression.py
    signal_pipeline.py
    stale_recovery.py
```

## Compatibility shim requirement

Do not move a module without leaving a same-name shim at the old path for at least one minor release:

```python
# forgeflow_runtime/artifact_validation.py
from .core.artifact_validation import *  # noqa: F401,F403
```

Shims are required because tests, scripts, docs examples, and downstream adapters may import old paths directly.

## Migration stages

### Stage 0 — current v0.11.x

- Keep files flat.
- Maintain `docs/runtime-modules.md` and `docs/api.md` as the source of truth for boundaries.
- Add tests that discourage new public imports outside `__all__` unless intentionally documented.

### Stage 1 — low-risk tools move

Move operator-only modules first, with shims:

- `natural_language_plan.py`
- `profiling.py`
- `cost.py`
- `telemetry.py`
- `profile_detector.py`
- `harness_profiles.py`
- progress/output/monitoring helpers

Validation:

```bash
python3 scripts/validate_structure.py
python3 scripts/validate_sample_artifacts.py
python3 -m pytest -q tests/test_runtime_package_boundaries.py tests/test_validate_structure.py
```

### Stage 2 — optional extensions move

Move optional modules after tool shims are stable:

- `orchestra/`
- `adversarial_review.py`
- `experiment/`
- `evolution/`
- intelligence helpers

Validation adds route/review tests:

```bash
python3 -m pytest -q tests/test_runtime_package_boundaries.py tests/test_plugin_smoke_ci_contract.py tests/test_ship_finish_contract.py
```

### Stage 3 — core move, only if needed

Move core contract modules last. Keep top-level `__all__` unchanged and keep old-path shims.

Validation should include the full targeted runtime suite plus plugin smoke contracts:

```bash
python3 -m pytest -q
make validate-structure
```

## Recommendation

For v0.11.x, prefer docs/API boundaries over physical package split. Revisit the physical split only when:

- direct internal imports are audited and reduced;
- compatibility shims are tested;
- plugin smoke tests cover Claude Code, Codex, and Gemini surfaces;
- release notes can call out the old-path shim window.
