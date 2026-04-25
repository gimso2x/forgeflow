# ForgeFlow Overall Improvement Review

Date: 2026-04-25

Source inputs:
- Local repo inspection on `/home/ubuntu/work/forgeflow`
- Validation baseline: `make validate` PASS, `python -m pytest -q` PASS (`354 passed`)
- Claude Code review via terminal CLI
- Codex review via terminal CLI

## 1. Executive verdict

ForgeFlow is in a good state: the repo is clean, validation is green, and the project has a strong artifact-first architecture. The next problem is not feature absence. The next problem is **change amplification**: core runtime files, policy files, and their tests are now large enough that every safe change costs too much attention.

So the correct next phase is not “add more agent features.” It is:

1. reduce runtime/test hotspots,
2. preserve the artifact contracts,
3. make generated/adaptor/doc source-of-truth boundaries explicit,
4. keep every refactor behavior-preserving and test-backed.

Short version: ForgeFlow is no longer a toy. Treat it like infrastructure.

## 2. Current evidence

### Git / validation state

```text
branch: main
main == origin/main at 625e381 docs: align ForgeFlow make-target contracts
working tree: clean
make validate: PASS
python -m pytest -q: 354 passed
```

### Repository shape

Approximate file counts:

```text
forgeflow_runtime: 21 files
scripts:           55 files
tests:             127 files
adapters:          28 files
schemas:           15 files
docs:              61 files
skills:            25 files
```

Approximate line counts, excluding `.git`, `.venv`, and caches:

```text
Markdown: 144 files / 17,948 lines
Python:    61 files / 15,952 lines
JSON:     197 files /  4,768 lines
YAML:      12 files /    478 lines
```

Largest Python files:

```text
tests/test_runtime_orchestrator.py  2753
 tests/test_evolution_policy.py     2060
forgeflow_runtime/orchestrator.py   1660
forgeflow_runtime/evolution.py      1287
scripts/forgeflow_evolution.py       567
tests/test_validate_generated.py     524
tests/test_first_clone_setup.py      445
scripts/install_agent_presets.py     350
scripts/run_orchestrator.py          336
forgeflow_runtime/executor.py        326
```

## 3. Top strengths

### 3.1 Artifact-first architecture is the right core

ForgeFlow’s strongest design choice is refusing to make chat memory the source of truth. The real workflow lives in explicit artifacts, schemas, stage gates, checkpoints, and review reports.

That is the right architecture for AI coding agents. Chat is fog. Artifacts are ground.

### 3.2 Validation discipline is real

The validation stack is not pretend-documentation:

- structure validation
- policy validation
- generated adapter drift validation
- sample artifact validation
- adherence evals
- import/mirror validation
- skill contract validation
- Claude hook validation
- plugin manifest validation
- runtime/orchestrator/evolution tests

The green baseline makes controlled refactors possible.

### 3.3 Adapter boundaries are mostly contained

Claude, Codex, and Cursor surfaces exist, but they do not dominate the runtime core. Recent generated-drift and preset contract hardening made this better.

### 3.4 Operational pain is being fixed at the right layer

Recent work moved examples toward repo-managed Make targets, venv-backed commands, and first-clone safe paths. That is boring work, which is exactly why it matters. Boring paths are where users actually fall over.

## 4. Top risks and bottlenecks

### P0 risk: runtime hotspots are too big

`forgeflow_runtime/orchestrator.py` and `forgeflow_runtime/evolution.py` are now high-gravity files. They likely carry too many responsibilities: state loading, artifact resolution, gate policy, route selection, execution dispatch, validation, and recovery semantics.

This makes every change expensive. Not impossible, just sticky.

### P0 risk: mega-tests mirror the same coupling

`tests/test_runtime_orchestrator.py` and `tests/test_evolution_policy.py` are too large. Passing is good, but a 2,753-line test file is not a comfort blanket. It is a haystack with assertions hidden inside.

The test suite should still be broad, but failure locality needs to improve.

### P1 risk: scripts may become second runtimes

There are 55 script files versus 21 runtime files. That is not automatically bad, but it is a drift warning.

The rule should be strict:

```text
scripts parse arguments and call runtime APIs.
scripts do not become alternative implementations of runtime behavior.
```

