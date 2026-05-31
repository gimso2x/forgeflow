# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Review runtime contract documented as a thin adapter-neutral layer with standalone input provenance, role-separated evidence handling, read-only tool permissions, evidence levels, human review gate requirements, and minimal team-mode guardrails.
- Review finding template now requires `Evidence Source` and `Evidence Level`, with advisory validation guarding those fields against drift.
- Standalone review provenance artifacts now have explicit templates for `input-source.md` and `normalized-input.md`, so adapters share one markdown-first bootstrap surface.
- Shared automation guidance now includes a stage artifact/tool boundary catalog so clarify, plan, execute, review, and ship preserve role separation while chaining.
- Review runtime contract now includes markdown-bound lead/member guardrails for occasional parallel reviewer passes without adding a persistent team scheduler.
- Review adapters now have an explicit compliance checklist for source classification, reproducible fetch labels, complete normalization, visible limitations, and single canonical report ownership.
- Execute subagent and parallel handoffs now require run-ledger claim markers with role, scope, and timestamp before delegated work starts.
- Standalone review normalization now has an explicit pre-role gate so missing brief/evidence/scope/constraints/limitations block approval instead of being inferred by reviewer roles.
- Standalone review provenance now records source classification rationale so adapters must explain input-type selection and ambiguity handling before normalization.
- Review role summaries now record the exact role checklist version used, with advisory validation guarding the field against template drift.
- Review skill now carries the inspection-only tool posture inline, with validation guarding that code/product fixes are handed back to execute.
- Role-based review now requires per-role pass records, including zero-finding passes, so aggregation depends on artifacted scope/evidence/verification/limitations instead of chat-only completion claims.
- `checkpoint.md` now includes a `Handoff Boundary` section so stage owner, next owner, handoff reason, and forbidden-action delegation stay explicit across refreshes and adapter handoffs.
- `review-report.md` now includes an explicit reusable role-pass record block for every active reviewer role, with advisory validation guarding scope/evidence, observed verification, limitations, finding counts, and role verdict fields.
- Advisory contract validation now guards standalone review normalization-gate fields and requires the gate to stay visible before reviewer summaries.
- Review role routing now records per-role trigger rationale so adapters and parallel reviewers cannot silently broaden or narrow review scope after standalone normalization.
- Review role summaries now separate `Active roles` from `Skipped roles`, requiring explicit skip reasons for every supported role that does not run.

## [1.9.3] - 2026-05-31

### Fixed

- Synchronized release manifests to `VERSION` 1.9.3.

## [1.9.2] - 2026-05-29

### Added

- **Post-task simplification loop**: 검증 통과 후 변경 코드에 대해 삼중 렌즈(코드 재사용, 품질, 효율) 분석을 반복 수행하는 정제 루프를 execute 스킬에 추가. small/medium은 마지막 단계 후 1회, high/epic은 매 단계 후 실행

### Fixed

- **marketplace.json 버전 동기화**: marketplace.json metadata.version이 1.9.0에 머물러 있던 문제 수정

## [1.9.1] - 2026-05-29

### Changed

- **워크트리 심볼릭 링크 순환 문제 근본 해결**: `.forgeflow` 전체 디렉터리 대신 비순환 서브디렉터리(tasks, telemetry, evolution, defaults.md 등)만 개별 symlink하여 Vite/webpack file watcher ELOOP crash 원천 차단
- **워크트리 수명주기 개선**: 고아 워크트리 탐지, cleanup-only 모드, review 단계 워크트리 경고, config prune 명령 추가
- **로컬 작업 산출물 무시 목록 정비**: `.gitignore`에 `.playwright-mcp/`, `samples/`, `forgeflow_runtime.egg-info/` 등 생성 산물 패턴 추가

### Fixed

- **config/SKILL.md 버전 포맷 정정**: schema version을 다른 skill과 동일한 `0.x.0` 포맷으로 통일
- **roadmap 상태 동기화**: Priority 6(scope boundary) 완료 표시, Phase 3+ 상태 업데이트, 기준 버전을 v1.9.0으로 갱신
- **.gitignore dogfooding 예외 명시화**: tracked `.forgeflow/tasks/*` fixture를 명시적 예외로 추가
- **review/ship 스킬에 decision-log 참조 추가**: 이전 단계 결정 추적성 향상

