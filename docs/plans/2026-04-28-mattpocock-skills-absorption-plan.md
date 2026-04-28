# Matt Pocock Skills → ForgeFlow Absorption Design

Date: 2026-04-28
Status: Cross-reviewed draft, revised after Claude/Codex review
Source: https://github.com/mattpocock/skills, inspected from fresh shallow clone on 2026-04-28
Review evidence:
- Claude Code review: `/tmp/claude-forgeflow-matt-review.log`
- Codex review attempt 1: `/tmp/codex-forgeflow-matt-review.log` could not read local files
- Codex review attempt 2: full artifacts pasted via stdin; process timed out after returning repeated substantive findings

> Do not import `mattpocock/skills` as a parallel workflow system. ForgeFlow already has the stronger core skeleton. Absorb only the operator patterns that strengthen artifact-first planning, issue decomposition, contract design, and review discipline.

## Executive decision

`mattpocock/skills` is a useful operator prompt library, not an architecture ForgeFlow should copy.

ForgeFlow should absorb four things:

1. `to-issues` style vertical backlog slicing.
2. `design-an-interface` style interface-option exploration, translated into contract-first artifacts.
3. `request-refactor-plan` style tiny safe refactor planning, translated into the existing `plan` skill.
4. Selected issue/triage and git-safety heuristics, translated into review/model policy language.

ForgeFlow should reject these as first-class workflow surfaces:

1. Standalone TDD ritual command.
2. Conversational QA session as a product surface.
3. `grill-me` as a productized stage.
4. Claude-specific git hook setup as canonical ForgeFlow behavior.
5. PRD generation as a mandatory stage.

Short version: steal the good knives, not the whole kitchen.

## Current ForgeFlow fit

ForgeFlow already has the important pieces that `mattpocock/skills` mostly leaves to convention:

- canonical stage flow: `clarify -> plan -> run -> review -> ship`
- artifact-first behavior
- JSON schemas for durable outputs
- generated adapter boundaries
- validation targets
- review evidence discipline
- stage transition gates

That means the absorption model must be translation, not import.

## Source inventory

Fresh clone contained these relevant skills:

- `to-issues`
- `design-an-interface`
- `request-refactor-plan`
- `to-prd`
- `github-triage`
- `triage-issue`
- `git-guardrails-claude-code`
- `tdd`
- `qa`
- `grill-me`
- `domain-model`
- `ubiquitous-language`
- `zoom-out`

Representative source patterns:

- `to-issues`: tracer-bullet vertical slices, HITL/AFK labels, dependency ordering, GitHub issue publication.
- `design-an-interface`: generate multiple materially different interface options, compare trade-offs, choose intentionally.
- `request-refactor-plan`: inspect, verify current coverage, split refactor into small always-green steps.
- `to-prd`: synthesize PRD and user stories; useful only for larger product-facing tasks.
- `github-triage` / `triage-issue`: labels, ready-for-agent state, root-cause-oriented issue filing.
- `git-guardrails-claude-code`: destructive git operation paranoia, but implemented as Claude-specific hooks.
- `tdd`: behavior-first tests and vertical red-green cycles; good discipline, bad as a new mandatory surface.
- `domain-model` / `ubiquitous-language`: terminology hardening; useful only if ForgeFlow later adds product/domain-heavy routes.

## Absorption principles

### 1. No new canonical stages

Do not add `/forgeflow:to-issues`, `/forgeflow:prd`, `/forgeflow:tdd`, or `/forgeflow:grill` as core stages.

Optional skills are fine only if they are subordinate to existing stages. Optional-but-detached is still a shadow workflow.

### 2. Every imported behavior must land in one of five existing surfaces

Allowed surfaces:

- `skills/*/SKILL.md`
- `docs/*-model.md` or `docs/*-decision.md`
- `schemas/*.schema.json` and sample artifacts, if the output is durable enough
- review/model policy language owned by docs, summarized by skills
- `docs/tasks/*.md` backlog slices

### 3. Artifacts beat conversation style

A pattern is worth productizing only if it improves a durable artifact or validation rule:

- `plan.json`
- `contracts.md`
- `issues.json` or markdown issue bundle
- `review-report.json`
- decision docs
- validation scripts

If the pattern only changes the vibe of the chat, leave it as operator behavior.

### 4. Cross-agent language only

ForgeFlow supports Claude and Codex surfaces. Do not canonize Claude Code-specific hook names, settings paths, or command theology. Extract safety intent, not tool wrapper ceremony.

