# Adapter Configuration

ForgeFlow는 여러 AI 에이전트 어댑터를 지원합니다. 각 어댑터의 CLI 호출 방식, 권한, 출력 특성을 추상화한 **canonical 참조 문서**입니다.
스킬에서 어댑터별 동작이 필요하면 이 파일을 기준으로 합니다.

**작업 위치 원칙:** plugin/extension 설치·cache 위치와 실제 workflow 대상 프로젝트 루트를 분리합니다. `/forgeflow:clarify`, `/forgeflow:execute` 같은 stage 명령은 변경하려는 프로젝트 루트에서 실행하고, 산출물은 그 프로젝트의 `.forgeflow/tasks/<task-id>/` 아래에 기록해야 합니다. 어댑터 cache 안에서 실행 중이면 `--task-dir <project>/.forgeflow/tasks/<task-id>`처럼 명시 경로를 사용합니다.

## Multi-harness routing invariants

ForgeFlow의 core contract는 `skills/`, `templates/`, `docs/review-runtime-contract.md`에 있고, Claude Code/Codex/Gemini/Cursor는 얇은 harness wrapper로만 동작합니다. 새 어댑터나 기존 어댑터별 예외를 추가할 때는 먼저 이 불변식을 확인합니다.

- **Canonical stage contract first**: route, artifact schema, verdict enum, human review gate, verification gate는 어댑터별로 갈라지지 않습니다. 차이가 필요하면 skill/template contract를 먼저 수정하고 모든 어댑터가 같은 contract를 따르게 합니다.
- **Harness-specific code paths stay shallow**: 어댑터별 차이는 slash command 이름, CLI flag, trust/permission mode, output normalization, timeout hint에 한정합니다. 판단 로직, role routing, approval/ship behavior는 어댑터 wrapper에 두지 않습니다.
- **Artifact handoff is the boundary**: 어댑터가 다른 도구나 subagent로 넘길 때도 `.forgeflow/tasks/<task-id>/` markdown artifact가 handoff source of truth입니다. Chat transcript, provider memory, hidden tool state는 다음 stage 입력으로 간주하지 않습니다.
- **Review adapters normalize before judging**: standalone review entrypoint는 `input-source.md`와 `normalized-input.md`를 먼저 남긴 뒤 canonical review skill에 위임합니다. Adapter별 별도 `review-report.md`, 자동 승인, hidden fallback은 금지합니다.
- **Validation follows touched surface**: adapter behavior를 바꾸면 focused target으로 `make validate-adapter-config validate-advisory-contract validate-markdown-links`를 실행하고, 마지막에 `make validate`로 전체 markdown contract drift를 확인합니다.

## 어댑터 CLI 플래그

### Claude Code

Claude Code plugin 설치는 Claude의 plugin/marketplace 위치에서 수행할 수 있지만, `/forgeflow:clarify`, `/forgeflow:execute` 같은 slash command는 **대상 프로젝트 루트**에서 실행합니다. ForgeFlow checkout이나 plugin cache 컨텍스트에서 열렸다면 `--task-dir <project>/.forgeflow/tasks/<task-id>`로 산출물 위치를 명시합니다.

Release 또는 dogfood smoke에서는 설치된 user-scope plugin 버전과 repo `VERSION` 드리프트를 먼저 확인합니다. `--plugin-dir /path/to/forgeflow`는 checkout 검증용이며, 실제 설치 plugin 검증에서는 빼야 합니다. 업데이트 후 Claude Code가 "Restart to apply changes"를 출력하면 새 Claude 프로세스에서 smoke를 다시 실행합니다.

- **비인터랙티브 실행**: `claude -p "프롬프트"`
- **권한 우회**: `--dangerously-skip-permissions` 또는 disposable smoke에서 `--permission-mode bypassPermissions`
- **출력 포맷**: `--output-format text | json | stream-json`
- **모델 지정**: `--model sonnet | opus | haiku`
- **디렉토리 trust**: 자동 (필요 없음)
- **출력 특성**: 간결 (평균 ~500자)
- **커스텀 시스템 프롬프트**: `--system-prompt` 또는 `--append-system-prompt`
- **설치 버전 확인**: `claude plugin list`
- **설치 plugin 업데이트**: `claude plugin update forgeflow@forgeflow` → restart/new process → `claude plugin list`
- **Checkout 검증**: `claude -p --plugin-dir /path/to/forgeflow "..."`
- **설치 plugin 검증**: `claude -p "..."` (`--plugin-dir` 없이 실행)

### Codex CLI