## [1.9.0] - 2026-05-29

### Added

- **Installed plugin E2E smoke**: README에 설치된 Claude 플러그인(≠ `--plugin-dir`) 기반 E2E 검증 절차 문서화; 플러그인 버전 불일치 방지 가이드 추가
- **Small route fast-review**: small 라우트에 fast-review depth 적용 — 최소 검증 게이트(변경 파일 스코프, 수용 조건 확인, 최소 1개 독립 게이트, 블로커 스캔), 산출물 ≤80줄 목표, bullets-only(마크다운 테이블 금지), Specialist Assertions/Code Quality Metrics 섹션 생략

### Changed

- **산출물 포맷**: review-report, implementation-notes, ship-summary 템플릿의 메트릭/마이크로게이트 테이블을 불릿 리스트로 변환; eval fixture의 잔여 테이블도 정리
- **Adapter config**: `docs/adapter-config.md`에 플러그인 버전 불일치 방지 섹션 추가
- **Skill 가이던스**: `skills/_shared/discipline.md`에 "불릿 리스트 선호" 가이드 추가; `skills/forgeflow/SKILL.md`에 산출물 포맷 가이던스 업데이트

### Fixed

- Context refresh references in skills now centralize `/compact` and `/clear` adapter hints in `_shared/context-resume.md`; public stage skills use adapter-neutral wording.
- **context refresh 문구 정합성**: shared automation/context-resume 문서와 eval을 `/clear` 강제 대신 adapter-neutral refresh로 정리

## [1.8.0] - 2026-05-27

### Added

- **Human review gate**: review와 ship 사이에 구조적 human judgment gate를 추가하고 spec/quality/security/ux/perf reviewer 역할, priority, disposition, remediation rationale을 review report 산출물에 반영
- **Standalone review coverage**: URL, diff, path, lockfile, generated/binary/symlink/submodule/deleted-test 등 독립 리뷰 입력 케이스를 eval fixture로 확장
- **Config menu full init**: `/forgeflow:config` 인터랙티브 메뉴에서 basic/full init을 선택해 `.forgeflow/defaults.md`와 `.forgeflow/project-draft.md`를 생성하는 흐름 추가

### Changed

- **Review criteria 정렬**: plan, review, README, root marketplace summary의 Design Intent / Review Criteria 필드를 template과 동기화
- **Evidence contract 강화**: observed evidence와 reported evidence를 구분하고 review/ship handoff에서 unresolved human judgment를 명확히 표시

## [1.7.0] - 2026-05-27

### Fixed

- **Release surface 정합성**: slim v1 배포 표면의 version, changelog, plugin prompt 계약 검증을 1.7.0 기준으로 동기화

## [1.6.0] - 2026-05-27

### Added

- **Telemetry 실구현**: `scripts/telemetry_collect.py`와 `scripts/telemetry_aggregate.py`를 추가해 `.forgeflow/tasks/` 산출물 기반 이벤트 수집과 `.forgeflow/telemetry/summary.md` 집계를 지원
- **Pipeline telemetry contract**: clarify, plan, execute, review, ship 각 스킬에 완료/실패/boundary alert 이벤트 기록 의무와 stage별 failure type을 추가
- **Specialist review routing**: clarify 단계에서 route와 specialist를 분리하고 review assertion profile을 role별로 적용
- **표준 산출물 확장**: `plan-ledger`, `decision-log`, `project-draft`, telemetry event, metrics dashboard 템플릿 추가
- **Init 아키텍처 초안 생성기**: config/forgeflow 스킬에 project draft 생성 흐름과 eval coverage 추가
- **Scope boundary 명시화**: route별 파일 수 기준, advisory boundary alert, review boundary 검증을 추가

### Changed

- **Makefile 검증 구조 개선**: 인라인 Python 검증 로직을 `scripts/validate_*.py`로 분리하고 `make validate` 유지보수성을 개선
- **Eval coverage 확장**: route policy, benchmark, long-run, telemetry, scope boundary, review standalone, config 전파 회귀 케이스를 포함해 총 92개 eval로 확장
- **문서 정합성 보강**: README, advisory guidance, roadmap, adapter/plugin reference 간 telemetry 및 scope boundary 참조를 동기화