### 5. Artifact authority is explicit

Derived artifacts must never quietly become new requirements sources.

Authority rule:

- `plan.json` owns scope, decomposition, and acceptance intent.
- `contracts.md` owns boundary, interface, compatibility, and invariant constraints.
- issue drafts are derived execution artifacts; they may not add net-new acceptance requirements without an explicit decision note.
- review artifacts judge evidence against the authoritative plan and contract artifacts; they do not redefine scope.

Staleness rule:

- if a traced `plan.json` step, `fulfills` link, or contract section changes, the issue bundle must be regenerated or explicitly marked stale.

Trace target rule:

- `plan.json.steps[].id` is the stable plan trace target.
- `contracts.md` needs stable headings or section IDs before issue drafts can claim durable contract traceability.

### 6. Policy ownership is explicit

Normative policy belongs in model/decision docs. Skills may summarize or apply it, but must not redefine it.

Preferred ownership:

- `docs/to-issues-model.md` owns issue-readiness and issue artifact semantics.
- `docs/review-model.md` or a focused decision doc owns review/git-safety semantics.
- `skills/*/SKILL.md` references those docs and gives operating procedure.

## Recommended design

### A. Add optional `to-issues` support skill

Purpose: turn an approved plan into issue-ready backlog slices.

Why: This is the highest-value import. ForgeFlow is artifact-first, but teams still need execution-sized backlog chunks. `to-issues` is the bridge.

ForgeFlow-native behavior:

- input: approved `plan.json`; optional `brief.json`, `contracts.md`, and publication adapter metadata
- output: either schema-backed `issues.json` plus sample, or markdown issue bundle plus a decision note explaining why schema is unnecessary
- each issue maps back to `plan.json.steps[].id` and `fulfills`
- contract links use stable `contracts.md` headings/anchors when available
- each issue includes derived acceptance checks and verification evidence expectations
- upstream HITL/AFK becomes ForgeFlow-native gating metadata, not imported vocabulary
- GitHub publication remains a separate explicit action

Gating model:

- use a ForgeFlow-native field such as `human_gate: required|not_required`
- optional detail may name the blocking human answer/artifact
- do not encode `AFK`/`HITL` as artifact values

Applicability threshold:

- use this skill only when a plan needs multiple independently verifiable slices or a publication-ready backlog bundle

Discovery issue rule:

- discovery-only issues must name the question, evidence to gather, artifact to produce, and decision unblocked

Do not:

- create GitHub issues automatically during planning
- replace `plan` with issue decomposition
- make issue creation mandatory for small tasks
- make GitHub labels/milestones part of the core artifact identity

### B. Add optional `design-interface` support skill

Purpose: harden interface-heavy work before implementation by comparing multiple interface shapes.

Why: ForgeFlow already has contract traceability in `plan`. This pattern makes that contract step less hand-wavy.

ForgeFlow-native behavior:

- the skill is used inside clarify/plan work and feeds `contracts.md` and/or `plan` artifacts
- default output is a `contracts.md` section
- use `interface-spec.json` only if a contract schema already exists or this task explicitly creates one through a decision
- require at least two materially different designs for non-trivial boundaries
- compare simplicity, depth, compatibility, testing surface, migration risk
- select one design and record rejected alternatives

Applicability threshold:

- use this skill for externally consumed, migration-sensitive, compatibility-sensitive, or ambiguity-heavy boundaries
- skip for obviously local changes already constrained by existing patterns

Do not:

- spawn a new top-level stage
- create a separate approval checkpoint
- force parallel agents for every tiny interface decision
- produce interfaces detached from existing repo patterns

### C. Fold refactor planning into `skills/plan/SKILL.md`

Purpose: make refactors safer without adding a new refactor workflow.

Why: Refactor work has special risks: behavior drift, migration ambiguity, rollback gaps, and tests that accidentally assert internals.

Refactor-mode entry criteria:

- behavior-preserving structural change across an existing public surface
- migration-sensitive internal reorganization
- test-sensitive decomposition work
- removal/replacement of implementation machinery while preserving user-visible behavior

ForgeFlow-native behavior:

When the task enters refactor mode, `plan` should require:

- preserved public behavior statement, or a decision explaining why the refactor is internal-only
- migration boundary
- rollback, escape hatch, or explicit not-applicable note for contained internal refactors
- tiny always-green step sequence
- regression verification strategy
- explicit non-goals
- note on whether existing tests cover affected public behavior