Codex plugin 파일 복사와 slash command 실행은 **대상 프로젝트 루트**에서 수행합니다. ForgeFlow checkout이나 Codex plugin cache 안에서 실행하면 `.forgeflow/tasks/<task-id>/` 산출물이 잘못된 위치에 생길 수 있습니다.

| 항목 | 값 |
|------|-----|
| 비인터랙티브 실행 | `codex exec "프롬프트"` |
| 권한 우회 | `-s danger-full-access` |
| 샌드박스 모드 | `-s read-only \| workspace-write \| danger-full-access` |
| 디렉토리 trust | git repo 필수 (없으면 `--skip-git-repo-check` 필요) |
| 출력 특성 | 상세 diff 포함 (평균 ~200KB, diff 84%) |
| 추가 검증 | `build` + `lint` 자동 실행 |

### Gemini CLI

Gemini extension 설치·업데이트는 extension manager/cache에서 처리될 수 있지만, `/forgeflow:clarify`, `/forgeflow:execute` 같은 workflow 명령은 **대상 프로젝트 루트**에서 실행합니다. Disposable 또는 untrusted repo에서 headless smoke를 실행할 때는 `--skip-trust`를 함께 사용하고, cache 컨텍스트에서 열렸다면 `--task-dir <project>/.forgeflow/tasks/<task-id>`로 산출물 위치를 명시합니다.

| 항목 | 값 |
|------|-----|
| 비인터랙티브 실행 | `gemini -p "프롬프트"` |
| 권한 우회 | `--yolo` |
| 승인 모드 | `--approval-mode default \| auto_edit \| yolo \| plan` |
| 디렉토리 trust | `--skip-trust` 필요할 수 있음 |
| 출력 포맷 | `--output-format text \| json \| stream-json` |
| Extension 설치 | `gemini extensions install https://github.com/gimso2x/forgeflow` |
| Extension 업데이트 | `printf 'Y\n' \| gemini extensions update forgeflow` |
| Extension 설치 확인 | `gemini extensions list` |
| Extension 검증/연결 | `gemini extensions validate .` → `gemini extensions link .` |
| 출력 특성 | 구조화된 마크다운 (평균 ~2.5KB) |

`gemini extensions update forgeflow`는 확인 프롬프트가 뜰 수 있으므로 자동화에서는 명시 승인 입력을 파이프합니다. 업데이트 후 `gemini extensions list`로 설치된 `forgeflow` extension을 확인합니다.

### Cursor (로컬 플러그인)

Cursor plugin symlink/install은 Cursor의 local plugin 위치에서 관리하지만, `/clarify`, `/execute` 같은 workflow 명령은 **대상 프로젝트 루트**에서 실행합니다. Plugin cache나 ForgeFlow checkout에서 열린 세션이면 `<workspace>/.forgeflow/tasks/<task-id>/` 산출물 경로를 명시하고, cache 내부에 task artifact를 만들지 않습니다.

| 항목 | 값 |
|------|-----|
| 실행 방식 | Cursor IDE Agent + slash commands (외부 CLI 없음) |
| 설치 | `~/.cursor/plugins/local/forgeflow` symlink → `Developer: Reload Window` |
| Slash 형식 | 콜론 없음: `/clarify`, `/plan`, `/execute`, `/review`, `/ship` (Claude/Codex/Gemini는 `/forgeflow:clarify`) |
| 권한 | IDE sandbox + 사용자 승인 (MCP, 터미널, 파일 쓰기) |
| 템플릿 해석 | `<workspace>/templates/` 우선, 없으면 plugin `templates/` (see `skills/forgeflow/SKILL.md`) |
| 산출물 경로 | 항상 `<workspace>/.forgeflow/tasks/<task-id>/` (plugin cache에 쓰지 않음) |
| Context resume | `checkpoint.md` 우선 재개; see `skills/_shared/context-resume.md` |
| 출력 특성 | IDE-native; artifact는 파일로 직접 작성 |

## 성능 참조

벤치마크 기반 예상 소요 시간 (Vite + React + TypeScript 프로젝트):
이 표는 historical reference이며 현재 live provider SLA나 이번 checkout에서 검증된 provider/plugin E2E 결과가 아닙니다.

| 어댑터 | Small (정적 페이지) | Medium (API+폼) | 예상 배율 |
|--------|---------------------|------------------|-----------|
| Gemini CLI | ~56s | ~101s | 1x (기준) |
| Claude Code | ~64s | ~243s | 1.1-2.4x |
| Codex CLI | ~119s | ~148s | 1.8-1.5x |
| Cursor | (IDE-bound, 벤치마크 미포함) | — | — |