### Fixed

- **CHANGELOG/비교 링크 정합성**: 누락된 과거 버전 섹션과 release compare link를 보강
- **Route/config 정합성**: auto/config 전파 회귀와 adapter plugin defaultPrompt mapping 검증을 추가
- **Template/reference 정합성**: 미사용 템플릿 제거, cross-reference 보강, GEMINI/shared skill 참조 정리

## [1.5.2] - 2026-05-27

### Fixed

- **`defaults.md auto:true`가 brief.md에 전파되지 않던 버그 수정**: config 스킬에서 `auto: true` 설정 시 clarify 단계에서 생성되는 brief.md에 자동 모드가 반영되지 않던 문제 해결

## [1.5.1] - 2026-05-26

### Changed

- **Route별 차등 테스트 적용**: medium은 test-after, high/epic만 TDD 적용
  - `skills/execute/SKILL.md`: Route-aware Testing 표 추가 — small(테스트스킵), medium(test-after), high(로직만TDD), epic(전체TDD)
  - `skills/plan/SKILL.md`: medium에서 T1 테스트 전용 단계 분리 금지, 구현 단계에 통합 및 Task Granularity 예시 분리

## [1.5.0] - 2026-05-26

### Added

- **워크트리 세션 속도 개선**:
  - `skills/_shared/isolation.md`: Vite/webpack watcher에 `.forgeflow` 제외 설정 추가 (OOM 원천 차단), worktree `pnpm install --frozen-lockfile` 적용 (설치 속도 향상), Known issues 섹션 추가 (dev server OOM, lint 중복, scope creep)
  - `skills/execute/SKILL.md`: adaptive verification 추가 (변경 성격에 따라 최소 게이트만 실행), `scope_boundary_check`를 medium/high/epic 표준 게이트로 추가, 워크트리 symlink 주의사항 확장

## [1.4.0] - 2026-05-26

### Added

- **브랜치명 컨벤션**: task ID와 branch name 분리. `<type>/<YYYYMM>-<한글-설명>` 형식 적용 (예: `fix/202605-면적-슬라이더-정합`). 커밋 prefix가 `[fix/202605-면적-슬라이더-정합]` 형태로 프로젝트 컨벤션 정합
- **adapter-neutral execute step checkpoint**: Claude-only `/clear` 강제를 제거하고 checkpoint-first continuation + 필요 시 adapter별 context refresh(Claude/Codex `/compact`, fresh session 등)로 정리

### Changed

- **ship `--auto` 동작 개선**: worktree + auto면 로컬 병합 + cleanup 자동 진행 (4선지 프롬프트 제거). non-worktree는 커밋 후 완료 보고만 출력
- **execute `--auto` 리뷰 자동 진행**: 완료 보고 후 `/forgeflow:review` 자동 invoke 명확화
- **worktree cleanup 후 메인 리포지토리로 cd**: merge/discard cleanup 시 세션이 삭제된 경로에 머무는 문제 해결
- **worktree 브랜치명에서 `ff/` 접두어 제거**: 가독성 개선, worktree 식별은 `git worktree list` 사용

### Fixed

- **worktree symlink 테스트 중복 수집**: `.forgeflow` symlink로 인해 Vitest/Jest가 중복 파일을 수집하는 문제. exclude 패턴 가이드 추가

## [1.3.4] - 2026-05-26

### Added

- **코딩 컨벤션 문서**: `skills/_shared/coding-convention.md` 추가 — execute/implementer에서 참조
- **`/forgeflow:config` 독립 스킬 등록**: 슬래시 커맨드 미동작 수정으로 config를 독립 호출 가능

## [1.3.5] - 2026-05-26

### Fixed

- **`skills/config/SKILL.md`**: `isolation` 기본값이 `false`로 잘못 표시되던 버그 수정 (실제 기본값은 `true`)
- **`skills/config/SKILL.md`**: `defaults.md` 미존재 시 모든 기본값을 `false`로 처리하던 문제 수정 (필드별 하드코딩된 기본값 사용)

### Changed

