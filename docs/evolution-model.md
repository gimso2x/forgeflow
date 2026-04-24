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
restore  -> move a retired rule back into .forgeflow/evolution/rules with a reason
doctor        -> read-only health check for active/retired rules and audit JSONL
effectiveness -> read-only audit-backed rule effectiveness review
promotion-plan -> read-only promotion proposal with evidence, approvals, and risk flags
proposal-review -> read-only validation of a persisted proposal
proposal-approve -> append-only human approval ledger; no promotion or rule mutation
proposal-approvals -> read-only approval ledger status and remaining approvals
promotion-gate -> read-only gate readiness check; no promotion or rule mutation
promotion-decision -> append-only human policy-gate decision; still no promotion
audit         -> show recent project-local lifecycle/execution events
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

`execute` never reads retired rules. Restore requires an explicit reason and re-runs safety checks before moving the rule back:

```bash
python3 scripts/forgeflow_evolution.py restore \
  --rule no-env-commit \
  --reason "false positive fixed"
```

The audit log records adopt, execute, retire, and restore events:

```bash
python3 scripts/forgeflow_evolution.py audit --limit 20
```

`doctor` is the read-only rot detector for the closed loop:

```bash
python3 scripts/forgeflow_evolution.py doctor --json
```

It checks active rules, retired rules, duplicate active/retired IDs, audit-log JSONL parsing, and required audit event fields. The closed-loop surfaces stay deliberately constrained: reactive fix learning is advisory metadata only, proactive feedback learning keeps raw text disabled, and meta effectiveness review is audit-backed only.

`effectiveness` reads audit history for one rule and returns a recommendation without mutating anything:

```bash
python3 scripts/forgeflow_evolution.py effectiveness \
  --rule no-env-commit \
  --since-days 30 \
  --json
```

Recommendations are intentionally non-binding:

```text
0 failures with executions -> effective_candidate
1 failure              -> watch_candidate
2+ failures            -> promotion_candidate
no executions          -> insufficient_data
```

Even `promotion_candidate` keeps `would_promote=false` and `would_mutate=false`. Automatic SOFT→HARD promotion needs a separate policy gate; otherwise the loop starts sharpening knives in the dark.

`promotion-plan` turns the same audit-backed evidence into a non-mutating operator proposal:

```bash
python3 scripts/forgeflow_evolution.py promotion-plan \
  --rule no-env-commit \
  --since-days 30 \
  --write \
  --json
```

`--write` saves the proposal under:

```text
.forgeflow/evolution/proposals/<timestamp>-<rule>-promotion-plan.json
```

This still does not append audit events or mutate rule registries. It only makes the proposal durable for later review.

The plan contains:

```text
recommendation
required_human_approvals
evidence_summary
risk_flags
suggested_next_command
```

For `promotion_candidate`, the required approvals are `maintainer_approval` and `project_owner_approval`, and the plan still reports `would_mutate=false`. It is a proposal, not a sneaky promote button with a moustache.

`proposal-review` validates a persisted proposal without mutating anything:

```bash
python3 scripts/forgeflow_evolution.py proposal-review \
  --proposal .forgeflow/evolution/proposals/<timestamp>-no-env-commit-promotion-plan.json \
  --json
```

It checks that the proposal is valid JSON, still says `would_mutate=false` and `would_promote=false`, has `recommendation=promotion_candidate`, includes required human approvals and risk flags, has enough evidence summary, and still maps to an active project-local rule. Failed review returns a clean error status with issue codes; it does not append audit events or change rules.

`proposal-approve` records one required human approval for a proposal that still passes `proposal-review`:

```bash
python3 scripts/forgeflow_evolution.py proposal-approve \
  --proposal .forgeflow/evolution/proposals/<timestamp>-no-env-commit-promotion-plan.json \
  --approval maintainer_approval \
  --approver "kim" \
  --reason "reviewed evidence" \
  --json
```

Approval records are append-only JSONL files under:

```text
.forgeflow/evolution/proposal-approvals/<proposal-id>.jsonl
```

The command requires a non-empty approver and reason, accepts only approvals listed in `required_human_approvals`, and rejects proposals that fail review. Repeated approvals are allowed as explicit duplicate records because append-only ledgers should not silently rewrite history. It still reports `would_promote=false` and `would_mutate_rules=false`; this is a paper trail, not a launch button.

`proposal-approvals` reads that ledger and reports whether all required approvals are present:

```bash
python3 scripts/forgeflow_evolution.py proposal-approvals \
  --proposal .forgeflow/evolution/proposals/<timestamp>-no-env-commit-promotion-plan.json \
  --json
```

It returns:

```text
required_approvals
recorded_approvals
missing_approvals
duplicates
ready_for_policy_gate
would_promote=false
would_mutate_rules=false
```

`ready_for_policy_gate=true` only means the approval paperwork is complete enough for a separate policy gate discussion. It still does not promote, edit rules, or bless automatic SOFT→HARD promotion. A green clipboard is not a deploy key.

`promotion-gate` combines proposal review and approval-ledger status into one read-only gate report:

```bash
python3 scripts/forgeflow_evolution.py promotion-gate \
  --proposal .forgeflow/evolution/proposals/<timestamp>-no-env-commit-promotion-plan.json \
  --json
```

It checks:

```text
proposal_valid
all_required_approvals_present
approval_records_complete
risk_flags_acknowledged
ready_for_policy_gate
would_promote=false
would_mutate_rules=false
```

`approval_records_complete` requires non-empty `approver` and `reason` on approval records. `risk_flags_acknowledged` requires the promotion proposal to carry `promotion_requires_separate_policy_gate`. If anything is missing, the command exits non-zero with issue codes. Even when it passes, it is still a gate report, not promotion. The door is visible; the handle is still not installed.

`promotion-decision` records the human decision to approve the policy gate after `promotion-gate` passes:

```bash
python3 scripts/forgeflow_evolution.py promotion-decision \
  --proposal .forgeflow/evolution/proposals/<timestamp>-no-env-commit-promotion-plan.json \
  --decision approve_policy_gate \
  --decider "kim" \
  --reason "promotion gate reviewed" \
  --write \
  --json
```

Decision records are append-only JSONL files under:

```text
.forgeflow/evolution/promotion-decisions/<proposal-id>.jsonl
```

The command accepts only `approve_policy_gate`, requires non-empty `decider` and `reason`, and rejects proposals whose `promotion-gate` is not ready. `--write` is required to persist the record; without it the command returns the would-be decision path but writes nothing. It still reports `would_promote=false` and `would_mutate_rules=false`. This is the person saying “open the policy gate next,” not the system promoting anything.