### 타임아웃 가이드

| 작업 규모 | Gemini | Claude | Codex | Cursor | 안전 상한 |
|----------|--------|--------|-------|--------|-----------|
| small | 120s | 120s | 180s | 180s | 300s |
| medium | 180s | 360s | 240s | 360s | 600s |
| high | 300s | 600s | 480s | 600s | 900s |
| epic | 600s | 1200s | 900s | 1200s | 1800s |

타임아웃 초과 시 어댑터 프로세스를 종료하고 `implementation-notes.md`에 기록.

## 검증 명령 표준

어댑터에 상관없이 동일한 검증 체크리스트를 사용:

| 게이트 | 명령 | 적용 조건 |
|--------|------|-----------|
| `build` | 프로젝트 빌드 명령 | 모든 코드 작업 |
| `lint` | 프로젝트 lint 명령 | lint 설정이 있는 경우 |
| `type_check` | `tsc --noEmit` 또는 동등 | TypeScript 프로젝트 |
| `test` | 프로젝트 테스트 명령 | 테스트가 있는 경우 |

각 어댑터는 `execute` 스테이지 종료 시 **최소 1개** 이상의 검증을 실행해야 합니다.
`review` 스테이지는 검증을 독립적으로 재실행합니다.

**Opt-in subagent per-task (`/forgeflow:execute --subagent-per-task`):** high/epic에서 plan step마다 subagent + micro-review 루프를 쓸 때도 동일한 artifact·검증 계약을 따릅니다. micro-gate 결과는 `implementation-notes.md`에만 기록하고, stage `review-report.md`는 `/forgeflow:review`에서 작성합니다.

## 출력 정규화

어댑터 출력을 ForgeFlow artifact로 파싱할 때 적용하는 정규화 규칙:

Artifact는 긴 표보다 bullet list를 우선합니다. 작은 metrics matrix처럼 행/열 비교가 꼭 필요한 경우에만 Markdown table을 사용하고, Telegram/CLI/IDE transcript에 붙여도 읽히도록 핵심 verdict, changed files, verification evidence, next action은 bullet 형태로도 남깁니다.

### Codex diff 정규화

Codex는 전체 git diff를 출력하므로 다음 후처리를 적용:

1. `---` / `+++` / `@@` 헤더 라인 제거
2. diff 통계 라인 제거 (`files changed`, `insertions`, `deletions`)
3. 실제 코드 변경과 에이전트 메시지를 분리
4. 최종 요약 섹션만 artifact로 추출

### 공통 정규화

모든 어댑터에 적용:

1. ANSI 이스케이프 시퀀스 제거
2. 프롬프트 캐시/메모리 로그 제거
3. 핵심 산출물(보고서, 파일 목록, 검증 결과)만 유지

## 어댑터 감지

현재 실행 중인 어댑터를 감지하는 방법 (우선순위: env var → adapter 디렉토리):

| 어댑터 | 환경 변수 | 디렉토리/기타 신호 |
|--------|-----------|-------------------|
| Claude Code | `CLAUDE_CODE_SESSION=1` | `.claude/` 디렉토리 존재 |
| Codex CLI | `CODEX_SESSION=1` | `.codex/` 디렉토리 존재 |
| Gemini CLI | `GEMINI_CLI=1` | `.gemini/` 디렉토리 존재 |
| Cursor | — | `.cursor/` 디렉토리 존재 (다른 adapter env signal 없을 때) |

## 프로젝트 기본값 (Project Defaults)

프로젝트 루트에 `.forgeflow/defaults.md`를 두면 모든 태스크에 적용할 기본값을 설정할 수 있습니다.

```markdown
# ForgeFlow Defaults

- **auto**: true
- **isolation**: true
```

지원 필드:

| 필드 | 기본값 | 설명 |
|------|--------|------|
| `auto` | `false` | `true`면 clarify 이후 전체 스테이지 자동 체이닝 (`--auto`와 동일) |
| `isolation` | `true` | `true`면 medium/high/epic 라우트에서 worktree 격리 사용 (`--no-isolation`으로 비활성화) |

우선순위: CLI 플래그 > `brief.md` 필드 > `.forgeflow/defaults.md` > 기본값 (필드별 상이)

스킬 내에서 조건부 동작이 필요한 경우 이 표를 참조합니다.
Slash command 매핑은 `skills/forgeflow/SKILL.md`의 Slash-style entrypoints 표를 따릅니다.