- **`subagent_per_task` 설정 제거**: config/defaults에서 제거. execute 스킬이 epic 라우트에서 필요시 자체 판단. CLI 플래그 `--subagent-per-task`로 수동 활성화 가능
- **`docs/adapter-config.md`**: `isolation` 필드를 프로젝트 기본값 테이블에 추가, 우선순위 설명 일반화
- **`skills/forgeflow/SKILL.md`**: config 메뉴 예시에 기본값 표시 및 `subagent_per_task` 제거 반영

## [1.2.0] - 2026-05-27

### Added

- **Standalone review mode** (`/forgeflow:review` without pipeline): review external input (URL/repo/diff/files) independently with role-based review (`--type spec|quality|security|ux|perf|all`)
- **`skills/review/SKILL.md` standalone flow (S1–S10)**: normalized-input.md generation, role-based routing, Human Judgment Gate
- **`templates/review-report.md` standalone sections**: mode header, evidence table, advisory disclaimer, `perf` role enum
- **SKILLS.md standalone lifecycle**: pipeline-independent review example added
- **README standalone review section**: usage examples, supported input types, supported roles
- **`skills/_shared/automation.md` Strict auto-chain mode**: `--auto` 스테이지 exit 체크리스트, artifact-before-code 순서, 금지 프롬프트 목록
- **auto-break 확장**: scope change, external dependency hard failure(예: API 429), context limit 시 checkpoint blocked 후 중단 규칙

### Changed

- **`skills/forgeflow/SKILL.md`**: `--auto` procedure에 Strict auto-chain checklist 참조 추가

## [1.1.4] - 2026-05-21

### Changed

- **`--auto` strict auto-chain 계약 보강**: `skills/_shared/automation.md`에 strict mode 체크리스트, artifact-before-code 순서, 금지 프롬프트 목록 추가
- **`skills/forgeflow/SKILL.md`**: `--auto` procedure에 strict auto-chain checklist 참조 추가

## [1.1.3] - 2026-05-21

### Added

- **`.github/workflows/evals.yml`**: eval fixture 계약 자동 검사 (`validate-evals-json`, `validate-eval-files`, `validate-evals-fixtures`)
- **`Makefile` `validate-evals-fixtures`**: 제거된 slash command 참조 및 smoke fixture 구체성 검사

### Changed

- **`validate-oh-my-agent-contract`** → **`validate-advisory-contract`**: oh-my-agent handoff 문서 의존 제거
- **README**: ship branch-disposition safety, advisory/eval fixture 검사 범위 및 `evals` workflow 설명

### Removed

- **`docs/oh-my-agent-forgeflow-handoff.md`**, **`docs/oh-my-agent-absorption-review.md`**: legacy handoff 문서 (흡수 완료, advisory 계약은 유지)

## [1.1.2] - 2026-05-21

### Added

- **`examples/evolution/`**: evolution rule 샘플 (`proposed/sample-rule.md`) 및 README
- **`docs/dogfooding.md`**: tracked `.forgeflow/tasks/*` fixture 설명
- **`Makefile` `validate-workflow-vocab`**: canonical lifecycle ordering 검사 (`ship → long-run`, stale `/forgeflow:finish` 차단)
- **`GEMINI.md`**: `@./docs/adapter-config.md` import

### Changed

- **1.1.0 스킬 통합 잔재 정리**: `automation.md`, 템플릿 stage enum, `evals.json` finish eval 3건을 ship branch disposition 기준으로 갱신
- **`skills/ship/SKILL.md`**: "finish"는 별도 스테이지가 아닌 ship 내부 branch disposition임을 명시
- **`skills/SKILLS.md`**: review를 `spec pass → quality pass` 한 줄로 통합
- **`.github/workflows/validate.yml`**: 인라인 검사 → `make validate` 단일 호출로 CI/Makefile 동기화
- **`AGENTS.md`**: release 스킬(`.claude/skills/release.md`)이 Claude Code 전용임을 명시

### Fixed

- CI가 삭제된 `skills/finish/SKILL.md` 및 `forgeflow-init` prompt 분기를 참조하던 contract drift

## [1.1.1] - 2026-05-21

### Added

- **`skills/_shared/context-resume.md`**: checkpoint-first resume, `/compact` timing, stage별 minimum read set, section-targeted read 규칙

### Changed

