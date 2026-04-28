# External Skill Ingestion Model

Date: 2026-04-29
Status: Adopted guidance
Source example: `jha0313/skills_repo`

## Purpose

ForgeFlow can learn from external skill repositories, but it must not import their command surface wholesale. Ingestion means extracting reusable discipline into ForgeFlow's existing stages, artifacts, and review gates.

The useful pattern from `jha0313/skills_repo` is not "more skills". It is **script-backed scoring + rubric-backed interpretation + operator-readable artifacts**.

## Ingestion rule

Before absorbing an external skill, classify it into one of three lanes:

| Lane | Meaning | ForgeFlow action |
|------|---------|------------------|
| Adopt | Directly strengthens an existing stage or artifact | Patch the relevant skill/doc/schema sample |
| Adapt | Useful idea, wrong surface | Translate into a ForgeFlow-native rubric/checklist/model doc |
| Archive | Interesting, not workflow-critical | Record in docs or wiki only |

A change is not eligible for `Adopt` if it creates a new required source of truth, runtime state, approval checkpoint, or persistence lane.

## Evaluation checklist

Each candidate skill must answer these questions before implementation:

1. **What artifact gets better?** Name the existing ForgeFlow artifact: `brief`, `contracts`, `plan`, `run-state`, `review-report`, `eval-record`, `issue-drafts`, or decision log.
2. **What stage gets clearer?** Name the existing stage. If the answer needs a new stage, default to `Adapt`, not `Adopt`.
3. **What is machine-checkable?** Prefer stdlib scripts, schema checks, path validation, or deterministic scoring over vibes.
4. **What is manual judgment?** Keep manual rubric items explicit instead of pretending automation saw everything.
5. **What is the smallest vertical slice?** Absorb one P0 rule first; do not dump a whole foreign workflow into ForgeFlow.
6. **What could drift?** Identify stale paths, stale scoring constants, external pricing assumptions, or UI templates.
7. **What evidence proves it worked?** Require a command, generated artifact, or diff-scoped review evidence.

## Patterns worth absorbing from `jha0313/skills_repo`

### 1. Token-efficiency analysis

`improve-token-efficiency` parses Claude Code JSONL sessions, computes cost/cache/tool/read-redundancy metrics, and renders a dashboard. ForgeFlow should treat this as an **operator telemetry pattern**, not a core runtime dependency.

Good absorption targets:

- long-run learning: measure tool calls, repeated reads, compaction points, and rework cost;
- review quality: detect evidence-free claims by requiring durable logs/artifacts;
- future eval records: store token/tool economy summaries when available.

Do not hardcode Claude pricing or Claude-only session paths into ForgeFlow core.

### 2. AI-readiness cartography

`ai-readiness-cartography` uses a 100-point A-G rubric with mixed auto/manual scoring. The strongest idea is the separation of **automatic evidence** from **manual judgment**, especially path hallucination checks.

Good absorption targets:

- `review` evidence policy: referenced paths must exist;
- `to-issues` readiness: agent-ready drafts need trace, acceptance checks, and verification expectations;
- repo onboarding: a future optional audit can score navigation, context freshness, dependency maps, and validation gates.

Do not turn AI-readiness into a mandatory release gate.

### 3. Presentation slides

`presentation_slides` is less relevant to ForgeFlow execution, but its artifact pattern is strong: fixed template, layout catalog, navigation rules, and explicit output checklist.

Good absorption targets:

- generated report/dashboard artifacts should use stable templates instead of one-off visual improvisation;
- docs that produce human-facing bundles should name layout choices and checklist rules.

Do not add presentation generation to the core workflow.

## ForgeFlow-native mapping

| External pattern | ForgeFlow owner | Absorption level |
|------------------|-----------------|------------------|
| Session/token efficiency scoring | `docs/long-run-model.md`, future eval artifacts | Adapt |
| Path hallucination detection | `docs/review-model.md`, validation scripts | Adopt |
| A-G readiness rubric | optional repo audit model | Adapt |
| ROI-ranked action list | `docs/tasks/*` backlog format | Adapt |
| Fixed HTML template discipline | generated reports/dashboards only | Archive/Adapt |

## Non-goals

- No `/forgeflow:ingest` command.
- No new required stage.
- No vendoring external skill scripts into runtime core without a separate design decision.
- No external repository becoming a source of truth for ForgeFlow policy.
- No Claude-only telemetry assumption in adapter-neutral policy.

## One-line policy

External skills are quarry, not architecture. Mine the stone; do not move into the quarry.
