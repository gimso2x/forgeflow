# Runtime Module Activation Guide

ForgeFlow is an artifact-first workflow contract plus a lightweight enforcement runtime for Claude Code, Codex, and Gemini CLI. The runtime exists to keep the artifact contract executable: stage transitions, gates, evidence, reviews, routing, and operator diagnostics are checked by code instead of chat memory.

This package intentionally has several module layers. They are not all equal entrypoints.

## Layers

### Core contract modules

Use these through public entrypoints such as `execute_stage`, `advance_to_next_stage`, `run_route`, `status_summary`, and `load_runtime_policy`. They are active for normal ForgeFlow operation.

- `artifact_validation.py` — reads/writes artifacts and validates strict JSON schemas.
- `schema_versions.py`, `artifact_migrations.py` — schema version support and migration compatibility.
- `policy_loader.py`, `enforcement_config.py` — canonical workflow policy loading.
- `gate_evaluation.py` — required stage-gate checks before transitions.
- `gate_ralf.py` — repair loop when gate artifacts are missing or invalid.
- `verify_pipeline.py` — validates artifact/pipeline readiness before handoff or release.
- `complexity.py`, `operator_routing.py` — route selection (`small`, `medium`, `high`, `epic`).
- `orchestrator.py`, `orchestrator_execution.py`, `route_execution.py`, `stage_transition.py`, `workflow_engine.py` — stage lifecycle coordination.
- `engine.py`, `executor.py`, `generator.py`, `adapter_registry.py` — prompt generation and adapter dispatch.
- `plan_ledger.py`, `task_identity.py`, `resume_validation.py`, `run-state` helpers — durable task state.

Activation condition: always available; invoked by plugin slash skills, local CLI, or runtime entrypoints when a ForgeFlow task is active.

### Optional extensions

These modules add higher-order behavior for special situations. They should stay inactive unless the route, policy, or operator request needs them.

- `orchestra/` — multi-model consensus, debate, pipeline, and fastest-result strategies.
  - **Controlled by:** `policy/canonical/complexity-routing.yaml` → `orchestration` key.
  - **Activation:** Active when a multi-model environment is configured and the selected strategy calls for cross-agent orchestration.
  - **Note:** Inactive for a single Claude Code/Codex/Gemini run unless explicitly configured.
- `adversarial_review.py` — hostile/independent review pass for higher-risk changes.
  - **Controlled by:** `policy/canonical/workflow.yaml` → `review_order` or route-specific `traits` in `complexity-routing.yaml`.
  - **Activation:** Active for `high`/`epic` or security-sensitive review policy.
  - **Note:** Inactive for routine `small` changes unless operator policy opts in.
- `experiment/` — experiment loop, metrics, stopping policy, and circuit behavior.
  - **Controlled by:** `schemas/experiment.schema.json` backed tasks or explicit operator-invoked experiment runs.
  - **Activation:** Active for eval/experiment runs and optimization loops.
- `evolution/` — rule proposal, approval, audit, and promotion lifecycle.
  - **Controlled by:** `policy/canonical/evolution.yaml`.
  - **Activation:** Active when maintaining ForgeFlow rules or approved memory/policy evolution (e.g., via `scripts/forgeflow_evolution.py`).
- Intelligence helpers such as `anti_rationalization.py`, `constraint_checker.py`, `context_freshness.py`, `evidence_qa.py`, `stuck_detector.py`, `lightweight_mode.py`.
  - **Controlled by:** `RuntimePolicy.constraints` or route-specific `traits` in `complexity-routing.yaml`.
  - **Activation:** Active when the route/policy enables the corresponding guardrail (e.g., `high` route enabling `stuck_detector`).

### Operator tooling

These are human-facing diagnostics, generation helpers, or CLI-backed surfaces. They are not the workflow contract itself.

- `natural_language_plan.py` — converts brief issue text into schema-valid draft plans.
  - **Controlled by:** operator/script invocation; no canonical policy key currently enables it automatically.
  - **Activation:** Invoked by operator when drafting a plan from natural language.
- `profiling.py`, `cost.py`, `telemetry.py` — performance/cost/token reporting.
  - **Controlled by:** CLI/operator flags such as `--profile`/`--telemetry` and runtime calls that explicitly attach collectors; no default canonical policy key.
  - **Activation:** Active when route execution records or compares runtime profiles.
- `profile_detector.py`, `harness_profiles.py` — project/profile detection.
  - **Controlled by:** setup/doctor command invocation; no workflow policy key.
  - **Activation:** Invoked during `init`/`setup` or `doctor`-style diagnostics (`scripts/codex_plugin_doctor.py`).
- `progress_tracker.py`, `progressive_output.py`, `output_compression.py`, `signal_pipeline.py`, `stale_recovery.py`.
  - **Controlled by:** operator monitoring/recovery scripts and explicit runtime calls; no always-on policy key.
  - **Activation:** Script/Operator-invoked only (e.g., `scripts/forgeflow_monitor.py`). Used for status/monitoring or stale-run recovery.
- Scripts under `scripts/` such as `forgeflow_profile.py`, validators, smoke tests, visual/debug helpers.
  - **Controlled by:** human, CI, or release workflow invocation; not a task-route policy.
  - **Activation:** Script-invoked only. Active only when called by a human, CI, or release workflow.

## Public import rule

Downstream integrations should prefer `forgeflow_runtime.__all__` and the documented API in `docs/api.md`. Direct imports from unexported modules are allowed inside ForgeFlow tests and scripts, but external users should treat them as internal until promoted to the public API.

## Positioning decision

ForgeFlow is not merely prose policy. It is an artifact-first workflow contract plus a lightweight enforcement runtime. The docs/skills define how work should proceed; `forgeflow_runtime/` makes those rules executable across Claude Code, Codex, and Gemini CLI.
