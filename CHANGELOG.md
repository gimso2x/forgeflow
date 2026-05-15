# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.11.1] - 2026-05-15

### Fixed

- `brief.json`의 `required_specialists` 기반 에이전트/스킬 자동 생성 기능 수정.
- `scripts/check_versions.py`에 `gemini-extension.json` 확인 로직 추가 및 정규식 개선.

## [0.11.0] - 2026-05-15

### Added

- **동적 실행 환경 감지**: `GEMINI_CLI` 및 `CLAUDE_CODE` 환경 변수를 감지하여 실행 중인 플랫폼(Gemini vs Claude)에 맞는 경로(`.gemini/` vs `.claude/`)와 메타데이터 파일(`GEMINI.md` vs `CLAUDE.md`)을 자동으로 생성하도록 개선.
- **한국어 로컬라이징**: 오케스트레이터의 모든 안내 메시지 및 `next_action`을 자연스러운 한국어로 변경.
- **Task ID 자동화**: 한국어 목표 입력 시에도 타임스탬프(`task-YYYYMMDD-HHMMSS`)를 활용해 고유한 Task ID를 자동으로 생성하는 기능 추가.
- **고급 품질 정제 루프**: `ship` 스킬에 Claude Code의 `/simplify` 철학(3중 렌즈 분석, 주석 보존, 수렴 반복)을 이식하여 최종 코드 품질 강화.

### Fixed

- Gemini CLI 환경에서 `.claude/` 폴더가 생성되던 플랫폼 미스매치 문제 수정.
- 한국어 메시지 변경에 따른 런타임 테스트 코드의 기대값 최신화.

## [0.10.0] - 2026-05-14

### Added

