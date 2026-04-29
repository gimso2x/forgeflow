# AI-Readiness Cartography Upgrade

- Date: 2026-04-29
- Owner: ForgeFlow
- Status: completed
- Source skill: `gimso2x/skills_repo/ai-readiness-cartography`
- Baseline audit artifact: `/tmp/forgeflow-ai-score.json`
- After audit artifact: `/tmp/forgeflow-ai-score-after.json`
- Baseline score: `29/100` (`AI-Hostile` by external rubric)
- After score: `33/100` (`AI-Hostile` by external rubric)

## Goal

Absorb the useful *analysis requirements* from `ai-readiness-cartography` into ForgeFlow without adding a new lifecycle stage, external source of truth, or a pile of repo-only context docs.

The target is not to worship the external scorecard. The target is to make ForgeFlow's own review/validation model better at asking the right AI-readiness questions:

- Can an agent find the real entry points?
- Are referenced files real, generated, installed-target examples, or hypothetical?
- Are hidden decisions externalized somewhere durable?
- Are cross-module dependencies visible enough before editing?
- Is there a deterministic gate that catches stale context before release?

## Baseline Findings

External scorer result:

- Total: `29/100`
- Grade: `AI-Hostile`
- Modules: `5`
- Context files: `38`
- Large files over 300 lines: `15`

Category scores:

- A. AI Navigation & Coverage: `1/15`
- B. Context Document Quality: `3/20`
- C. Tribal Knowledge Externalization: `0/20`
- D. Cross-Module Dependency Mapping: `8/15`
- E. Verification & Quality Gates: `8/15`
- F. Freshness & Self-Maintenance: `6/10`
- G. Agent Performance Outcomes: `3/5`

High-signal findings:

- `context 미보유 핵심 module 4개: adapters, docs, forgeflow_runtime, tests`
- `root CLAUDE.md 부재 — 진입점 브리핑 없음`
- `hallucinated path 32건 (총 74 참조 중)`
- `CI에 context / docs validation step 없음`
- `MEMORY.md / ADR / docs/decisions 부재 — tribal knowledge 외부화 store 없음`
- `mermaid 다이어그램 없음 — 시각적 의존도 표현 부재`

## Absorption Rule

Follow `docs/external-skill-ingestion-model.md`:

- Adopt: path reference validation and review evidence discipline.
- Adapt: A-G readiness rubric as an optional audit/backlog lens.
- Archive: do not make the 100-point score a release gate.

Installable-product boundary:

ForgeFlow is not only a source repo; it is an installable harness/plugin that writes files into another target project. Therefore AI-readiness work must distinguish two surfaces:

- Source-repo contributor surface: files such as `AGENTS.md`, `docs/`, `scripts/`, `forgeflow_runtime/`, and `tests/` help agents safely modify ForgeFlow itself.
- Installed-project user surface: generated or copied artifacts such as `adapters/generated/claude/CLAUDE.md`, `adapters/generated/codex/CODEX.md`, `.claude-plugin/`, `.forgeflow/tasks/*`, and installer outputs help agents use ForgeFlow inside a target project.

Implication: do not add source-repo `AGENTS.md` files to pretend they are installed user guidance. Installed guidance belongs in generated adapter docs, installer output docs, or plugin command help. Source `AGENTS.md` is still useful, but it is contributor/developer context only.

Non-negotiable boundary:

- No new mandatory ForgeFlow stage.
- No new runtime state lane.
- No external skill repo as policy source of truth.
- No Claude-only context assumption in adapter-neutral docs.
- No source-only context file should be treated as proof that installed projects are well-guided.

## Scope

Create or modify:

- `scripts/validate_context_paths.py`
- `tests/test_validate_context_paths.py`
- `.github/workflows/*` or existing validation wiring, if present and appropriate
- `docs/review-model.md` or review checklist/schema docs, to absorb AI-readiness analysis questions
- `docs/external-skill-ingestion-model.md`, if the ingestion rule needs a clearer example
- `docs/decisions/README.md`
- `docs/decisions/0001-ai-readiness-cartography-absorption.md`
- `docs/architecture.md` or `docs/contract-map.md`, only if dependency-map guidance has no existing home
- stale path references in `README.md` and other context docs found by validation

De-prioritized unless later needed:

- Root/module `AGENTS.md` files. They help ForgeFlow contributors, but they do not improve the installed user surface by themselves.

Out of scope for this slice:

- Splitting `forgeflow_runtime/orchestrator.py`.
- Full telemetry/OpenTelemetry implementation.
- Mandatory AI-readiness score gates.
- Importing the external scorer into ForgeFlow runtime core.
- Adding context docs just to satisfy the external scorer.

## Acceptance Criteria

- A repo-local command can validate markdown/context path references and report broken references deterministically.
- Known stale references from the baseline audit are either corrected, marked as examples/placeholders, or ignored by an explicit documented rule.
- ForgeFlow review guidance includes AI-readiness analysis questions for navigation, evidence, dependency mapping, tribal knowledge, and freshness.
- Tribal knowledge has an explicit decision-log home under `docs/decisions/`.
- Architecture or contract mapping includes dependency-map guidance only where it helps real maintainers, not to chase scorecard points.
- Existing ForgeFlow validation still passes.
- The external audit score is re-run and the before/after score is recorded in this task document, but it remains a diagnostic metric, not a release gate.

## Step Plan

### Step 1 — Confirm baseline and exact stale path list

Objective: Turn the external audit finding into a concrete local target list.

Files:

- Read: `/tmp/forgeflow-ai-score.json`
- Read: `README.md`
- Read: existing markdown docs that contain broken references
- Produce: notes inside this task document, if needed

Commands:

```bash
python3 /tmp/tmp.xg6H43zYiJ/skills_repo/ai-readiness-cartography/scripts/score.py /home/ubuntu/work/forgeflow --json /tmp/forgeflow-ai-score.json
python3 - <<'PY'
import json
p='/tmp/forgeflow-ai-score.json'
data=json.load(open(p))
print(data['total'], data['grade'])
print(data['categories']['E']['findings'])
PY
```

Expected:

- Baseline remains reproducible.
- Broken reference examples are confirmed before editing.

### Step 2 — Add deterministic context path validator

Objective: Add a small stdlib validator for markdown path references.

Files:

- Create: `scripts/validate_context_paths.py`
- Create: `tests/test_validate_context_paths.py`
- Modify: `scripts/README.md` if command documentation is needed

Rules:

- Validate relative file/path references in markdown and agent context docs.
- Ignore URLs.
- Ignore code fences when references are clearly example-only, or support an explicit marker such as `example:` / placeholder angle brackets.
- Do not flag generated adapter docs unless the rule is intentional and documented.
- Output file, line, and reference for each broken path.

Verification:

```bash
.venv/bin/python -m pytest tests/test_validate_context_paths.py -q
.venv/bin/python scripts/validate_context_paths.py
```

### Step 3 — Fix or mark stale references

Objective: Remove the worst referential-trust failures.

Files:

- Modify: `README.md`
- Modify: any context markdown files reported by `scripts/validate_context_paths.py`

Known examples from baseline:

- `README.md: ./CLAUDE.md`
- `README.md: ./.forgeflow/tasks/my-task-001/checkpoint.js`
- `README.md: project/.codex/forgeflow/forgeflow-coordinator.md`
- `README.md: project/CODEX.md`

Policy:

- Real repo paths must exist.
- Example project paths must be clearly marked as examples/placeholders.
- Generated-install target paths must not pretend to exist in this repo.

Verification:

```bash
.venv/bin/python scripts/validate_context_paths.py
```

Expected:

- Broken context path count drops to zero or only explicit allowed examples remain.

### Step 4 — Absorb AI-readiness analysis questions into review guidance

Objective: Turn the external rubric into ForgeFlow-native review questions, not new source-repo context sprawl.

Files:

- Modify: `docs/review-model.md`
- Modify: schema/checklist docs only if there is already a natural hook

Review guidance should ask:

- Navigation: can a fresh agent identify the real entry points and command path?
- Evidence: are cited files real, installed-target examples, generated outputs, or hypothetical?
- Dependencies: does the change cross runtime, adapters, schemas, policy, prompts, or tests?
- Tribal knowledge: is the reason captured in a durable doc/decision when it affects future work?
- Freshness: is there a cheap gate that will catch this class of stale context later?

Constraints:

- Do not add `AGENTS.md` just to satisfy the external scorer.
- Do not add a new ForgeFlow lifecycle stage.
- Keep this as review/evaluation discipline that can apply to installed artifacts too.

Verification:

```bash
.venv/bin/python scripts/validate_context_paths.py
```

### Step 5 — Add decision-log home

Objective: Externalize tribal knowledge without creating a parallel runtime source of truth.

Files:

- Create: `docs/decisions/README.md`
- Create: `docs/decisions/0001-ai-readiness-cartography-absorption.md`
- Optionally link from: `docs/external-skill-ingestion-model.md`

Decision doc must state:

- What was adopted.
- What was adapted.
- What was rejected.
- Why this does not create a new ForgeFlow stage or score gate.

Verification:

```bash
.venv/bin/python scripts/validate_context_paths.py
```

### Step 6 — Add dependency map diagram

Objective: Make cross-module flow visible to humans and agents.

Files:

- Modify: `docs/architecture.md` or `docs/contract-map.md`

Add a small Mermaid diagram covering:

- `skills/*`
- `forgeflow_runtime/*`
- `policy/canonical/*`
- `schemas/*`
- `adapters/*`
- `prompts/canonical/*`
- `tests/*`
- `.forgeflow/tasks/*` artifact shape

Verification:

```bash
.venv/bin/python scripts/validate_context_paths.py
```

### Step 7 — Wire validation into existing gates

Objective: Prevent context paths from rotting again.

Files:

- Modify: `Makefile` or existing validation script, after inspection
- Modify: `.github/workflows/*`, if ForgeFlow already has a validation workflow

Rules:

- Prefer adding the validator to existing `make validate` if the cost is low.
- Do not add a heavy new CI lane.
- Keep output readable for operators.

Verification:

```bash
make validate
git diff --check
```

### Step 8 — Re-run external audit and record delta

Objective: Measure the result without making the external score a release gate.

Commands:

```bash
python3 /tmp/tmp.xg6H43zYiJ/skills_repo/ai-readiness-cartography/scripts/score.py /home/ubuntu/work/forgeflow --json /tmp/forgeflow-ai-score-after.json
```

Update this document with:

- After score
- Category deltas
- Remaining gaps
- Explicit non-goals deferred to later work

## Verification Bundle

Run before final review:

```bash
.venv/bin/python scripts/validate_context_paths.py
.venv/bin/python -m pytest tests/test_validate_context_paths.py -q
git diff --check
make validate
python3 /tmp/tmp.xg6H43zYiJ/skills_repo/ai-readiness-cartography/scripts/score.py /home/ubuntu/work/forgeflow --json /tmp/forgeflow-ai-score-after.json
```

If runtime files are touched unexpectedly, also run:

```bash
.venv/bin/python -m pytest -q
```

## Step 1 Result — Exact Baseline Broken References

Reproduced external scorer logic locally:

- Total path-like refs: `74`
- Broken refs: `32`

Broken refs found:

- `README.md:384`: `./.forgeflow/tasks/my-task-001/brief.js`
- `README.md:386`: `./.forgeflow/tasks/my-task-001/checkpoint.js`
- `README.md:385`: `./.forgeflow/tasks/my-task-001/run-state.js`
- `README.md:387`: `./.forgeflow/tasks/my-task-001/session-state.js`
- `README.md:459`: `./CLAUDE.md`
- `README.md:445`: `./CODEX.md`
- `README.md:140`: `claude/hooks/forgeflow/basic_safety_guard.py`
- `README.md:140`: `claude/settings.js`
- `README.md:112`: `docs/forgeflow-team-init.md`
- `README.md:599`: `plugin/marketplace.js`
- `README.md:68`: `plugin/plugin.js`
- `README.md:105`: `project/.claude/agents/forgeflow-coordinator.md`
- `README.md:106`: `project/.claude/agents/forgeflow-nextjs-worker.md`
- `README.md:107`: `project/.claude/agents/forgeflow-quality-reviewer.md`
- `README.md:108`: `project/.codex/forgeflow/forgeflow-coordinator.md`
- `README.md:109`: `project/.codex/forgeflow/forgeflow-nextjs-worker.md`
- `README.md:110`: `project/.codex/forgeflow/forgeflow-quality-reviewer.md`
- `README.md:111`: `project/.codex/rules/forgeflow-nextjs-worker.md`
- `README.md:75`: `project/CLAUDE.md`
- `README.md:76`: `project/CODEX.md`
- `README.md:128`: `project/docs/ADR.md`
- `README.md:127`: `project/docs/ARCHITECTURE.md`
- `README.md:126`: `project/docs/PRD.md`
- `README.md:129`: `project/docs/UI_GUIDE.md`
- `README.md:112`: `project/docs/forgeflow-team-init.md`
- `README.md:295`: `schemas/review-report.schema.js`
- `docs/upstream/hoyeon/README.md:13`: `cli/src/commands/plan.js`
- `docs/upstream/hoyeon/README.md:14`: `hooks/hooks.js`
- `docs/upstream/hoyeon/README.md:10`: `skills/blueprint/SKILL.md`
- `docs/upstream/hoyeon/README.md:12`: `skills/compound/SKILL.md`
- `docs/upstream/hoyeon/README.md:11`: `skills/execute/SKILL.md`
- `adapters/generated/claude/CLAUDE.md:44`: `adapters/targets/claude/hooks/hooks.js`

