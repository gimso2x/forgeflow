# ForgeFlow Runtime Architecture

## Overview

ForgeFlow is an artifact-first delivery harness for AI coding agents. The runtime is a zero-dependency Python library (`forgeflow_runtime/`) that provides staged workflows, gate enforcement, evidence trails, and multi-agent orchestration.

- **84 Python files** across 4 domains
- **stdlib only** — no pip dependencies
- **1414 tests** — full coverage of contracts and runtime

## Module Map

```
forgeflow_runtime/
├── Core Pipeline           # Stage execution, routing, artifact I/O
│   ├── orchestrator.py     # Central coordinator — stage transitions, gates, checkpoints
│   ├── engine.py           # Stage execution glue, parallel workers
│   ├── executor.py         # Adapter dispatch (Claude/Codex/other agents)
│   ├── generator.py        # Prompt generation from templates
│   ├── stage_transition.py # Stage-to-stage advancement logic
│   ├── route_execution.py  # End-to-end route runner
│   └── operator_routing.py # Route selection: small / medium / high
│
├── Artifact Layer          # JSON schema, validation, migration
│   ├── artifact_validation.py  # Schema loading, validation, read/write (3 dependents)
│   ├── artifact_migrations.py  # Version migration (0.1→0.2+)
│   └── schema_versions.py     # Version constants and assertions
│
├── Gate & Quality          # Stage gates, evidence, review
│   ├── gate_evaluation.py  # Pre-stage gate enforcement
│   ├── gate_ralf.py        # RALF self-healing loop for gate recovery
│   ├── evidence_qa.py      # Evidence quality scoring
│   ├── adversarial_review.py   # Adversarial review patterns
│   ├── anti_rationalization.py # Anti-rationalization checks
│   └── verify_pipeline.py  # Output verification pipeline
│
├── Planning & State        # Plans, checkpoints, resume
│   ├── plan_ledger.py          # Plan task tracking
│   ├── natural_language_plan.py # NL→structured plan generation
│   ├── worktree.py             # Worktree isolation for parallel execution
│   ├── checkpoint management   # (via orchestrator)
│   └── resume_validation.py    # Resume-from-checkpoint validation
│
├── Intelligence            # Routing, stuck detection, complexity
│   ├── stuck_detector.py   # Stagnation detection and recovery
│   ├── complexity.py       # Task complexity estimation
│   ├── feedback_router.py  # Feedback loop routing
│   ├── signal_pipeline.py  # Signal extraction from outputs
│   ├── profiling.py        # Runtime profiling hooks
│   └── context_freshness.py # Context staleness detection
│
├── Policy & Config         # Configuration, constraints, enforcement
│   ├── policy_loader.py        # Policy file loading (3 dependents)
│   ├── constraint_checker.py   # Constraint validation
│   ├── enforcement_config.py   # Enforcement rule configuration
│   ├── tool_policy.py          # Tool usage policy
│   ├── harness_profiles.py     # Harness profile definitions
│   ├── lightweight_mode.py     # Lightweight mode toggle
│   └── profile_detector.py     # Auto-detect project profile
│
├── Output & Telemetry      # Progress, cost, telemetry
│   ├── progress_tracker.py     # Progress tracking
│   ├── progressive_output.py   # Streaming output
│   ├── output_compression.py   # Output compression
│   ├── cost.py                 # Cost tracking
│   ├── telemetry.py            # Telemetry collection
│   └── crystallization.py      # Knowledge crystallization
│
├── Utilities               # Shared helpers
│   ├── errors.py           # RuntimeViolation + error types (8 dependents)
│   ├── execute_context.py  # Execution context management
│   ├── ears_parser.py      # EARS requirement parsing
│   ├── task_identity.py    # Task identity and naming
│   ├── stale_recovery.py   # Stale state recovery
│   └── versioning.py       # Version utilities
│
└── Subpackages
    ├── evolution/           # Rule lifecycle engine (10 modules)
    │   ├── rules.py         # Rule definitions (7 dependents)
    │   ├── proposals.py     # Rule proposals (3 dependents)
    │   ├── promotions.py    # Promotion execution (3 dependents)
    │   ├── promotion_gates.py # Promotion gate checks (3 dependents)
    │   ├── audit.py         # Audit trail (9 dependents — highest fan-in)
    │   ├── lifecycle.py     # Lifecycle management
    │   ├── execution.py     # Rule execution
    │   ├── observations.py  # Observation recording
    │   ├── cases.py         # Case management
    │   └── doctor.py        # Self-diagnosis
    │
    ├── experiment/          # Experiment loop & metrics
    │   └── (circuit breaker, stopping policy, metrics)
    │
    └── orchestra/           # Multi-model orchestration
        └── strategy.py      # Consensus/debate/pipeline/fastest (4 dependents)
```

## Dependency Hubs

Modules with the highest fan-in (most imported by others):

| Module | Imported by | Role |
|--------|------------|------|
| `executor` | 9 | Adapter dispatch — everything goes through here |
| `evolution.audit` | 9 | Audit trail — evolution hooks everywhere |
| `errors` | 8 | `RuntimeViolation` — shared error types |
| `evolution.rules` | 7 | Rule definitions for evolution hooks |
| `orchestra.strategy` | 4 | Multi-model orchestration strategies |
| `artifact_validation` | 3 | Schema validation — gate, orchestrator, task identity |

## Data Flow

```
                    ┌──────────────┐
                    │  CLI / API   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ orchestrator │ ◄── Central coordinator
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──┐  ┌──────▼──┐  ┌──────▼──┐
       │ engine  │  │ routing │  │  gates  │
       └────┬────┘  └────┬────┘  └────┬────┘
            │            │            │
       ┌────▼────┐       │       ┌────▼────────┐
       │executor │       │       │ gate_eval   │
       │(adapter)│       │       │ gate_ralf   │
       └────┬────┘       │       └─────────────┘
            │            │
       ┌────▼────────────▼──────┐
       │   Artifact Layer       │
       │  validation / migrate  │
       └────┬───────────────────┘
            │
       ┌────▼────────────────────┐
       │   JSON Artifacts        │
       │  (brief, plan, review,  │
       │   checkpoint, state)    │
       └─────────────────────────┘
```

## Key Design Decisions

1. **Artifact-first**: All state lives in JSON files on disk. No database, no hidden state. Every stage transition produces a validated artifact.

2. **Zero dependencies**: stdlib only. No pip install required. The runtime is self-contained.

3. **Gate enforcement**: Every stage transition must pass through `gate_evaluation`. Gates check artifact presence, schema validity, and quality criteria before allowing advancement.

4. **Schema migration**: Artifacts carry `schema_version`. The runtime auto-migrates older versions on load (`validate_and_migrate` mode). Current version: `0.2`, minimum supported: `0.1`.

5. **Route-based complexity**: Tasks are classified as `small`, `medium`, or `high` routes. Higher routes include more stages (spec review, quality review, eval records).

6. **Evolution hooks**: The `evolution/` subpackage provides rule lifecycle management with audit trails. Rules can be proposed, reviewed, promoted, and retired — all artifact-tracked.

7. **Multi-model orchestration**: The `orchestra/` subpackage supports consensus, debate, pipeline, and fastest strategies for multi-model workflows.