- `epic` route 추가 (#140).
- `milestone` stage 및 관련 에이전트/스킬 추가.
- Massive scope 작업을 위한 마일스톤 기반 분할 워크플로우 지원.

### Changed

- `Route model`을 4단계(small, medium, high, epic)로 확장.
- `orchestrator` 로직을 epic route 및 milestone stage에 맞춰 업데이트.

## [0.9.0] - 2026-05-14

### Added

- Gemini 어댑터 익스텐션 지원 추가 (#131).
- Gemini CLI 익스텐션용 bootstrap 및 환경 검증 지원.

### Changed

- Gemini 익스텐션 bootstrap 로직을 기존 워크플로우와 정렬.

## [0.8.1] - 2026-05-14

### Added

- Add `plan.steps[].source` provenance for natural-language plan drafts.
- Add `dry_run` to execution payloads so stub and real adapter runs are explicit.

### Changed

- Migrate artifact schema version from 0.1 to 0.2 with backward-compatible auto-migration (#129).
- Add `validate_and_migrate` mode: 0.1 artifacts silently upgraded on load.
- Implement `_migrate_0_1_to_0_2`: brief gains specialist fields, review-report gains review_roles.
- Document current artifact schema ownership and keep plugin install/release docs aligned with v0.8.1.

### Fixed

- Enforce specialist require/skip decisions and skip rationales for new brief artifacts while preserving legacy compatibility.
- Preserve validated gate payloads during stage gate evaluation.
- Persist execute worktree cleanup state before writing route artifacts.

## [0.8.0] - 2026-05-13

### Added

- Wire specialist agents into runtime execution path (#135).
- `DOMAIN_TO_STAGE` mapping: security→security-review, backend→backend-execute, frontend→frontend-execute, infra→infra-execute, ux→ux-review, perf→perf-review.
- `specialists_from_brief()` now handles both domain names and stage names.
- 6 specialist prompt files in `prompts/canonical/` (security-reviewer, ux-reviewer, perf-reviewer, frontend-worker, backend-worker, infra-worker).
- 48 TDD tests for specialist wiring in `tests/runtime/test_specialist_wiring.py`.
- Real plugin E2E harness in `scripts/real_plugin_e2e.py`.

### Changed

- `ROLE_TO_FILENAME` now covers 11 roles (added 6 specialist agents) in both `generator.py` and `preset_resolver.py`.
- Codex `plugin.json` supports 6 specialist agents in `supports_roles` and `agents`.
- `operator_routing.py` gains `_normalise_specialist()` for domain→stage conversion.
- Route terminology cleanup: "high risk" → "high" in docs.

### Stats

- **1541 tests passed**, 0 failed.

## [0.7.5] - 2026-05-13

### Added

- Standalone review entrypoint: review without full pipeline via review-input.json normalization.
- `schemas/review-input.schema.json` with mode (pipeline|standalone), brief, evidence, target_scope, review_roles.
- `review_roles` enum: spec-review, quality-review, security-review, ux-review.
- 2-axis specialist agent selection — spec-based routing for Claude and Codex adapters.
- Specialist agent definitions (spec-reviewer, quality-reviewer, etc.) per target agent.
- AI-team handoff contract tests + handoff documentation.
- 5 new schema migration tests (0.1→0.2 for brief, review-report, generic, preserve, fixtures).

### Changed

- Extended review-report schema with security/ux review types and blockers field.
- Enriched 30 review-report fixtures with evidence_refs, next_action, blockers.
- Updated canonical prompts (spec-reviewer, quality-reviewer) for standalone review roles.
- Updated adapter docs (Claude/Codex) for standalone review input rules.
- Refreshed generated adapter prompts and runtime module map.
- Split evolution runtime into subpackage.
- Opt into GitHub Node 24 actions runtime.

## [0.7.4] - 2026-05-11

### Changed

- Absorbed Karpathy engineering discipline heuristics into docs.

### Fixed

- Hardened plugin route label smoke tests.
- Refreshed generated adapter prompts.
- Aligned execute command naming convention.
- Documented Claude worktree run preference.
- Ask before execute worktree isolation.

## [0.7.3] - 2026-05-11

### Fixed

- Plugin route label smoke hardening (continued).

## [0.7.2] - 2026-05-11

### Changed

- Refreshed generated adapter prompts.

### Fixed

- Aligned execute command naming.
- Documented Claude worktree run preference.

## [0.7.1] - 2026-05-11

### Fixed

- Ask before execute worktree isolation.

## [0.7.0] - 2026-05-11

### Added

- Optional worktree isolation for execute stage.

## [0.6.1] - 2026-05-11

### Added

- Korean output directives — generator and all agent prompts/adapters.

### Changed

- Renamed route `large_high_risk` to `high` for consistency.
- Split `init_task` into slim init + `clarify_task`.
- Separated init (scaffold-only) from clarify (heavy analysis).

### Fixed

- Hardened init skill — never ask user for missing args.
- `/forgeflow:init` now fully auto-inferable — objective, task-id, risk all optional.

## [0.5.1] - 2026-05-10

### Added

- TanStack Start detection + route field in brief.json.
- Domain-specific agents/skills (harness-100 style).
- Objective-only init — auto-infer task-id (slug) and risk (keyword analysis).
- Antigravity instruction adapter.
- Harness absorption sample surface.

### Changed

- Bumped plugin version 0.3.2 → 0.4.0 → 0.4.1 → 0.5.0 → 0.5.1.

### Fixed

- Agents/skills written to project root instead of task dir.
- Init skill no longer prompts when args provided.
- Corrected version 0.4.0 → 0.5.1 (was mistakenly downgraded).

## [0.4.0] - 2026-05-08

### Added

- **Domain analysis engine**: `_analyze_objective_domain()` detects 8 domain categories (api, frontend, backend, data, auth, infra, testing, security), 5 tech stacks (python, javascript, typescript, go, rust), and 6 change types (feature, bugfix, refactor, migration, security, testing) from objective text.
- **Project type detection**: `_detect_project_type()` scans filesystem markers to identify Next.js, React, FastAPI, Django, Flask, Express, Go, Rust, and Python CLI projects.
- **Domain-aware init drafts**: PRD, ARCHITECTURE, and QA drafts now include domain-specific considerations, architecture advice, and QA checklists based on detected domains and change type.
- **Project-aware init drafts**: init drafts include framework-specific guidelines when a project type is detected.
- **Domain analysis tests**: `test_domain_analysis.py` (21 tests) covering domain detection, consideration generation, QA checklist, and integration with init.
- **Project type detection tests**: `test_project_type_detection.py` (17 tests) covering marker scanning, framework identification, and consideration generation.

### Changed

- **Agent templates**: restructured from 1-2 line summaries to Role/Responsibilities/Input Artifacts/Output Artifacts/Collaboration Rules/Error Handling (4 agents).
- **Skill templates**: restructured from 1-2 line summaries to Trigger/Procedure(6-7 steps)/Exit Criteria/References (4 skills).
- **harness absorption handoff**: updated to reflect completed domain analysis and project type detection milestones.

### Fixed

- **Data domain detection**: added mysql, postgres, sqlite keywords to data domain signals.

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

[Unreleased]: https://github.com/gimso2x/forgeflow/compare/v0.10.0...HEAD
[0.10.0]: https://github.com/gimso2x/forgeflow/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/gimso2x/forgeflow/compare/v0.8.1...v0.9.0
[0.8.1]: https://github.com/gimso2x/forgeflow/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/gimso2x/forgeflow/compare/v0.7.5...v0.8.0
[0.7.5]: https://github.com/gimso2x/forgeflow/compare/v0.7.4...v0.7.5
[0.7.4]: https://github.com/gimso2x/forgeflow/compare/v0.7.3...v0.7.4
[0.7.3]: https://github.com/gimso2x/forgeflow/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/gimso2x/forgeflow/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/gimso2x/forgeflow/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/gimso2x/forgeflow/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/gimso2x/forgeflow/compare/v0.5.1...v0.6.1
[0.5.1]: https://github.com/gimso2x/forgeflow/compare/v0.4.0...v0.5.1
[0.4.0]: https://github.com/gimso2x/forgeflow/compare/v0.3.2...v0.4.0
