# ForgeFlow

ForgeFlow는 AI coding agent를 위한 artifact-first delivery workflow입니다. 채팅 기억에 의존하지 않고 **명시적인 markdown 산출물, 프롬프트 기반 게이트, 독립 review**로 작업하게 만듭니다.

현재 릴리즈: **v1.0.0**

## 누가 왜 쓰나

- AI 코딩 에이전트로 **실제 프로덕션 코드**를 작성하는 개발자
- 에이전트의 작업을 **검증 가능한 산출물**로 추적하고 싶은 팀
- "에이전트가 뭘 했는지 모르겠다"는 문제를 해결하고 싶은 사람

## 30초 퀵스타트

**Claude Code:**

```
/plugin marketplace add https://github.com/gimso2x/forgeflow
/plugin install forgeflow
```

**Gemini CLI:**
```
gemini extensions install https://github.com/gimso2x/forgeflow
```

**Codex:**
```
# .codex-plugin/plugin.json을 프로젝트에 복사
```

## 기본 워크플로우

```text
/forgeflow:clarify   → 요구사항 정리 → brief.md
/forgeflow:plan      → 작업 계획 → plan.md        (medium 이상)
/forgeflow:execute   → 구현 실행 → implementation-notes.md
/forgeflow:review    → 독립 검증 → review-report.md
/forgeflow:ship      → 배포/마무리
/forgeflow:finish    → 브랜치 정리
```

## Routes (자동 선택)

clarify 스킬이 복잡도를 평가하여 자동으로 라우트를 선택합니다:

| Route   | Stages                                              | When                      |
|---------|-----------------------------------------------------|---------------------------|
| small   | clarify → execute → review → ship                   | 저위험, 소규모, 쉬운 롤백  |
| medium  | clarify → plan → execute → review → ship            | 범위 명확, 검증 필요       |
| high    | clarify → plan → execute → review → ship → long-run | 아키텍처 영향, 롤백 어려움 |
| epic    | clarify → milestone → plan → execute → review → ship → long-run | 대규모, 멀티윅       |

## Artifacts

모든 산출물은 `.forgeflow/tasks/<task-id>/` 아래에 markdown 파일로 기록됩니다:

| 산출물 | 설명 | 라우트 |
|---|---|---|
| `brief.md` | 요구사항, 라우트, 제약사항 | 전체 |
| `plan.md` | 작업 계획, 태스크 분해, 검증 | medium+ |
| `implementation-notes.md` | 실행 진행, 결정 기록, 편차 | 전체 |
| `review-report.md` | 독립 검증 결과 | 전체 |
| `roadmap.md` | 마일스톤 분해 | epic |
| `eval-record.md` | 학습 기록 | high+ |

## 특징

- **의존성 제로** — Python, Node.js 등 외부 런타임 불필요
- **순수 Markdown** — 모든 산출물이 사람이 읽을 수 있는 markdown
- **프롬프트 기반** — 스크립트가 아닌 프롬프트 지시로 강제
- **멀티 플랫폼** — Claude Code, Codex, Gemini CLI 지원

## 첫 실행 예시

```text
> /forgeflow:clarify 로그인 페이지에 소셜 로그인 버튼 추가
# → brief.md 생성, route: small

> /forgeflow:execute
# → 구현 진행, implementation-notes.md 업데이트

> /forgeflow:review
# → 독립 review, review-report.md 생성

> /forgeflow:ship
# → 변경 요약, PR 준비
```

## 라이선스

MIT
