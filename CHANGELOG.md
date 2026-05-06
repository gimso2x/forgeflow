# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.2] - 2026-05-06

### Added

- **Ouroboros handoff absorption**: documented ForgeFlow contract improvements from `docs/ouroboros-forgeflow-handoff.md`.
- **Runtime adapter boundary docs**: added `docs/runtime-adapters.md` to separate workflow contracts from execution backend capabilities.

### Changed

- **Clarify contract**: made Socratic clarification, ambiguity scoring, hidden assumptions, non-goals, and blocker/non-blocking question separation explicit.
- **Plan/review/run contracts**: strengthened requirement traceability, adapter limitation handling, blocker-first review evidence, and scoped execution discipline.
- **Route vocabulary**: pinned route labels to `small`, `medium`, and `large_high_risk` across coordinator prompts and generated Claude/Codex adapters.

### Fixed

- **Claude/Codex plugin smoke hardening**: stabilized Codex doctor artifact-policy checks, route-label exact-output checks, and non-mutating smoke validation.
- **Generated adapter validation**: normalized generated validation paths across platforms.
- **Windows CI stability**: removed POSIX-only assumptions from runtime fixture paths, plugin metadata path rendering, verification-pipeline tests, fake CLI execution, and PID liveness checks.
- **Codex smoke route labels**: prevented adapter/team-size synonyms such as `solo` from satisfying ForgeFlow route-label dry-runs.

### Validation

- Local: `python3 scripts/validate_generated.py` PASS before route-vocabulary generation update.
- Local: Claude/Codex plugin smoke matrix passed for `small`, `medium`, and `large_high_risk`.
- Local: `python3 scripts/validate_structure.py` PASS.
- Local: `python3 -m pytest -q` → 1217 passed.
- CI: `windows-smoke`, `repo-validation`, and `generated-drift` passed on `main` run `25386400965` before this release.

## [0.3.0] - 2026-05-05

### Added

- **Natural language plan generation**: `natural_language_plan.py` — generate plan drafts from free-form descriptions
- **Profile artifact CLI**: `forgeflow_profile.py` — inspect and export task profiles
- **Visual companion tooling**: `forgeflow_visual.py` + `visual-companion.cjs` — visual pipeline status rendering
- **Codex plugin doctor**: `codex_plugin_doctor.py` — diagnose and repair Codex plugin installations

### Fixed

- **Codex ForgeFlow flow contracts**: hardened worker verification and retry loop
- **Claude/Codex agent SKILL.md updates**: review gate, run-state discipline improvements

### Removed

- Cleaned up 7 stale backup/rebuild local branches
- Deleted 3 merged/unused remote branches

## [0.2.1] - 2026-05-04

### Fixed

- **Review gate hardening**: Added Test verification gate to review SKILL.md — reviewer must run test suite independently, test failures force `changes_requested` verdict, pass/fail counts recorded in evidence
- **Run-state discipline**: Added progress/timestamp rules to run SKILL.md — `progress.percentage` must be recalculated on each write, timestamps must be real ISO 8601 (not placeholder zeros)

## [0.2.0] - 2026-05-04

### Added

**Execute Intelligence (#87)**
- `execute_intelligence.py`: execution context tracking, progress estimation, stuck detection
- 24 tests

**Multi-Model Orchestration (#88)**
- `orchestra.py`: consensus, debate, pipeline, fastest strategies for multi-model coordination
- 52 tests (largest test suite)

**RALF Self-Healing Gate Loop (#89)**
- `gate_ralf.py`: RED→GREEN→REFACTOR→LOOP cycle with automatic recovery
- 21 tests

**Token Budget & Telemetry (#90)**
- `cost.py`: token budget enforcement per stage
- `telemetry.py`: pipeline telemetry JSONL logging
- 48 tests combined

**Adaptive Task Complexity (#91)**
- `complexity.py`: weighted scoring (file count, risk keywords, LOC, requirements) + route selection
- 28 tests

**Constraint Scanning Gate (#92)**
- `constraint_checker.py`: regex-based anti-pattern and quality scanning
- 36 tests

**Automated Experiment Loop (#93)**
- `experiment.py`: metric-driven iteration with circuit breaker (XLOOP)
- 42 tests

**EARS Requirements Parser (#96)**
- `ears_parser.py`: 5 EARS patterns (ubiquitous, event-driven, optional, stateful, undesirable) + Korean support
- 24 tests

**Verification-Driven Pipeline (#74)**
- `verify_pipeline.py`: verify→fix loop + spec review gate + max attempts + summarization
- 13 tests

**Cross-Model Adversarial Review (#79)**
- `adversarial_review.py`: dual reviewer with agreement scoring + tiebreaker
- 10 tests

**Feedback Routing (#75)**
- `feedback_router.py`: CI/PR/user events → task worker auto-routing with retry budget
- 16 tests

**Execution Crystallization (#80)**
- `crystallization.py`: success path → soft/hard rule promotion via pattern extraction
- 28 tests

**Lightweight Mode (#64)**
- `lightweight_mode.py`: SKILL.md-only fallback when runtime unavailable (SOFT/HYBRID/HARD enforcement)
- 17 tests

**Anti-Rationalization Checklists (#65)**
- `anti_rationalization.py`: 10 Red Flags patterns across 5 stages (clarify/plan/review/run/verify)
- 11 tests

**Semantic Versioning & Changelog (#67)**
- `versioning.py`: SemVer parsing/bumping, commit-based version suggestion, Keep a Changelog formatting
- 20 tests

**Evolution Case Logger (#72)**
- `evolution_cases.py`: case recording, impact summarization, README section generation
- 13 tests

### Stats

- **14 new modules** in `forgeflow_runtime/`
- **44 new test functions** (948 → 1077 total)
- **3 new evolution test files** (audit, doctor, effectiveness, promotion pipeline)
- Closes issues: #64, #65, #67, #72, #74, #75, #79, #80, #87, #88, #89, #90, #91, #92, #93, #96

## [0.1.27] - 2026-05-03

### Changed
- AI readiness cartography absorbed into docs

## [0.1.26] - 2026-05-03

### Fixed
- Incremental run state updates (#60)

## [0.1.25] - 2026-04-29

### Fixed
- ForgeFlow review gate workflow (#58)

## [0.1.24] - 2026-04-28

### Added
- Windows and Codex plugin install support (#62)

## [0.1.22] - 2026-04-28

### Fixed
- Home path context validation (#63)

## [0.1.13] - 2026-04-24

### Added
- Initial release with canonical 5-stage workflow (clarify → plan → run → review → verify)
- Evolution engine (8 modules)
- CI gate with GitHub Actions workflow generation
- Agent preset installer (Claude + Codex)
