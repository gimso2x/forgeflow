# Context Brief

<!-- ForgeFlow brief template. Fill each section during clarify. -->

## Objective
<!-- One-sentence description of what this task accomplishes -->

## Route
<!-- small | medium | high | epic -->
<!-- Route sub-band (medium only): medium-light | medium-full — from brief.md raw_score -->
<!-- Route rationale: why this route is sufficient and smallest safe choice -->

## Route Rationale
<!-- Evidence behind route selection: scope, risk, dependencies, rollback, ambiguity -->

## Route Sub-band
<!-- medium-light (10-16.9) | medium-full (17-24.9) | n/a for other routes -->

## WHERE Grounding
<!-- Project context for calibrating intake depth -->
- **Project type**: <!-- user-facing app | API/service | dev tool/library | infrastructure -->
- **Situation**: <!-- greenfield | brownfield extension | brownfield refactor | hybrid -->
- **Ambition**: <!-- toy/experiment | feature/MVP | product -->

## In Scope
-

## Out of Scope
-

## Constraints
-

## Acceptance Criteria
- [ ]

## Risk Level
<!-- low | medium | high | critical -->

## Risk Modifiers
<!-- Check all that apply -->
- [ ] Sensitive data
- [ ] External exposure
- [ ] Irreversible operations
- [ ] High scale

## Ambiguity Score
<!-- 0.0 to 1.0. Above 0.2 requires blocker resolution or bounded assumptions. -->

## Assumptions
<!-- Bounded assumptions for non-blocking unknowns -->
-

## Applied Evolution Rules
<!-- Rules loaded during clarify. Project active rules are required; global rules are advisory. -->
- **Project active rules**: <!-- .forgeflow/evolution/active/*.md that matched -->
- **Global advisory rules**: <!-- ~/.forgeflow/evolution/active/*.md that matched -->
- **Ignored rules**: <!-- rules checked but not applicable, with reason -->

## Open Questions
<!-- Blockers that must be resolved before proceeding -->
-

## Specialists
<!-- Required: (none | security-review | ux-review | perf-review | frontend-execute | backend-execute | infra-execute) -->
<!-- Suggested specialists: advisory candidates from request keywords and repo context -->
<!-- Skipped: (none | list) -->
<!-- Skip rationale: -->

## Budget Note
<!-- Advisory only: expected size/complexity, e.g. small single-file, medium coordinated files, high multi-component, epic milestone-scale -->

## Suggested Next Skill
<!-- /forgeflow:execute | /forgeflow:plan | /forgeflow:milestone | /forgeflow:review | /forgeflow:ship -->

## Verification Gates
<!-- Auto-detected from tech stack -->
- [ ]

## Min Verification
<!-- small: build|lint|type_check (fastest available) -->
<!-- medium: lint + type_check + test (if exists) -->
<!-- high: build + lint + type_check + test -->
<!-- epic: full suite + milestone integration tests -->

## Environment Preflight
<!-- git repo status, lockfile/dependency check, etc. -->
