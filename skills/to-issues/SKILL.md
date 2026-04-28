---
name: to-issues
description: Convert an approved ForgeFlow plan into traceable issue draft artifacts without publishing them.
---

# Skill: to-issues

## Purpose

Turn an approved `plan.json` into vertical, issue-ready draft slices while preserving ForgeFlow artifact authority.

## Trigger

Use this skill when:

- the user asks to split a plan into backlog issues;
- a plan has multiple independently verifiable vertical slices;
- human-gated and agent-ready chunks need to be separated before execution;
- a GitHub publication adapter needs a safe draft bundle.

Do not use it for one-file or one-step tasks.

## Input Artifacts

| Artifact | Source |
|----------|--------|
| `plan.json` | Required. Approved plan from `plan`. |
| `brief.json` | Optional. Context and acceptance criteria from `clarify`. |
| `contracts.md` | Optional. Contract boundaries referenced by the plan. |
| publication metadata | Optional adapter data: target repo, labels, milestone. |

## Output Artifacts

| Artifact | Schema | Description |
|----------|--------|-------------|
| `issue-drafts.json` | `schemas/issue-drafts.schema.json` | Machine-readable draft issue bundle. |
| `issue-drafts.md` | none | Human-readable issue bundle when JSON is overkill. |
| `decision-log.json` entry | `schemas/decision-log.schema.json` | Optional staleness or markdown-only decision note. |

## Procedure

1. Confirm the source plan is approved enough to slice. If approval is missing, stop and report the missing review evidence.
2. Read `plan.json.steps[]`, `verify_plan`, optional `brief.json`, and optional `contracts.md`.
3. Group steps into vertical slices. Prefer one externally reviewable outcome per draft.
4. Reject horizontal chores unless they unblock a vertical slice and include explicit trace or discovery justification.
5. For each issue draft, assign a stable id: `draft-<short-kebab-name>`.
6. Copy trace links from plan step ids, `fulfills`, and stable contract anchors. Do not invent contract anchors.
7. Derive acceptance checks from plan intent. Do not add net-new acceptance requirements.
8. Derive verification expectations from the plan and contracts.
9. Mark `human_gate: required` only when a human answer or artifact is genuinely needed.
10. For discovery drafts, include the question, evidence to gather, artifact to produce, and decision unblocked.
11. Write `issue-drafts.json` when publication or automation is possible. Otherwise write `issue-drafts.md` and add a decision note explaining why markdown is enough.
12. Validate JSON output against `schemas/issue-drafts.schema.json` when present.

## Constraints

- Default to **artifact-first mode**.
- Never write inside the plugin installation directory, marketplace cache, or global config unless the user explicitly asks for a dry run there.
- Write task artifacts under `.forgeflow/tasks/<task-id>/` unless the caller provides a project-local artifact directory.
- `plan.json` owns scope, decomposition, and acceptance intent.
- `contracts.md` owns interface, compatibility, and invariant constraints.
- Issue drafts are derived artifacts. They cannot become a second plan.
- `AFK` and `HITL` are upstream commentary only. Do not use them as artifact values.
- GitHub labels, milestones, and target repo are adapter metadata, not core identity.
- Do not call the GitHub API. Publishing is a separate explicit adapter action.
- Redact credentials as `[REDACTED]`.

## Exit Condition

The skill is complete when:

- `issue-drafts.json` validates against `schemas/issue-drafts.schema.json`, or a markdown-only decision note exists;
- every non-discovery draft traces to at least one plan step;
- every discovery draft includes question, evidence, artifact, and unblocked decision;
- every draft has acceptance checks and verification expectations;
- no draft adds scope beyond the source plan without an explicit decision-log entry;
- the final response names the written artifact path and says whether publication was skipped.

## Notes

Design details live in `docs/to-issues-model.md`.
