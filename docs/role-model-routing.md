# Role / Model Routing

ForgeFlow keeps routing simple: stages choose roles, and operators may bind models to those roles in their own CLI/runtime configuration. The artifact contract records the role boundary; it does not require a central model database.

## Canonical responsibilities

- **planning** — clarify scope, decompose work, write/update plan artifacts, define file boundaries.
- **implementation** — edit code/docs only inside the assigned scope, run required validation, update evidence refs.
- **review** — inspect diff/artifacts independently, separate reported evidence from observed evidence, approve or request changes.
- **qa** — reproduce behavior, run scenarios, check edge cases, and record validation evidence.

## Runtime role mapping

Default runtime stage roles are owned by `forgeflow_runtime/operator_routing.py`:

- `clarify`, `finalize` → `coordinator`
- `milestone`, `plan` → `planner`
- `execute`, `long-run` → `worker`
- `spec-review` → `spec-reviewer`
- `quality-review` → `quality-reviewer`
- specialist stages such as `security-review`, `frontend-execute`, `backend-execute`, `infra-execute`, `ux-review`, `perf-review` → specialist reviewers/workers

## Model binding guidance

Model names are intentionally not hard-coded in artifacts. Use these defaults when your shell supports role-specific model selection:

- planning/coordinator: strongest reasoning model available
- implementation/worker: coding-optimized model with tool access
- review/spec/quality: independent model or at least a separate session from implementation
- qa: model/session focused on reproduction and test execution

If only one model is available, keep the role boundary by using separate sessions and artifact handoffs. Do not let the implementing session silently approve its own work.

## Handoff fields to preserve

When handing off between roles, include:

- task directory
- current stage and route
- assigned role
- allowed file scope
- required gates
- structured `evidence_refs`
- next command or slash stage
