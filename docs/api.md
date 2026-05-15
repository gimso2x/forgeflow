# Runtime API & Integration Boundary

ForgeFlow is an artifact-first workflow contract plus a lightweight enforcement runtime for Claude Code, Codex, and Gemini CLI. `forgeflow_runtime/` provides the executable layer for this contract. While the library contains many submodules, **not all of them are intended for direct external use**. For the module layer/activation map, see [runtime-modules.md](runtime-modules.md). For the future package split strategy, see [runtime-package-split-plan.md](runtime-package-split-plan.md).

This document outlines the public API boundary for downstream integrators and plugin developers.

## Public API (`forgeflow_runtime.__all__`)

The root `__init__.py` explicitly defines the stable public API via `__all__`. If a function, class, or type is exported here, it is safe to integrate into your custom CLI or pipeline.

### Core Entrypoints

These are the primary functions for manipulating a task's state and moving it through the ForgeFlow stages.

- `init_task`: Bootstrap a new task workspace.
- `start_task`: Fallback entry to initialize artifacts.
- `clarify_task`: Run the clarify stage.
- `execute_stage`: Run a single, specific stage (e.g., plan, execute, review).
- `advance_to_next_stage`: Safely transition from the current stage to the next.
- `retry_stage`: Attempt to re-run the current stage.
- `step_back`: Rewind to a previous stage.
- `run_route`: Run an entire route (small, medium, high) end-to-end.
- `status_summary`: Inspect the current task's state without mutating it.
- `resume_task`: Reload task state from persistence.

### Extensibility & Policy

- `load_runtime_policy`: Load the project's `RuntimePolicy`.
- `dispatch`: The lowest-level adapter dispatch method (sends prompts to Claude/Codex/Gemini).
- `list_adapters`: Discover available executor adapters.
- `generate_prompt`: Core template rendering logic.
- `RuntimeViolation`: The canonical exception for rule or gate violations.
- `GenerationError`, `ExecutorError`: Errors raised during prompt generation or execution.

### Profiling

- `PipelineProfile`, `StageProfile`, `ProfilingCollector`, `compare_profiles`, `detect_bottlenecks`, `format_comparison`, `format_summary`.

## Internal / Private API

Any module not explicitly exported in `forgeflow_runtime.__init__.py` should be considered an **internal implementation detail**. 

Specifically, you should **avoid directly importing from**:
- `gate_ralf.py`, `gate_evaluation.py` (Gate enforcement logic)
- `cost.py`, `telemetry.py` (Internal tracking)
- `stuck_detector.py`, `anti_rationalization.py`, `constraint_checker.py` (Intelligence and heuristics)
- `orchestra/*` (Multi-model coordination internals)
- `evolution/*` (Rule lifecycle internals)

If you need to trigger multi-model orchestration or enforce a gate, do so by invoking the corresponding public core entrypoints (like `execute_stage` or `advance_to_next_stage`), which will automatically invoke the internal machinery according to the loaded `RuntimePolicy`.