- **`skills/_shared/preflight.md`**: checkpoint-first, section-targeted reads (full artifact 재독 기본값 제거)
- **Stage skills** (`clarify`, `plan`, `execute`, `review`, `ship`, `forgeflow`): context-resume cross-ref 및 stage별 minimum read set
- **Templates** (`checkpoint`, `implementation-notes`, `run-ledger`, `review-report`, `ship-summary`): Evidence Index, Minimum Read Set, compact evidence refs
- **README**, **docs/adapter-config.md**: Context efficiency / compact resume 요약

## [1.1.0] - 2026-05-21

### Changed

- **Evolution 파이프라인**: evolution rule 생성을 ship 단계로 통합 (propose→activate 일원화)
- **Evolution rule format**: global-advisory compact 6-line format (`Trigger`, `Stage`, `Mode`, `Apply`, `Skip`)
- **review 스킬**: evolution rule validation 제거 — ship이 생성·활성화 담당
- **스킬 통합**: 12개 스킬을 8개로 축소하여 워크플로우 단순화
  - `forgeflow-init` → `clarify`에 통합 — clarify가 작업 공간 생성 및 task ID 자동 생성
  - `finish` → `ship`에 통합 — ship이 브랜치 정리(merge/PR/keep/discard)까지 담당
  - `milestone` → `plan`에 통합 — epic 라우트에서 plan이 마일스톤 분해 포함
  - `subagent-execute` → `execute`에 통합 — `--subagent-per-task` 플래그로 전환

### Removed

- `/forgeflow-init` 명령어 (→ `/forgeflow:clarify` 사용)
- `/forgeflow:finish` 명령어 (→ `/forgeflow:ship` 사용)
- `/forgeflow:milestone` 명령어 (→ `/forgeflow:plan`이 epic decomposition 포함)
- `/forgeflow:subagent-execute` 명령어 (→ `/forgeflow:execute --subagent-per-task` 사용)

## [1.0.7] - 2026-05-21

### Fixed

- Makefile Python `SyntaxWarning` 10건 제거 — `exec()` 내 비표준 이스케이프 시퀀스(`\s`, `\[`, `\.`) 정규화

### Changed

- clarify 라우트 스코어링에 WHERE 기반 보정 규칙 추가 — `ambition=toy` 강등, `ambition=product+risk` 승격, greenfield cap 명시

## [1.0.6] - 2026-05-20

### Added

- oh-my-agent style handoff absorption: structured skill metadata contracts, multilingual alias hints, route/session budget guidance, and enriched brief/plan templates.
- Local validation coverage for release/version alignment, changelog compare links, skill inventory/frontmatter, Gemini imports, plugin prompts, eval fixture contracts, markdown links, adapter config, route vocabulary, finish safety, and oh-my-agent advisory contracts.
- First-run demo target and docs/eval coverage for local template/artifact smoke.

### Changed

- ForgeFlow remains markdown-only/no-runtime while centralizing advisory route guidance in `docs/advisory-guidelines.md` and importing it into Gemini context.
- Codex/Gemini/README/operator docs now document project-root/plugin-cache safety, Gemini extension update/list checks, and validation scope more explicitly.
- Plan and brief templates now include advisory execution pattern, budget, suggested next skill, specialist, and evolution-rule sections.

### Fixed

- Finish/worktree cleanup guidance now avoids destructive removal of unrelated dirty state and protects Gemini extension cache paths.
- Active docs and eval contracts now reject stale route/schema vocabulary and broken or escaping markdown links.
- 4-model cross-review corrections: YAML frontmatter integrity validation, concrete dependency paths, optional Mermaid guidance, `small` alias ambiguity cleanup, and advisory-doc modified-date header.

## [1.0.5] - 2026-05-20

### Added

