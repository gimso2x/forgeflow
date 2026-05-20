---
name: forgeflow
description: Artifact-first delivery workflow for AI coding agents
version: "1.0.5"
category: engineering
tags: [ai-agents, workflow, artifacts, claude-code, codex, gemini, cursor]
---

# ForgeFlow

ForgeFlow는 Claude Code, Codex, Gemini CLI, Cursor를 위한 **artifact-first delivery workflow**입니다.
채팅 기억 대신 markdown 산출물, 프롬프트 기반 gate, 독립 review로 작업을 진행합니다.

## Quick start

```text
/forgeflow-init          → task workspace
/forgeflow:clarify       → brief.md + route
/forgeflow:plan          → plan.md (medium+)
/forgeflow:execute       → implementation-notes.md + code
/forgeflow:review        → review-report.md
/forgeflow:ship          → ship-summary.md
/forgeflow:finish        → branch disposition
```

Cursor는 콜론 없는 slash (`/clarify`, `/execute` 등)를 사용합니다. 전체 매핑은 canonical contract를 참고하세요.

## Canonical contract

**전체 stage, route, artifact, evolution, adapter 규칙은 [`skills/forgeflow/SKILL.md`](skills/forgeflow/SKILL.md)가 단일 소스입니다.**

이 파일(루트 `SKILL.md`)은 Claude marketplace entry용 **한국어 요약**입니다. 상세 계약·영문 instruction·slash 표·template resolution은 위 canonical skill을 따릅니다.

## Routes (요약)

| Route | Stages |
|-------|--------|
| small | clarify → execute → review → ship → finish |
| medium | clarify → plan → execute → review → ship → finish |
| high | clarify → plan → execute → review (spec+quality) → ship → long-run → finish |
| epic | clarify → milestone → plan → execute → review (spec+quality) → ship → long-run → finish |

Route scoring, medium-light/full sub-band, artifacts 목록: [`skills/forgeflow/SKILL.md`](skills/forgeflow/SKILL.md), [`README.md`](README.md).

## Docs

- [README.md](README.md) — 설치, artifacts, evolution lifecycle
- [docs/adapter-config.md](docs/adapter-config.md) — 어댑터 CLI, 타임아웃, 감지, 출력 정규화
- [skills/SKILLS.md](skills/SKILLS.md) — 스킬 inventory

## Conventions (필수)

- Artifact는 Markdown; `templates/` 참조
- Review는 읽기 전용 — findings 기록 후 worker에게 handoff
- Verification은 실제 명령만 (hallucinated command 금지)
- 산출물 경로: `.forgeflow/tasks/<task-id>/`
- Project active evolution rules는 required; global rules는 advisory only

릴리즈 버전은 루트 `VERSION` 파일이 기준입니다. Per-skill frontmatter `version`은 skill schema 버전이며 릴리즈 `VERSION`과 별개입니다.
