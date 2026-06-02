# Shared Discipline Rules

## Behavioral Guardrails

When writing or reviewing code, apply the advisory guardrails in `docs/advisory-guidelines.md`:

- **Think Before Coding**: do not silently pick among materially different interpretations.
- **Simplicity First**: avoid speculative abstractions or features not required by the brief.
- **Surgical Changes**: changed lines must trace to the user request, brief, or plan.
- **Goal-Driven Execution**: success must be verifiable by artifact evidence or command output.
- **Evidence Contract**: a completion declaration without a `ship-summary.md` Evidence Manifest section is incomplete. Gate results must come from actual command execution, not claims. Review must treat a missing Evidence Manifest as `blocked`.


Common file-write and response discipline shared across ForgeFlow workflow skills.
Each skill links here and adds skill-specific rules inline.

## File write and output discipline (core)

- Default to **artifact-first mode**. Write artifacts under `.forgeflow/tasks/<task-id>/` unless the user explicitly asks for a dry run, exact-output response, or no-write simulation.
- If the task directory is missing, bootstrap or recover it first. Do not proceed to source edits while the workflow state lives nowhere.
- Write only under the current project workspace or the active task directory. Never write inside the plugin installation directory, marketplace cache, extension cache (including `.claude/plugins/cache`, `.codex/plugins`, `.cursor/plugins`, `~/.cursor/plugins/local`, `.gemini/extensions`, or `~/.gemini/extensions`), or `skills/<skill>/`.
- Treat repository cleanup as selective and evidence-based. Never run broad destructive cleanup such as `git clean -fdX`; inspect status first and remove only explicitly identified generated caches or task-scoped artifacts.
- Never claim provider/plugin E2E, live CLI smoke, or real Claude/Codex/Gemini behavior unless the exact provider command was actually run in the current task and its result is cited. If only repo validators or deterministic smoke fixtures ran, say that explicitly.
- If the user says "do not write files", "return only", "dry run", "just list", or asks for a label/summary only, obey that output constraint exactly and do not attempt any filesystem mutation.
- When artifacts are mentioned without an explicit path, assume `.forgeflow/tasks/<task-id>/`, not chat-only fallback.

## Template resolution (core)

Skills reference templates as `templates/<file>.md`. Resolve the actual path in this order (first match wins):

1. `.forgeflow/templates/<file>.md` in the workspace — exists when `ff-config init` has been run.
2. Plugin cache `templates/<file>.md` — search these paths:
   - `~/.claude/plugins/cache/forgeflow/**/templates/<file>.md`
   - `~/.cursor/plugins/local/forgeflow/templates/<file>.md`
   - `~/.cursor/plugins/**/forgeflow/templates/<file>.md`
   - `.codex/plugins/**/forgeflow/templates/<file>.md`
3. If no template file is found, generate the artifact structure from the fields listed in the skill's procedure section. Do not invent structure beyond what the skill specifies.

When creating `.forgeflow/templates/` during init, copy all `*.md` files from the resolved plugin `templates/` directory to `.forgeflow/templates/` so subsequent runs do not depend on plugin cache paths.

## User language and artifact readability (core)

- Detect the user's primary language from the current request and recent conversation. Write user-facing replies and Markdown artifact prose in that language.
- For Korean users, write explanatory prose in `brief.md`, `plan.md`, `implementation-notes.md`, `review-report.md`, `ship-summary.md`, and finish decision reports in natural Korean.
- Keep technical identifiers in English when they are part of the workflow contract: file paths, commands, code identifiers, artifact filenames, frontmatter keys, table keys, route labels (`small`, `medium`, `high`, `epic`), verdict enums (`approved`, `changes_requested`, `blocked`), and gate values (`PASS`, `FAIL`, `skip`, `n/a`).
- Prefer localized section titles with the canonical English label preserved in parentheses, such as `## 검증 계획 (Verification Plan)`, so artifacts stay readable to the user without losing ForgeFlow traceability.
- Prefer bullet lists over Markdown tables in user-facing artifacts. Use tables only when a compact matrix is materially easier to scan, and always keep verdicts, changed files, evidence, metrics, risks, and next actions readable in plain CLI/Telegram transcripts.
- For long high/epic artifacts, put a short user-language summary near the top before detailed sections or checklists.
- On stage resume after context refresh, follow `_shared/context-resume.md` (checkpoint-first, section-targeted reads).

## Security discipline (core)

- Token/secret/credential은 환경 변수에서만 읽는다. tool/API 입력 스키마에 token 필드를 배제하고, 오류 메시지에 token 값을 마스킹하거나 제외한다.
- MCP tool 서버를 구현하거나 확장할 때, plan에서 contract(입력/출력 타입, read-only 범위)를 먼저 정의하고 server의 `tools/call`에서 unknown tool을 명시적 거부한다. write 기능이 필요한 경우에도 contract-first 원칙은 유지한다.

## Strict response constraints (core)

- When the user asks for an exact count, exact format, or "only" output, that instruction overrides the normal artifact template. Return exactly what was requested and nothing extra.
- When the user says "do not run commands", do not propose command execution as if it happened. You may name a manual check, but label it as manual inspection, not a command result.
- For exact-count list prompts, output numbered lines only. No heading, preamble, fenced block, summary, or extra lines.