- **Benchmark v0.3.0** — CLI 경로 해석(WSL2 `/mnt/c/` 스킵), rate limit 자동 감지/순차 재시도, 컴플라이언스 `<!-- BEGIN/END -->` 구분자, large 사이즈, N회 반복/분산 분석, DNF 명시 처리.
- **코드 품질 메트릭 파이프라인** — execute → review → ship 단계로 정량 메트릭(LOC, TS errors, type assertions, debug artifacts, max component LOC, log volume) 흐름.
- **Adapter-aware execution 확장** — Verification / Output Discipline / Rate Limit 3열 테이블. Codex 출력 정규화, Gemini 순차/cooldown 가이드, 메트릭 수집 명령어.
- **Completion Response 구분자** — `### Completion Response` 헤딩으로 프롬프트 에코와 실제 응답 분리.
- **Review 정량 평가** — Code Quality Metrics 섹션, blocker threshold 자동 판정.
- **Ship 정량 요약** — Quantitative Summary 섹션으로 메트릭 누적.
- **템플릿 메트릭 슬롯** — `implementation-notes.md`, `review-report.md`, `ship-summary.md`에 정량 필드 추가.

### Changed

- `skills/benchmark/SKILL.md` — v0.2.0 → v0.3.0 (전면 개선).
- `skills/execute/SKILL.md` — adapter-aware 실행 확장, completion checklist 항목 7(메트릭) 추가.
- `skills/review/SKILL.md` — Code Quality Metrics 섹션 추가.
- `skills/ship/SKILL.md` — Quantitative summary 요구사항 추가.
- `templates/implementation-notes.md`, `templates/review-report.md`, `templates/ship-summary.md` — 메트릭 테이블 추가.

## [1.0.4] - 2026-05-20

### Added

- **Opt-in `subagent-execute` skill** — high/epic per-plan-step loop: implementer → spec micro-review → quality micro-review (`/forgeflow:subagent-execute`, `/subagent-execute`, or `/forgeflow:execute --subagent-per-task`).
- **Execute subagent reference prompts** — `skills/execute/references/implementer-prompt.md`, `spec-reviewer-prompt.md`, `quality-reviewer-prompt.md`.
- **Per-task micro-gates** on high/epic execute (controller or subagent); evidence via `micro_spec:*`, `micro_quality:*` in `implementation-notes.md`.
- **`review-report.md` → Execute Micro-Gates** — stage review summarizes execute micro-gates as reported evidence and re-verifies independently.
- **run-ledger Assignee discipline** — `worker` | `specialist` | `spec-reviewer` | `quality-reviewer`.
- **Eval cases** `fan-out-execute-ledger`, `review-micro-gates-table` in `evals/evals.json`.
- **CI P12–P13** — execute reference prompts; review-report Execute Micro-Gates contract for template, review skill, high/epic smoke.
- **`docs/adapter-config.md` Cursor 섹션** — IDE slash, template resolution, 타임아웃 가이드.
- **medium-light / medium-full 실행 계약** — brief, plan, review 스킬·템플릿에 sub-band depth 연결.
- **CI adapter-config parity, GEMINI inventory, docs link** 검사.

### Changed

