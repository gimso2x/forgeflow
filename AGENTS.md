# ForgeFlow — AGENTS.md

> **대상:** 이 파일은 ForgeFlow 레포 자체를 개발하거나 수정하는 AI coding agent를 위한 instructions입니다.

Repository-level instructions for AI coding agents working on this repo.

## Project Overview

ForgeFlow는 AI coding agent를 위한 artifact-first delivery workflow입니다.
clarify, plan, execute, review, ship 파이프라인을 markdown 산출물과 프롬프트 기반 강제로 제공합니다.
plan은 epic 라우트에서 마일스톤 분해를 포함하고, execute는 opt-in subagent per-task 모드를 지원하며, ship은 브랜치 정리까지 담당합니다.
Claude Code, Codex, Gemini CLI, Cursor(로컬 플러그인)를 지원합니다.

## Current Repo Surface

ForgeFlow v1.x is a slim, markdown-only distribution. Do not assume the older `forgeflow_runtime/`, `schemas/`, or `tests/` trees exist when working on this branch. Use the current Makefile validators (`make validate` and focused `validate-*` targets) as the local contract surface.

## Tech Stack

- **Skills**: 순수 Markdown (SKILL.md + YAML frontmatter)
- **Templates**: Markdown artifact templates (`templates/`)
- **Docs**: 어댑터 참조 (`docs/adapter-config.md`)
- **No runtime dependencies** — Python, Node.js 등 외부 의존성 없음
- **Adapters**: Claude Code (`.claude-plugin/`), Codex (`.codex-plugin/`), Gemini CLI (`GEMINI.md`), Cursor (`.cursor-plugin/`)

## Repo Structure

```
skills/                   # 각 스킬 디렉토리 (SKILL.md 포함)
  forgeflow/              # 메인 라우터 (canonical contract, 영문)
  clarify/                # 작업 공간 초기화 + 요구사항 정리 → brief.md
  plan/                   # 계획 수립 → plan.md; epic 라우트 시 마일스톤 분해
  execute/                # 구현 실행 → implementation-notes.md (+ references/ subagent prompts; opt-in subagent per-task loop)
  review/                 # 독립 검증 → review-report.md
  ship/                   # 배포/마무리 + 브랜치 정리 (merge/PR/keep/discard)
  long-run/               # 학습 기록 → eval-record.md
  benchmark/              # cross-adapter 벤치마크
templates/                # Markdown 산출물 템플릿
docs/                     # adapter-config 등 참조 문서
.claude-plugin/           # Claude Code 플러그인 설정
.codex-plugin/            # Codex 플러그인 설정
.cursor-plugin/           # Cursor 로컬 플러그인 설정
GEMINI.md                 # Gemini CLI 어댑터 (skill imports)
SKILL.md                  # Claude marketplace entry (한국어 요약 → skills/forgeflow 위임)
```

## Development Workflow

1. **스킬 수정** — `skills/<name>/SKILL.md` 편집 (canonical contract 변경 시 `skills/forgeflow/SKILL.md` 우선)
2. **템플릿 수정** — `templates/<name>.md` 편집
3. **어댑터 문서** — `docs/adapter-config.md` (감지·CLI·타임아웃 canonical)
4. **플러그인 설정** — `.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `GEMINI.md` 동기화
5. **수동 테스트** — 해당 스킬 실행하여 산출물 확인
6. **릴리즈** — `VERSION` 파일만 수정하면 CI(`sync-version.yml`)가 나머지 매니페스트 7개를 자동 동기화. `CHANGELOG.md` 수동 작성 후 `/forgeflow:release` 스킬로 커밋·push·GitHub release 생성. manifest 직접 수정 금지.
   - **Release 스킬**: `.claude/skills/release.md` — Claude Code 전용. 공개 `skills/` inventory에 포함되지 않음.

## Code Conventions

- 모든 산출물은 Markdown. `templates/` 디렉토리에 템플릿이 있습니다.
- 스킬은 YAML frontmatter (`name`, `description`, `validate_prompt`)로 시작. 일부 스킬은 스키마 버전용 `version`/`author` 필드를 추가할 수 있으며, 이는 릴리즈 `VERSION`과 별개입니다.
- **버전 관리**: `VERSION` 파일이 단일 소스. 매니페스트(SKILL.md, .claude-plugin/*.json, .codex-plugin/plugin.json, .cursor-plugin/plugin.json, gemini-extension.json)는 직접 수정하지 않는다. CI가 자동 동기화함.
- 산출물은 `.forgeflow/tasks/<task-id>/` 아래에 작성.
- Review는 읽기 전용. 코드 수정 금지.
- Verification은 실제 명령 기반. hallucinated command 금지.
- 외부 의존성 추가 금지.
- Evolution rules: `templates/evolution-rule.md` + `.forgeflow/evolution/{proposed,active,retired}/`

## Key Patterns

- **Route selection**: clarify 스킬이 small/medium/high/epic 라우트 선택; medium은 medium-light/full sub-band 기록
- **Canonical contract**: `skills/forgeflow/SKILL.md` — 루트 `SKILL.md`는 marketplace 요약만
- **Adapter config**: `docs/adapter-config.md` — forgeflow SKILL은 중복 표 대신 참조
- **Milestone planning**: Epic 태스크는 roadmap.md로 마일스톤 분해 후 상세 계획
- **Evidence discipline**: review는 파일 경로와 구체적 증거로 판단
- **Prompt-driven enforcement**: 게이트와 규칙은 프롬프트로 강제, 스크립트 없음