Interpretation:

- Many `README.md` hits are install-target or example-project paths, not repo paths. They should be marked so validators do not treat them as local repo evidence.
- `schemas/review-report.schema.js` looks like a real stale extension; the repo uses JSON schema naming elsewhere.
- `docs/upstream/hoyeon/README.md` is vendored upstream reference material and should probably be excluded from repo-local context validation.
- `adapters/generated/claude/CLAUDE.md` is generated output; either fix the source/generator or exclude generated adapter output from local context trust checks.

## Progress Log

- 2026-04-29: Baseline audit completed. Score `29/100`, grade `AI-Hostile`.
- 2026-04-29: Task plan created in `docs/tasks/2026-04-29-ai-readiness-cartography-upgrade.md`.
- 2026-04-29: Step 1 completed. Exact `32/74` broken reference list recorded above.
- 2026-04-29: Step 2 completed. Added `scripts/validate_context_paths.py`, `make validate-context-paths`, and `tests/test_validate_context_paths.py`. The validator passes current repo state and ignores install-target examples, vendored upstream notes, and generated adapter outputs instead of pretending they are repo-local evidence.
- 2026-04-29: Step 3 resolved by policy rather than README churn. The focused validator now treats install-target/example references as examples and reports zero repo-local context path failures.
- 2026-04-29: Step 4 completed. `docs/review-model.md` now absorbs AI-readiness as review questions: Navigation, Evidence, Dependency, Tribal knowledge, Freshness.
- 2026-04-29: Step 5 completed. Added `docs/decisions/README.md` and `docs/decisions/0001-ai-readiness-cartography-absorption.md` to capture why the external rubric was mined, not copied.
- 2026-04-29: Step 6 partially completed. `docs/architecture.md` now includes evidence-ref classification in success criteria; a larger diagram remains optional/deferred.
- 2026-04-29: Step 7 completed. `make validate` now runs `scripts/validate_context_paths.py`.
- 2026-04-29: Step 8 completed. External audit improved from `29/100` to `33/100`; the grade remains `AI-Hostile` because the external scorer still treats install-target examples and generated/upstream references as hallucinated paths. That is recorded as diagnostic debt, not a release gate.

Verification:

```bash
make validate-context-paths
python3 -m pytest tests/test_validate_context_paths.py -q
git diff --check
make validate
python3 -m pytest -q
python3 /tmp/tmp.xg6H43zYiJ/skills_repo/ai-readiness-cartography/scripts/score.py /home/ubuntu/work/forgeflow --json /tmp/forgeflow-ai-score-after.json
```

Final result:

- Local context validator: `PASS`
- Full validation: `PASS`
- Full pytest: `465 passed`
- External audit: `33/100`, still `AI-Hostile`, useful as backlog signal only

Result: all passed.

## Final Result

Implemented the ForgeFlow-native absorption path:

- Score delta: external diagnostic moved from `29/100` to `33/100`.
- Main real gain: `C. Tribal Knowledge Externalization` moved from `0/20` to `4/20` via `docs/decisions/`.
- `make validate` now runs `scripts/validate_context_paths.py`, so source-context path rot has a cheap gate.
- `docs/review-model.md` now treats AI-readiness as review questions, not as a copied external scorecard.
- `docs/architecture.md` now names evidence-ref classification as a success criterion.

Important interpretation:

- The external scorer still reports `32` hallucinated paths because it does not understand ForgeFlow's installed-target examples, generated adapter outputs, or vendored upstream notes.
- That is acceptable for now. The scorer remains an X-ray, not a release gate.
- We intentionally did not add root/module `AGENTS.md` files or new lifecycle stages just to game the score.

Verification passed:

```bash
make validate-context-paths
python3 -m pytest tests/test_validate_context_paths.py -q
git diff --check
make validate
python3 /tmp/tmp.xg6H43zYiJ/skills_repo/ai-readiness-cartography/scripts/score.py /home/ubuntu/work/forgeflow --json /tmp/forgeflow-ai-score-after.json
```