Representation rule:

- every refactor-specific requirement must map to an existing artifact field or a named markdown section
- if no canonical representation exists, stop and write a schema/decision note before burying requirements in prose

Do not:

- create `/forgeflow:refactor-plan` yet
- turn every refactor into an essay
- let tiny-commit language override artifact schema constraints

### D. Add issue-readiness and triage language as docs/policy, not runtime

Purpose: make backlog issues better for human or agent execution.

Useful imports:

- agent-ready / human-gated distinction expressed in ForgeFlow-native terms
- dependency-aware issue ordering
- root-cause vs symptom separation
- public behavior oriented bug reports
- issue bodies that avoid stale implementation line references unless the task is explicitly code-local

ForgeFlow-native behavior:

- document issue readiness in `docs/to-issues-model.md`
- use it in `to-issues` output expectations
- avoid a label state machine in core runtime
- Issue 4 should depend on or reference Issue 1's canonical model rather than redefine readiness semantics

### E. Absorb git guardrails as review discipline only

Purpose: preserve safety instincts without adapter lock-in.

Cross-agent language to keep:

- never stage broad unrelated diffs
- name exact diff scope under review
- verify before commit
- destructive git commands require explicit user approval
- preserve user work in dirty trees

Do not import:

- Claude Code hook implementation as canonical ForgeFlow product behavior
- global settings mutation
- hardcoded `.claude` paths in core docs
- a new `safe-commit` skill unless that surface already exists and is explicitly part of the product model

### F. Defer PRD and domain-language support

`to-prd`, `domain-model`, and `ubiquitous-language` are useful, but they should not be first-wave imports.

Recommended stance:

- PRD transformation is optional for large product tasks only.
- Domain glossary is optional for DDD/product-heavy repos only.
- Neither belongs in the canonical stage chain today.

## Backlog slices

This design should become four backlog issues, not one blob:

1. Add ForgeFlow-native `to-issues` draft artifact model.
2. Add contract-first `design-interface` support skill.
3. Add refactor-mode branch to `plan` guidance.
4. Add issue-readiness and git-safety policy language.

The slices are deliberately vertical and reviewable. They avoid runtime changes unless later evidence demands schema validation for `issues.json`.

## Acceptance criteria for the absorption

- No new canonical ForgeFlow stage is introduced.
- Existing `clarify -> plan -> run -> review -> ship` docs remain the source of truth.
- New skills, if added, declare input artifacts, output artifacts, applicability threshold, and exit conditions.
- New support skills produce or govern artifacts consumed by existing stages.
- No new required runtime state, source of truth, approval checkpoint, or persistence lane is introduced.
- Any new durable artifact has either a schema/sample or a clear decision saying why markdown is enough.
- Derived artifacts have authority and staleness rules.
- GitHub publication remains opt-in and explicit.
- Claude-specific implementation details do not leak into cross-agent core docs.
- Validation remains cheap: markdown lint/skill validation first; runtime tests only if code changes.

## Stop rules

Stop and write a decision note before proceeding if:

- a proposed import needs a new runtime state
- a proposed import needs a new canonical stage
- a proposed import cannot name its durable artifact
- a proposed import cannot name the authoritative source artifact it derives from
- a proposed import lacks a staleness/invalidation rule for derived output
- a proposed import is only useful for Claude Code
- a proposed import duplicates `plan` or `review` instead of strengthening them

## Cross-review summary

Claude Code verdict:

- no blockers
- recommended clarifying issue artifact format, refactor-specific checks, Issue 4 file priority, and contract compliance in `design-interface`

Codex verdict:

- strategy is correct, but backlog needed tighter artifact governance before implementation
- key blockers: AFK/HITL vocabulary leak, missing artifact authority, missing staleness rule, unresolved output format, stage-leak risk for `design-interface`, undefined refactor-mode trigger, Issue 4 policy ownership ambiguity

This revision accepts Codex's stricter review. Claude was right that the design direction is sound; Codex was right that boundary slop here would grow a second workflow by accident. Boundary slop is where workflow systems go to die.

## Final recommendation

Proceed with the four backlog issues after the revised boundary rules above.

Do not directly copy the upstream skills into ForgeFlow. Rewrite them in ForgeFlow language, tied to artifacts, schemas, validation, and existing stages. The upstream repo is good prompt compost. ForgeFlow should grow stronger plants, not transplant the weeds too.
