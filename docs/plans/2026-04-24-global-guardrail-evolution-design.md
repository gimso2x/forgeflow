# Global Guardrail Evolution Design Plan

> **For Hermes:** This is a design-first plan. Do not implement runtime mutation yet. First get independent Claude and Codex reviews, then revise the canonical policy.

**Goal:** Define ForgeFlow self-evolution as a two-scope loop: global cross-project learning informs `/forgeflow:clarify` and `/forgeflow:plan`, while project-local adoption controls HARD enforcement.

**Architecture:** Global memory stores metadata-only reusable mistake patterns from opted-in projects, but it cannot block execution by default. Raw evidence stays project-local unless an operator explicitly exports a redacted bundle. Project-local policy decides which rules are adopted and which can become HARD gates. The loop converts evidenced repeated mistakes into guardrails, not vibes into commandments.

**Reference Inputs:**
- `engineering-discipline` — workflow skeleton, checkpoint/source-of-truth, worker/validator split
- `hoyeon` — artifact contracts, schema discipline, learnings/context files
- `gstack` — canonical policy → generated adapters, local memory/eval substrate
- `superpowers` — adversarial review, anti-rationalization, spec-review before quality-review
- Hugh Kim Claude Code Harness — mistake-to-guardrail loop, SOFT→HARD promotion, hook `exit 2` enforcement

---

## 1. Problem

Plain rules in `CLAUDE.md`/`CODEX.md` are weak. Agents forget, rationalize, or repeat the same failure in the next session. The harness should learn from actual mistakes.

But global automatic enforcement is dangerous. A rule learned in one repo can be wrong in another. So ForgeFlow needs a split:

```text
global scope  = learn, rank, retrieve, advise
project scope = adopt, verify, enforce, rollback
```

Short version:

```text
Global learns. Global advises. Global does not block by default.
Project adopts. Project verifies. Project blocks.
```

---

## 2. Core Concept: Mistake-to-Guardrail Loop

The self-evolution unit is a **guardrail**, born from an evidenced mistake.

Pipeline:

```text
signal → evidence bundle → pattern → candidate rule → SOFT rule → project adoption → HARD rule → eval keep/discard
```

Signal sources:

```text
fix commit
review finding
eval failure
repeated tool failure
user frustration phrase
manual operator note
```

Evidence sources:

```text
git diff
commit message
review-report.json
decision-log.json
eval-record.json
run-state.json
tool failure logs
user prompt snippet
```

A user frustration phrase is only a signal, not evidence. Phrases like “왜이래”, “또 이래”, “이거 하지 말랬지” can start investigation, but cannot create HARD rules alone.

---

## 3. Storage Model

### 3.1 Global Store

Recommended configurable default:

```text
${FORGEFLOW_EVOLUTION_HOME:-~/.forgeflow/evolution}/
  patterns/
    global-patterns.jsonl
  rules/
    global-soft-rules.json
  indexes/
    project-map.json
    rule-effectiveness.json
  evals/
    retrieval-quality.jsonl
```

Global storage is **metadata-only by default**:

```text
pattern id
normalized tags
project fingerprint, not absolute private path
language/framework/surface tags
counts and time windows
rule effectiveness metrics
redacted evidence refs, not raw evidence
```

Raw prompt snippets, raw frustration text, full diffs, review artifacts, and tool logs stay project-local unless the operator explicitly exports a redacted evidence bundle.

Properties:

```text
scope: global
permission: metadata learning store
activation: explicit opt-in or configured path
default enforcement: none
used by: clarify, plan, review
```

### 3.2 Project Store

Recommended default:

```text
<project>/.forgeflow/evolution/
  adopted-rules.json
  local-soft-rules.json
  local-hard-rules.json
  pending/
    self-improve-*.json
  evidence/
    <rule-id>/
      evidence.json
      diff.patch
      review-report.json
      eval-record.json
  evals/
    guardrail-score.json
    regression-history.tsv
  hooks/
    pre-commit.sh
    pre-push.sh
```

Properties:

```text
scope: project-local
permission: enforcement allowed only here
HARD gate: allowed only for adopted local hard rules
```

---

## 4. Rule Lifecycle

```text
candidate → soft → hard_candidate → adopted_hard → retired
```

`soft` may be global advisory or project-local advisory. Adoption is metadata on the rule, not a separate lifecycle state. This keeps v1 smaller: one advisory state, one blocking state, and one retirement path.

### candidate

Created from one or more signals plus evidence.

Required fields:

```json
{
  "rule_id": "generated-stable-id",
  "title": "Do not hand-edit generated adapter files",
  "scope": "global|project",
  "source_projects": ["forgeflow"],
  "signals": ["fix_commit", "review_finding"],
  "evidence_refs": [],
  "suggested_check": null,
  "severity": "low|medium|high",
  "false_positive_risk": "low|medium|high",
  "status": "candidate"
}
```