Recent Make target hardening helped. The next step is checking whether script logic can be thinned.

### P1 risk: documentation is large enough to fork reality

ForgeFlow has many docs, plans, generated adapter docs, plugin docs, skills, and install instructions. That is useful, but it creates source-of-truth pressure.

The repo needs a contract map that clearly says:

- what is canonical,
- what is generated,
- what is an example,
- what command validates each surface.

### P1 risk: schema versioning is not yet a migration story

Schemas pin artifact shapes. Good. But long-lived artifact-first systems eventually need migration/coercion rules. If schema versioning stays “const 0.1 forever,” future changes will either stall or break old tasks.

Do not overbuild migrations now. But define the seam before the first painful schema change.

## 5. Claude review summary

Claude’s review agreed that the architecture is strong and the next step is focused maintainability.

Claude emphasized:

- artifact-first architecture is the key strength,
- explicit schema contracts are valuable,
- complexity routing and independent review are good design choices,
- current validation infrastructure is strong,
- biggest near-term issue is large runtime/test files,
- schema migration and better error types will matter soon.

Claude’s suggested next sequence:

1. split large test files,
2. add schema version upgrade path,
3. improve error handling,
4. add runtime metrics,
5. unify CLI surface.

Good take, but I would not start with schema migration before decomposing tests. The tests are the safety net; untangle that net first.

## 6. Codex review summary

Codex was sharper on engineering sequencing.

Codex emphasized:

- the project is healthy, but structural complexity is now the limiting factor,
- `orchestrator.py`, `evolution.py`, and their mega-tests are the main hotspots,
- the script surface is wide and can drift into duplicate behavior,
- docs have source-of-truth fragmentation risk,
- generated adapter/plugin boundaries need a single contract map,
- next phase should be maintainability and contract hardening, not capability expansion.

Codex’s suggested next sequence:

1. test decomposition,
2. orchestrator seam extraction,
3. evolution policy extraction,
4. script thinning,
5. contract/doc source-of-truth map.

This is the better sequencing. Start where the blast radius is lowest: tests first, runtime seams second.

## 7. Improvement backlog

### P0 — do next

#### P0.1 Split mega-tests by behavior family

Target files:

```text
tests/test_runtime_orchestrator.py
tests/test_evolution_policy.py
```

Proposed split:

```text
tests/runtime/test_stage_transitions.py
tests/runtime/test_artifact_validation.py
tests/runtime/test_checkpoint_resume.py
tests/runtime/test_review_gates.py
tests/runtime/test_route_selection.py
tests/evolution/test_policy_loading.py
tests/evolution/test_rule_scoring.py
tests/evolution/test_generation_step.py
tests/evolution/test_rewind_and_status.py
```

Acceptance criteria:

- no behavior change,
- `python -m pytest -q` stays green,
- shared fixtures/builders move to `tests/fixtures` or `tests/conftest.py` only when they reduce duplication,
- no “utils dumping ground.”

Why first: this lowers the cost of every later refactor.

#### P0.2 Extract one orchestrator seam

Target:

```text
forgeflow_runtime/orchestrator.py
```

Do not rewrite it. Extract one seam only.

Best first candidates:

```text
artifact loading / validation helpers
gate evaluation
route selection / route floor logic
checkpoint resume validation
```

Acceptance criteria:

- top-level public API remains stable,
- existing CLI behavior unchanged,
- focused unit tests cover extracted seam,
- integration tests still pass.

#### P0.3 Extract one evolution policy seam

Target:

```text
forgeflow_runtime/evolution.py
scripts/forgeflow_evolution.py
```

Best first candidates:

```text
policy representation
rule scoring / selection
status reconstruction
rewind mechanics
```

Acceptance criteria:

- no change to generated/evolution outputs,
- policy decisions testable without running the whole loop,
- existing adherence/evolution tests remain green.

#### P0.4 Keep scripts thin

Targets:

```text
scripts/run_orchestrator.py
scripts/forgeflow_evolution.py
scripts/forgeflow_plan.py
scripts/forgeflow_monitor.py
```

Rule:

```text
scripts parse CLI args, call runtime/library functions, print output.
runtime/library owns behavior.
```