- `skills/execute`, `skills/review`, `skills/forgeflow` — review depth by route, delegation red flags, stage vs micro-gate boundaries.
- `templates/review-report.md`, `templates/run-ledger.md` — micro-gate handoff and assignee guidance.
- `GEMINI.md`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json` — `subagent-execute`, `benchmark` entrypoint parity.
- `skills/SKILLS.md` — inventory row for `subagent-execute`.
- **어댑터 감지 표** — `docs/adapter-config.md`를 canonical source로 통합; forgeflow SKILL은 참조만.
- **루트 `SKILL.md`** — 한국어 요약 + `skills/forgeflow/SKILL.md` 위임으로 축소.
- `plan` / `execute` / `review` Input — `requirements.md` 제거, `brief.md` 단일 소스.
- `README.md`, `AGENTS.md` — docs 링크 및 레포 구조 갱신.

### Removed

- Unused eval artifacts: historical `evals/results/*` reports, route/smoke snapshots, `evals/scenarios/`, smoke fixture dirs except CI-checked high/epic `review-report.md`.
- Root `benchmark-report.md` (unreferenced one-off report).
- Orphan `templates/evolution.md` (superseded by `templates/evolution-rule.md`).

## [1.0.3] - 2026-05-20

### Added

- Cursor 로컬 플러그인 어댑터 (`.cursor-plugin/plugin.json`) 및 README 로컬 설치 가이드.
- `skills/forgeflow/SKILL.md`에 플러그인 `templates/` 경로 해석 규칙과 Cursor 슬래시 명령 매핑.
- `templates/ship-summary.md` 템플릿 추가.
- CI 검사 확장: template 10종, frontmatter contract, template xref, route scoring parity, review/ship artifact contract, SKILLS.md inventory, GEMINI import, evals schema, Exit Condition, CHANGELOG release links.
- `GEMINI.md`에 `long-run` 스킬 import 추가.

### Fixed

- 감사 drift 수정: review 산출물 단일 `review-report.md` 계약 (high/epic spec→quality 순차 pass).
- README/SKILL.md route 표에 `finish` 및 dual review 단계 반영.
- Artifacts 표에 `run-ledger`, `checkpoint`, `ship-summary` 추가.
- clarify epic next-step (`/forgeflow:milestone`), evolution `retired` README 반영.
- Codex `defaultPrompt`에 init/milestone/long-run slash 추가.
- release skill VERSION/SKILL.md/CHANGELOG/cursor-plugin 동기화 목록 보강.

## [1.0.2] - 2026-05-19

### Added

- 진화 규칙 자동 적용 흐름 추가.
- `templates/evolution-rule.md`와 clarify/plan/execute/review/long-run 단계 연결 보강.

### Changed

- README에서 현재 릴리즈 버전 하드코딩을 제거하고, release version policy를 문서화.
- medium route의 weighted scoring 기준과 `17.0` mid threshold 근거 문서화.
- evolution rule lifecycle 진입점과 승격 흐름 문서화.
- 실제 외부 실행 adapter 재도입 시 stderr 경고와 `[y/N]` 확인 프롬프트를 필수 안전 계약으로 명시.

## [1.0.1] - 2026-05-19

### Added

- v1.0.0 마이그레이션 중 유실된 `run-ledger`, `checkpoint`, 역할 분리, evolution pipeline, 실행 패턴 개념 복구.

## [1.0.0] - 2026-05-19

### Breaking Changes

- Python 런타임(`forgeflow_runtime/`) 전체 제거
- JSON 스키마(`schemas/`) 전체 제거
- Python 스크립트(`scripts/`) 전체 제거
- Python 테스트(`tests/`) 전체 제거
- 샘플 산출물(`examples/`) 전체 제거
- 정책 파일(`policy/`) 전체 제거
- 어댑터 생성 파일(`adapters/`) 전체 제거
- 기존 JSON 산출물 포맷(brief.json 등)이 Markdown(brief.md 등)으로 교체됨
- v0.x의 `.forgeflow/tasks/` 디렉토리와 호환되지 않음

### Changed

- 산출물 포맷: JSON → Markdown (templates/에 템플릿 제공)
- 강제 방식: Python 스크립트 → 프롬프트 기반 지시
- 673개 파일에서 ~40개 파일로 축소
- 외부 의존성 제로 (Python, Node.js 불필요)

## [0.13.1] - 2026-05-19

### Fixed

- 전체 pytest CI에서 `forgeflow-init` 스킬 경로 변경을 반영하지 못한 docs schema contract 테스트 수정.

## [0.11.7] - 2026-05-19

### Changed

- 릴리즈/플러그인/확장 버전 메타데이터를 v0.11.7로 동기화.

## [0.11.6] - 2026-05-19

### Changed

- Claude Code 기본 `/init` 명령과 충돌하지 않도록 ForgeFlow 초기화 slash command를 `/forgeflow-init`으로 분리.
- 릴리즈/플러그인/확장 버전 메타데이터를 v0.11.6로 동기화.

## [0.11.5] - 2026-05-18

### Fixed

- 릴리즈/플러그인/확장 버전 메타데이터를 v0.11.5로 재동기화.

## [0.11.4] - 2026-05-17

### Changed

- 문서 전반의 canonical workflow stage 이름을 실제 slash command `/forgeflow:execute`와 맞춰 `execute`로 통일.
- 릴리즈/플러그인/확장 버전 메타데이터를 v0.11.4로 동기화.

## [0.11.3] - 2026-05-17

### Added

- 병렬 작업 안전성, structured evidence, starter blueprint, role/model routing, developer handoff 템플릿 문서 계약 보강.

### Changed

- README/워크플로우 문서에 새 운영 가이드 링크와 병렬 작업 규칙을 반영.

## [0.11.2] - 2026-05-17

### Fixed

- Windows CI에서 비-UTF-8 콘솔 인코딩(cp1252)이 Korean JSON status 문구를 출력하다 실패하던 문제 수정.

## [0.11.1] - 2026-05-15

### Added

- 첫 클론/첫 실행 검증용 disposable `make demo` 경로 추가.
- 로컬 온보딩 smoke path와 런타임 모듈/실행 흐름 문서 보강.

### Changed

- 플러그인 smoke contract와 현재 route/schema vocabulary 검증 강화.
- plan ledger evidence refs를 구조화된 계약으로 정렬.

### Fixed

- `brief.json`의 `required_specialists` 기반 에이전트/스킬 자동 생성 기능 수정.
- `scripts/check_versions.py`에 `gemini-extension.json` 확인 로직 추가 및 정규식 개선.
- editable install smoke 테스트의 불필요한 실행 비용 축소.

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
- `/forgeflow-init` now fully auto-inferable — objective, task-id, risk all optional.

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
- Initial release with canonical 5-stage workflow (clarify → plan → execute → review → verify)
- Evolution engine (8 modules)
- CI gate with GitHub Actions workflow generation
- Agent preset installer (Claude + Codex)

[Unreleased]: https://github.com/gimso2x/forgeflow/compare/v1.9.3...HEAD
[1.9.3]: https://github.com/gimso2x/forgeflow/compare/v1.9.2...v1.9.3
[1.9.2]: https://github.com/gimso2x/forgeflow/compare/v1.9.1...v1.9.2
[1.9.1]: https://github.com/gimso2x/forgeflow/compare/v1.9.0...v1.9.1
[1.9.0]: https://github.com/gimso2x/forgeflow/compare/v1.8.0...v1.9.0
[1.8.0]: https://github.com/gimso2x/forgeflow/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/gimso2x/forgeflow/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/gimso2x/forgeflow/compare/v1.5.2...v1.6.0
[1.5.2]: https://github.com/gimso2x/forgeflow/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/gimso2x/forgeflow/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/gimso2x/forgeflow/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/gimso2x/forgeflow/compare/v1.3.5...v1.4.0
[1.3.5]: https://github.com/gimso2x/forgeflow/compare/v1.3.4...v1.3.5
[1.3.4]: https://github.com/gimso2x/forgeflow/compare/v1.3.3...v1.3.4
[1.2.0]: https://github.com/gimso2x/forgeflow/compare/v1.1.4...v1.2.0
[1.1.4]: https://github.com/gimso2x/forgeflow/compare/v1.1.3...v1.1.4
[1.1.3]: https://github.com/gimso2x/forgeflow/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/gimso2x/forgeflow/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/gimso2x/forgeflow/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/gimso2x/forgeflow/compare/v1.0.7...v1.1.0
[1.0.7]: https://github.com/gimso2x/forgeflow/compare/v1.0.6...v1.0.7
[1.0.6]: https://github.com/gimso2x/forgeflow/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/gimso2x/forgeflow/compare/v1.0.4...v1.0.5
[1.0.4]: https://github.com/gimso2x/forgeflow/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/gimso2x/forgeflow/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/gimso2x/forgeflow/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/gimso2x/forgeflow/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/gimso2x/forgeflow/compare/v0.13.1...v1.0.0
[0.13.1]: https://github.com/gimso2x/forgeflow/compare/v0.13.0...v0.13.1
[0.11.7]: https://github.com/gimso2x/forgeflow/compare/v0.11.6...v0.11.7
[0.11.6]: https://github.com/gimso2x/forgeflow/compare/v0.11.5...v0.11.6
[0.11.5]: https://github.com/gimso2x/forgeflow/compare/v0.11.4...v0.11.5
[0.11.4]: https://github.com/gimso2x/forgeflow/compare/v0.11.3...v0.11.4
[0.11.3]: https://github.com/gimso2x/forgeflow/compare/v0.11.2...v0.11.3
[0.11.2]: https://github.com/gimso2x/forgeflow/compare/v0.11.1...v0.11.2
[0.11.1]: https://github.com/gimso2x/forgeflow/compare/v0.11.0...v0.11.1
[0.11.0]: https://github.com/gimso2x/forgeflow/compare/v0.10.0...v0.11.0
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
