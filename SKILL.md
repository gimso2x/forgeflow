---
name: forgeflow
description: Artifact-first delivery workflow for AI coding agents
version: "1.0.2"
category: engineering
tags: [ai-agents, workflow, artifacts, claude-code, codex, gemini]
---

# ForgeFlow

ForgeFlow는 Claude Code, Codex, Gemini CLI를 위한 artifact-first delivery workflow입니다.
AI coding agent 작업을 채팅 기억이 아니라 **명시적인 stage, markdown 산출물, 프롬프트 기반 gate, 독립 review**로 진행하게 만듭니다.

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

## Route scoring 기준

v1.x는 Python 런타임을 제거했지만 route 판단은 v0.x의 weighted scoring 기준을 문서 계약으로 유지합니다.

```text
raw_score = file_count*1.0 + estimated_lines*0.1 + requirement_count*2.0 + dependency_count*1.5 + risk_keywords*3.0
```

| Score | Route 판단 |
|---:|---|
| `< 10` | small |
| `10-16.9` | medium-light |
| `17-24.9` | medium-full |
| `25-49.9` | high |
| `>= 50` | epic |

`17.0`은 medium 내부의 light/full 경계입니다.
Python `complexity.py`가 없으므로 이 값을 바꾸면 `skills/clarify/SKILL.md`, `skills/forgeflow/SKILL.md`, README의 기준을 함께 갱신해야 합니다.

## Artifacts

`.forgeflow/tasks/<task-id>/` 에 markdown artifact로 상태를 기록:

- `brief.md` — 요구사항, 라우트, 제약사항
- `roadmap.md` — Epic 전용 마일스톤 및 진행 상태
- `plan.md` — 작업 계획 (task 분해, 검증, 의존성)
- `run-ledger.md` — 실행 truth (task별 pending/running/done/blocked 상태)
- `checkpoint.md` — 재개용 전술 포인터 (context compaction 후 복구)
- `implementation-notes.md` — 실행 진행 상태, 결정 기록, 편차
- `review-report.md` — review 결과 (spec + quality)
- `eval-record.md` — 재사용 학습 기록 (high-risk)
- `evolution-rule.md` — 반복 패턴/실수를 다음 작업에 적용하는 규칙 (template: `templates/evolution-rule.md`)

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
- 역할 분리: 구현 세션과 리뷰 세션은 분리. 구현자의 자체 승인은 승인이 아님.
- 진화 규칙: `.forgeflow/evolution/`에 저장. long-run이 `proposed/`에 후보를 만들고, review 승인 후 `active/`로 활성화합니다.
- Active project rules는 다음 clarify/plan/execute에서 자동으로 읽어 적용합니다.
- Global rules(`~/.forgeflow/evolution/active/*.md`)는 advisory only이며 hard block하지 않습니다.
- 실제 외부 호출: v1.x에는 Python `exec-stage --real` 런타임이 없습니다.
- 향후 `--real` 또는 live adapter 경로를 추가하면 기본값은 stub/dry-run이고, 실제 CLI/API 호출 전 stderr 경고와 `[y/N]` 확인 프롬프트가 필수입니다.

## Evolution rule lifecycle

- `long-run`
  - 생성/진입 조건: high/epic 완료 후 반복 실수, review finding, eval failure, operator note가 evidence로 남음
  - 산출물: `eval-record.md`, `.forgeflow/evolution/proposed/*.md`
  - 승인/적용 조건: 후보 규칙은 `Review Status: unreviewed`로 시작
- `proposed`
  - 생성/진입 조건: `templates/evolution-rule.md`의 필수 필드가 채워짐
  - 산출물: `Lifecycle: proposed`
  - 승인/적용 조건: review가 evidence와 false-positive guard를 검증
- `review`
  - 생성/진입 조건: reviewer가 read-only로 후보 규칙을 평가
  - 산출물: `review-report.md` Evolution Rule Review
  - 승인/적용 조건: approved면 active로 승격, rejected면 폐기
- `active`
  - 생성/진입 조건: 프로젝트 규칙으로 승인됨
  - 산출물: `.forgeflow/evolution/active/*.md`
  - 승인/적용 조건: 다음 clarify/plan/execute에서 trigger/stage가 맞으면 required constraint
- `retired`
  - 생성/진입 조건: 규칙이 해롭거나 더 이상 맞지 않음
  - 산출물: `.forgeflow/evolution/retired/*.md`
  - 승인/적용 조건: retirement reason과 rollback 근거 필요