### soft

Advisory only. Can be injected into clarify/plan/review.

Behavior:

```text
warn
add checklist item
add plan verification step
add review question
```

### project-adopted soft

A project may mark a soft rule as locally adopted without making it blocking.

Behavior:

```text
project-local warning
review checklist
no exit 2
```

### hard_candidate

Eligible for blocking if all conditions hold:

```text
project-local enablement exists
soft-mode soak period completed
independent recurrence_count >= 2, or explicit maintainer hard-enable with audit note
deterministic_check_available == true
false_positive_risk == low
measured false_positive_rate stays below threshold
rollback_available == true
clear remediation text exists
eval_record exists
```

`explicit maintainer hard-enable` does not mean automatic import from global memory. It means a project owner deliberately enables the local HARD rule and leaves an audit trail.

### adopted_hard

Project-local hook can block with `exit 2`.

Behavior:

```text
hook blocks action
prints exact reason
prints remediation
writes evidence record
```

### retired

Rule is disabled when it is noisy, obsolete, or repeatedly blocks valid work.

---

## 5. Global Retrieval in `/forgeflow:clarify`

Clarify should query global patterns by task traits.

Inputs:

```text
user request
repo language/framework
changed surface if known
route guess
risk level
```

Retrieval contract:

```text
retrieve only when global evolution is enabled
return at most 3 patterns
include scope, confidence, why_matched, and source_count
prefer same framework/language/surface
prefer recent and multi-project-confirmed patterns
never include raw prompt snippets or raw frustration text
extra questions allowed only for unresolved high-risk boundaries
```

Output injected into clarify reasoning:

```text
Relevant prior failure patterns:
1. Next.js auth tasks repeatedly missed callback URL/env separation.
2. Generated adapter edits caused drift; prefer canonical source + regenerate.

Clarify questions to ask or bound:
- What environment scopes are affected: local, preview, production?
- Is this generated output or canonical source?
```

Hard rule: global retrieval must not force extra questions when the user request is already clear. It should add missing risk boundaries, not turn every request into an interrogation.

---

## 6. Global Retrieval in `/forgeflow:plan`

Plan should turn relevant global patterns into verification steps.

Example:

```text
Known pattern: generated adapter hand edits caused validation drift.
Plan injection:
- Modify canonical policy/docs/prompts only.
- Regenerate adapters with `python3 scripts/generate_adapters.py`.
- Run `make validate` and confirm generated validation passes.
```

Global rules can affect plan content, but they cannot block implementation unless locally adopted.

---

## 7. Enforcement Model

### Global

Allowed:

```text
rank patterns
suggest rules
inject warnings/checklists
recommend project adoption
```

Forbidden by default:

```text
exit 2
pre-push block
automatic generated file edits
automatic global-to-hard promotion across all projects
```

### Project

Allowed after adoption:

```text
local soft warnings
local hard hook `exit 2`
pre-commit/pre-push checks
project-specific rule retirement
```

---

## 8. Promotion Policy

A rule may become HARD only if:

```text
1. project-local enablement exists
2. soft-mode soak period completed
3. recurrence is independent, not repeated retries from one incident
4. deterministic check exists
5. check has low false-positive risk and measured false_positive_rate below threshold
6. remediation text is clear
7. rollback path exists
8. eval record exists and does not regress after enabling it
9. audit trail names why the project adopted this HARD rule
```

HARD rule example:

```text
Rule: Do not edit adapters/generated/* directly.
Check: git diff --name-only | grep '^adapters/generated/' and no canonical source changed.
Block: exit 2.
Remediation: edit canonical source and regenerate adapters.
```

Bad HARD rule example:

```text
Rule: Write better code.
Check: none.
Block: impossible.
```

That is not a rule. That is a motivational poster wearing a helmet.

---

## 9. Eval Keep/Discard

Every HARD promotion needs an eval record.

Metrics:

```text
blocked_real_issues / total_blocks
false_positive_count / total_blocks
manual_override_count / total_blocks
independent_recurrence_after_rule within 30/90 day windows
validation_pass_rate before/after
operator_retained_rule after review window
project_count_confirming_pattern
```

Decision:

```text
keep if recurrence decreases and false positives stay low
soften if noisy
retire if obsolete or harmful
rollback if validation worsens
```

---

## 10. Canonical Policy Changes Proposed

Modify:

```text
policy/canonical/evolution.yaml
schemas/policy/evolution.schema.json
scripts/validate_policy.py
docs/architecture.md
README.md
```

Replace current project-only policy with explicit two-scope policy:

```yaml
version: 0.2
scopes:
  global:
    artifact_root: ${FORGEFLOW_EVOLUTION_HOME:-~/.forgeflow/evolution}
    activation: explicit_opt_in
    permissions:
      - learn_metadata_patterns
      - advise_clarify
      - advise_plan
      - advise_review
    forbidden:
      - raw_prompt_storage_by_default
      - raw_frustration_text_by_default
      - hard_enforcement_by_default
      - cross_project_exit_2
  project:
    artifact_root: .forgeflow/evolution
    permissions:
      - adopt_rules
      - verify_rules
      - enforce_adopted_hard_rules
      - store_raw_evidence
    hard_gate_requires:
      - project_local_enablement
      - soft_soak_period
      - independent_recurrence_or_audited_maintainer_enablement
      - deterministic_check
      - low_false_positive_rate
      - rollback_available
      - eval_record
      - audit_trail
rule_lifecycle:
  - candidate
  - soft
  - hard_candidate
  - adopted_hard
  - retired
signal_sources:
  - fix_commit
  - review_finding
  - eval_failure
  - repeated_tool_failure
  - user_frustration_label
  - manual_operator_note
retrieval_contract:
  max_patterns: 3
  requires:
    - confidence
    - why_matched
    - scope
    - source_count
non_negotiables:
  - global learns metadata and advises but must not block by default
  - raw evidence stays project-local unless explicitly redacted and exported
  - project-local adoption is required before HARD enforcement
  - user frustration is a signal label, not standalone evidence or raw global text
  - generated adapters are regenerated from canonical sources, not hand-edited
```

---

## 11. Implementation Plan After Review

### Task 1: Revise canonical evolution policy schema

Files:

```text
policy/canonical/evolution.yaml
schemas/policy/evolution.schema.json
scripts/validate_policy.py
tests/test_validate_policy.py
```

Verification:

```bash
pytest tests/test_validate_policy.py -q
make validate
```

### Task 2: Add global retrieval design docs

Files:

```text
docs/evolution-model.md
README.md
docs/architecture.md
```

Verification:

```bash
make validate
```

### Task 3: Add deterministic local HARD rule examples

Files:

```text
examples/evolution/generated-adapter-drift-rule.json
examples/evolution/no-env-commit-rule.json
```

Verification:

```bash
make validate
```

### Task 4: Add runtime only after policy stabilizes

Possible files:

```text
forgeflow_runtime/evolution.py
scripts/forgeflow_evolution.py
tests/test_evolution_policy.py
```

No runtime should be added until Claude/Codex reviews converge on the scope boundary.

---

## 12. Review Questions for Claude and Codex

1. Is the global/project split safe enough?
2. Is “global advises, project blocks” the right invariant?
3. Are the promotion criteria sufficient to prevent noisy HARD gates?
4. Should user frustration signals be stored globally, and if yes, how should privacy/scope be bounded?
5. Is `~/.forgeflow/evolution` the right global path for a multi-agent harness, or should it be configurable only?
6. What deterministic checks should be first-class examples?
7. What part of this design is overbuilt and should be cut?

---

## 13. Acceptance Criteria

- [x] Claude review returns no blocking architecture objections after privacy/scope refinements.
- [x] Codex review returns no blocking architecture objections after privacy/scope refinements.
- [x] If either reviewer flags global privacy/enforcement risk, revise this plan before implementation.
- [ ] Canonical policy is updated only after review.
- [x] Runtime mutation is not implemented in this design step.

---

## 14. Independent Review Summary

### Claude review

Verdict: fundamentally sound, but needed privacy protection, simpler lifecycle, and stronger effectiveness tracking.

Blocking concerns raised:

```text
- raw user frustration stored globally is privacy-risky
- global learning can contaminate unrelated projects
- recurrence_count >= 2 is too permissive without impact/effectiveness controls
```

Changes applied:

```text
- global store is metadata-only by default
- raw prompt/frustration/diff/log evidence stays project-local unless redacted and exported
- global path is configurable and explicit opt-in
- HARD promotion now requires project-local enablement, soak period, low false-positive rate, rollback, eval, audit trail
- lifecycle simplified by removing adopted_soft as a separate state
```

### Codex review

Verdict: promising but not ready to canonize until privacy, tenancy, retrieval, and HARD-promotion boundaries are tightened.

Blocking concerns raised:

```text
- global evidence storage was not privacy-safe
- explicit adoption clause could collapse safety boundary
- clarify/plan retrieval could become hidden enforcement
- ~/.forgeflow/evolution is unsafe as an assumed default on shared/CI machines
```

Changes applied:

```text
- global memory stores metadata patterns, not raw evidence
- global activation is explicit opt-in/configured path
- retrieval is capped to 3 patterns and must expose scope/confidence/why_matched/source_count
- extra clarify questions are allowed only for unresolved high-risk boundaries
- HARD promotion requires local enablement plus audit trail, not automatic global import
- v1 cuts ship-warning integration and full raw evidence indexing
```
