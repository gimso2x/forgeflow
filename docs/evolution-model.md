# Evolution model

ForgeFlow self-evolution is intentionally split into two scopes:

```text
global advisory only
project-local enforcement
```

The invariant is simple: global learning may suggest, but project-local adoption is required before any HARD rule can block work.

## Scope boundary

### Global scope

Global evolution is metadata-only by default. It may learn redacted patterns and advise `/forgeflow:clarify` or `/forgeflow:plan`, but it must not block by default.

Allowed global behavior:

```text
learn_metadata_patterns
advise_clarify
advise_plan
```

Forbidden global behavior:

```text
raw_prompt_storage_by_default
raw_frustration_text_by_default
hard_enforcement_by_default
cross_project_exit_2
```

raw evidence stays project-local unless a maintainer explicitly redacts and exports it.

### Project scope

Project evolution owns adopted rules, raw evidence, audit trail, eval records, and HARD enforcement.

Project-local rules live under:

```text
.forgeflow/evolution/rules/*.json
```

Examples live under:

```text
examples/evolution/*.json
```

Examples are not operational rules. They are templates. `execute` does not run examples directly.

## Retrieval contract

Global retrieval is capped and explainable:

```yaml
max_patterns: 3
requires:
  - confidence
  - why_matched
  - scope
  - source_count
```

This prevents hidden enforcement through prompt stuffing. If a pattern is shown to clarify/plan, the agent must know why it matched and where it came from.

## Rule lifecycle

```text
candidate -> soft -> hard_candidate -> adopted_hard -> retired
```

HARD promotion requires:

```text
project_local_enablement
soft_soak_period
independent_recurrence_or_audited_maintainer_enablement
deterministic_check
low_false_positive_rate
rollback_available
eval_record
audit_trail
```

## Runtime surfaces

The runtime ladder is deliberately gradual:

```text
inspect  -> read policy and examples
list     -> show project registry and optional examples
adopt    -> copy a safe example into .forgeflow/evolution/rules
dry-run  -> show command and safety checks without executing
execute  -> run only project-local adopted rules with explicit acknowledgement
retire   -> move a project-local rule into .forgeflow/evolution/retired-rules with a reason
audit    -> show recent project-local lifecycle/execution events
```

Execute requires the long flag:

```bash
python3 scripts/forgeflow_evolution.py execute \
  --rule no-env-commit \
  --i-understand-project-local-hard-rule
```

That flag is intentionally ugly. This should never become a silent `--yes` flow.

## Execution boundary

`execute` only loads `.forgeflow/evolution/rules/*.json` from the selected project root. It refuses rules that exist only in `examples/evolution/`.

Before execution, every rule must pass safety checks:

```text
scope_project
adopted_hard
hard_exit_2
deterministic
global_export_disabled
hard_gate_evidence_present
raw_evidence_absent
```

If any check fails, the command is not executed.

Retire requires an explicit reason:

```bash
python3 scripts/forgeflow_evolution.py retire \
  --rule no-env-commit \
  --reason "false positive for this project"
```

Retired rules move out of the active registry:

```text
.forgeflow/evolution/retired-rules/*.json
```

`execute` never reads retired rules. The audit log records adopt, execute, and retire events:

```bash
python3 scripts/forgeflow_evolution.py audit --limit 20
```
