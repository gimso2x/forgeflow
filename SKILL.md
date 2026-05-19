---
name: forgeflow
description: Artifact-first delivery workflow for AI coding agents — clarify, plan, execute, review, ship through markdown artifacts and prompt-driven gates
version: "1.0.0"
category: engineering
tags: [ai-agents, workflow, artifacts, claude-code, codex, gemini]
---

# ForgeFlow

ForgeFlow는 Claude Code, Codex, Gemini CLI를 위한 artifact-first delivery workflow입니다. AI coding agent 작업을 채팅 기억이 아니라 **명시적인 stage, markdown 산출물, 프롬프트 기반 gate, 독립 review**로 진행하게 만듭니다.

## Core Workflow

```text
user request
  → clarify    # 요구사항 정리 → brief.md
  → milestone  # (Epic 전용) 마일스톤 분해 → roadmap.md
  → plan       # 작업 계획 → plan.md (medium/high/epic)
  → execute    # 구현, updates implementation-notes.md
  → review     # 독립 검증 → review-report.md
  → ship       # 배포/마무리
  → long-run   # (high-risk only) 재사용 학습 → eval-record.md
```

## Routes (자동 선택)

| Route   | Stages                                              | When                      |
|---------|-----------------------------------------------------|---------------------------|
| small   | clarify → execute → review → ship                   | 저위험, 소규모, 쉬운 롤백  |
| medium  | clarify → plan → execute → review → ship            | 범위 명확, 검증 필요       |
| high    | clarify → plan → execute → review → ship → long-run | 아키텍처 영향, 롤백 어려움 |
| epic    | clarify → milestone → plan → execute → review → ship → long-run | 대규모, 멀티윅       |

## Artifacts

`.forgeflow/tasks/<task-id>/` 에 markdown artifact로 상태를 기록:

- `brief.md` — 요구사항, 라우트, 제약사항
- `roadmap.md` — Epic 전용 마일스톤 및 진행 상태
- `plan.md` — 작업 계획 (task 분해, 검증, 의존성)
- `implementation-notes.md` — 실행 진행 상태, 결정 기록, 편차
- `review-report.md` — review 결과 (spec + quality)
- `eval-record.md` — 재사용 학습 기록 (high-risk)

## Slash Skills

```text
/forgeflow-init     — task 생성 (task-id, objective)
/forgeflow:clarify  — 요구사항 정리
/forgeflow:milestone — Epic 전용 마일스톤 관리
/forgeflow:plan     — 계획 수립
/forgeflow:execute  — 구현 실행
/forgeflow:review   — 독립 검증
/forgeflow:ship     — 배포/마무리
/forgeflow:long-run — 학습 기록 (high-risk route only)
/forgeflow:finish   — 정리 및 종료
```

## Conventions

- Artifact는 항상 Markdown. templates/ 디렉토리에 템플릿이 있습니다.
- Review는 읽기 전용. 코드 수정 금지 — findings에 기록 후 worker에게 돌려보냄.
- Verification은 실제 명령 기반. hallucinated command 금지.
