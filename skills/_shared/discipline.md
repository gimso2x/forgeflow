# Shared Discipline Rules

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

## User language and artifact readability (core)

- Detect the user's primary language from the current request and recent conversation. Write user-facing replies and Markdown artifact prose in that language.
- For Korean users, write explanatory prose in `brief.md`, `plan.md`, `implementation-notes.md`, `review-report.md`, `ship-summary.md`, and finish decision reports in natural Korean.
- Keep technical identifiers in English when they are part of the workflow contract: file paths, commands, code identifiers, artifact filenames, frontmatter keys, table keys, route labels (`small`, `medium`, `high`, `epic`), verdict enums (`approved`, `changes_requested`, `blocked`), and gate values (`PASS`, `FAIL`, `skip`, `n/a`).
- Prefer localized section titles with the canonical English label preserved in parentheses, such as `## 검증 계획 (Verification Plan)`, so artifacts stay readable to the user without losing ForgeFlow traceability.
- For long high/epic artifacts, put a short user-language summary near the top before detailed tables or checklists.
- On stage resume after context compaction, follow `_shared/context-resume.md` (checkpoint-first, section-targeted reads).

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
