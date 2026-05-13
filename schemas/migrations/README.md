# Migration skeleton

ForgeFlow artifact schemas are versioned, but runtime migration is deliberately conservative.

Current policy:
- Current artifact schema version: `0.2`
- Supported range: `0.1` – `0.2`
- Current runtime mode: `validate_and_migrate`
- Current migration path: `0.1 -> 0.2` (brief: specialist fields, review-report: review_roles)

The real runtime entrypoint is `forgeflow_runtime/artifact_migrations.py`. The operator CLI is `scripts/upgrade_artifact.py`.

This directory exists as the schema-side migration playbook, not a second runtime source of truth. When a future schema version lands, add the executable transform to `forgeflow_runtime/artifact_migrations.py`, then mirror the compatibility notes here so reviewers can audit schema evolution without spelunking through runtime code.

## Version bump checklist

1. Add or update the JSON schema in `schemas/`.
2. Update `ARTIFACT_VERSION_POLICY` in `forgeflow_runtime/artifact_migrations.py` for the affected artifact types.
3. Add an ordered transform in `migrate_artifact_payload()`.
4. Add tests covering old payload -> migrated payload -> `validate_artifact_payload()` pass.
5. Smoke the operator path:

```bash
scripts/upgrade_artifact.py --artifact-name brief --path .forgeflow/tasks/<task-id>/brief.json --check
scripts/upgrade_artifact.py --artifact-name brief --path .forgeflow/tasks/<task-id>/brief.json
```

6. Document runtime behavior: refuse, warn, or auto-upgrade. Default remains refuse unless explicitly changed.

Do not silently coerce unknown versions. Silent migration bugs are the kind that wear a fake moustache and call themselves “compatibility”.