## Scope Boundary

### In Scope (명시적 허용)
- 요구사항에 명시된 기능/수정
- 직접적 의존 파일
- 관련 테스트 파일
- 관련 문서 업데이트

### Out of Scope (명시적 거부 필요)
- 요구사항에 없는 리팩토링
- 인접 모듈 "개선"
- 의존성 버전 업그레이드
- 포맷팅/스타일 변경 (별도 태스크가 아닌 경우)
- "어차피 건드리니까" 식의 확장

### Boundary Judgment Criteria
- 파일 수정 범위가 route 임계값 초과 시 자동 경고
- scope 파일 수: small ≤3, medium ≤8, high ≤20, epic 무제한
- 초과 시 "scope split 권장" advisory 발행
- boundary 판단은 사람 해석에 의존하지 않고 파일 수/경로 기준으로 자동 산정

### Scope Expansion Alert
- execute 중 scope 파일 수가 route 임계값을 초과하면 경고
- review에서 scope boundary 위반을 탐지
- advisory로 "scope creep 의심" 발행

## Harness Level Principles

ForgeFlow는 키노트 "도구보다 구조, 구조보다 검증 루프"의 Harness L0→L7 프레임워크를 따른다.

### Evidence Contract (L3)
- 완료 선언은 증거가 아니다, 완료는 계약이다.
- `ship-summary.md` Evidence Manifest 섹션 없는 completion declaration은 불완전.
- Gate 결과는 실제 명령 실행 기반이어야 하며, claim이 아님.
- FAIL 시 실패 원인·교정 조치·다음 실행 조건을 기록.

### Hook Pipeline (L5)
- 규칙은 적는 게 아니라 강제되어야 한다.
- SOFT 규칙(advisory markdown)이 반복 FAIL하면 HARD 규칙(json, `exit 2`)으로 자동 승격.
- `scripts/forgeflow_hook_check.sh`로 Claude Code hooks에서 검증 호출.

### Memory Bank (L4)
- 기억은 저장이 아니라 다음 실행 조건.
- 팩트는 출처(artifact, task-id)와 함께 저장. 요약으로 대체 불가.
- `scripts/forgeflow_fact_store.py`로 팩트 추가/검색/정리.
- ship과 long-run에서 팩트 추출. clarify에서 관련 팩트 자동 회수.
- 승격 이력은 audit-log에 기록.

### Closed Loop (L6)
- 사과가 아니라 조건이 바뀌어 루프가 닫힌다.
- review FAIL → checkpoint.md Re-Execution Conditions 섹션 자동 작성 → execute 재진입.
- 실패 시 rollback(git restore), Memory Bank에 실패 패턴 기록.
- 최대 3회 루프. 3회 초과 시 blocked. 동일 finding 반복 시 재계획 권장.

## Telemetry Event Recording

Every pipeline stage (clarify, plan, execute, review, ship) must record a
telemetry event upon completion. Events are written to the project-global
`.forgeflow/telemetry/` directory.

### Automatic collection via scripts

Run `python3 scripts/telemetry_collect.py` after any stage completes to scan
`.forgeflow/tasks/<task-id>/` artifacts and append structured events to
`.forgeflow/telemetry/<task-id>.md`. Run `python3 scripts/telemetry_aggregate.py`
to generate `.forgeflow/telemetry/summary.md` with aggregated metrics.

### Manual event recording (when scripts are unavailable)

When `telemetry_collect.py` cannot run, the agent must manually append an event
block to `.forgeflow/telemetry/<task-id>.md`. **반드시 다음 형식을 준수한다**:

```yaml
### <ISO 8601 timestamp (예: 2026-05-29T14:30:00+09:00)>
- **event**: stage_complete | stage_fail | boundary_alert | stage_start
- **stage**: clarify | plan | execute | review | ship
- **task_id**: <task-id>
- **outcome**: success | partial | failed
- **route**: small | medium | high | epic | unknown
- **adapter**: claude | codex | gemini | cursor | unknown
- **timestamp**: <ISO 8601>
```

**필수 필드**: `event`, `stage`, `task_id`, `outcome`, `timestamp`는 반드시 기록한다. 나머지 필드는 알 수 없으면 `unknown` 또는 `n/a`로 기록한다. 필드를 생략하지 않는다.

**금지 사항**:
- 필드 이름을 임의로 변경하지 않는다 (예: `stage:` → `단계:` 사용 금지)
- YAML frontmatter가 없는 telemetry 파일은 생성하지 않는다
- 기존 이벤트를 덮어쓰지 않고 append만 한다

### Rules
- Create `.forgeflow/telemetry/` if it does not exist.
- Use one file per task: `.forgeflow/telemetry/<task-id>.md`.
- Do not overwrite existing events; append only.
- If the file is new, write the YAML frontmatter and header first (see `templates/telemetry-event.md`).
- Record a `boundary_alert` event when scope_boundary.status is `exceeds`.
- After high/epic ship, run `telemetry_aggregate.py` to refresh `summary.md`.