Acceptance criteria:

- no duplicated policy logic in scripts,
- CLI tests assert wiring, not reimplement rules,
- direct script examples remain Make-target-backed where read-only and repo-managed.

### P1 — next wave

#### P1.1 Contract source-of-truth map

Create a canonical document, likely:

```text
docs/contract-map.md
```

It should map:

```text
schemas/*.json                 canonical artifact contracts
forgeflow_runtime/*             runtime behavior
adapters/targets/*              handwritten adapter source
adapters/generated/*            generated output
.claude-plugin / .codex-plugin  plugin packaging surfaces
Make targets                    repo-managed execution paths
examples/runtime-fixtures       golden runtime examples
```

For each surface, include:

```text
owner/source of truth
regeneration command
validation command
known consumers
```

#### P1.2 Schema version migration seam

Do not build a giant migration framework. Start with a tiny seam:

```text
forgeflow_runtime/schema_versions.py
```

Acceptance criteria:

- current `0.1` artifacts still validate,
- invalid future/unknown versions fail with a clear error,
- one test documents where migration hooks will live.

#### P1.3 Structured runtime metrics

Start local-only. No network. No SaaS.

Potential artifact:

```text
metrics.json
```

Track:

```text
stage duration
retry count
gate failure count
validation error count
review approval/reject count
adapter execution mode: stub/real
```

This feeds `forgeflow_monitor.py` later.

#### P1.4 Golden end-to-end fixture tests

Use existing runtime fixtures more explicitly.

Goal:

```text
Given fixture X and route Y,
when running command Z,
then emitted artifacts match schema and key stable fields.
```

This protects future refactors.

### P2 — later

#### P2.1 Adapter capability normalization

Claude/Codex/Cursor should share an internal capability model. Generate adapter-specific docs from that.

#### P2.2 Repo health dashboard

Local CLI only at first:

```bash
make repo-health
```

Output:

```text
largest files
slowest tests if available
validation surfaces
generated drift status
docs contract-map freshness
```

#### P2.3 Audience-based docs restructuring

Docs should eventually split by reader:

```text
user/operator
adapter author
ForgeFlow maintainer
plugin installer
AI agent consuming the harness
```

But do not start here. Docs restructuring before contract-map is how you make a prettier maze.

## 8. Suggested next 5 PRs

### PR 1 — test decomposition without behavior change

Goal:

```text
Split one mega-test file into behavior-focused modules.
```

Start with `tests/test_runtime_orchestrator.py`, not both huge files at once.

Acceptance:

```text
same tests pass
no runtime code changes unless import paths force tiny fixture moves
```

### PR 2 — extract orchestrator gate/artifact seam

Goal:

```text
Move one coherent responsibility out of orchestrator.py.
```

Recommended seam:

```text
gate evaluation or checkpoint resume validation
```

### PR 3 — split evolution policy tests

Goal:

```text
Make evolution policy behavior easier to locate and review.
```

Only after PR 1 proves the test split pattern.

### PR 4 — extract evolution policy seam

Goal:

```text
Separate policy/rule scoring from execution plumbing.
```

### PR 5 — add contract map document + validation smoke

Goal:

```text
Make source-of-truth boundaries explicit and test one or two high-risk claims.
```

This prevents the next round of docs/generated/scripts drift.

## 9. Things not to do

- Do not do a big-bang runtime rewrite.
- Do not add new adapters before shrinking the current hotspots.
- Do not create a generic `utils.py` junk drawer.
- Do not add SaaS telemetry or network dependencies for observability.
- Do not make chat memory a fallback source of truth.
- Do not broaden the cron/autoresearch loop until this backlog is packaged into small PRs.
- Do not restructure docs before defining the contract map.
- Do not chase schema migration as a large framework before extracting tests.

## 10. Recommended immediate action

Do **PR 1**:

```text
Split tests/test_runtime_orchestrator.py into smaller runtime test modules without behavior changes.
```

Why this one:

- lowest product risk,
- improves future review speed,
- gives a safe path to extract orchestrator seams,
- reduces the biggest current maintenance bottleneck.

This is not glamorous. Good. Glamour is how harnesses become unusable.
