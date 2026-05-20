# Adapter Configuration

ForgeFlow는 여러 AI 에이전트 어댑터를 지원합니다. 각 어댑터의 CLI 호출 방식, 권한, 출력 특성을 추상화한 **canonical 참조 문서**입니다.
스킬에서 어댑터별 동작이 필요하면 이 파일을 기준으로 합니다.

## 어댑터 CLI 플래그

### Claude Code

| 항목 | 값 |
|------|-----|
| 비인터랙티브 실행 | `claude -p "프롬프트"` |
| 권한 우회 | `--dangerously-skip-permissions` |
| 출력 포맷 | `--output-format text \| json \| stream-json` |
| 모델 지정 | `--model sonnet \| opus \| haiku` |
| 디렉토리 trust | 자동 (필요 없음) |
| 출력 특성 | 간결 (평균 ~500자) |
| 커스텀 시스템 프롬프트 | `--system-prompt` 또는 `--append-system-prompt` |

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

| 항목 | 값 |
|------|-----|
| 실행 방식 | Cursor IDE Agent + slash commands (외부 CLI 없음) |
| 설치 | `~/.cursor/plugins/local/forgeflow` symlink → `Developer: Reload Window` |
| Slash 형식 | 콜론 없음: `/clarify`, `/execute`, `/review` (Claude/Codex/Gemini는 `/forgeflow:clarify`) |
| 권한 | IDE sandbox + 사용자 승인 (MCP, 터미널, 파일 쓰기) |
| 템플릿 해석 | `<workspace>/templates/` 우선, 없으면 plugin `templates/` (see `skills/forgeflow/SKILL.md`) |
| 산출물 경로 | 항상 `<workspace>/.forgeflow/tasks/<task-id>/` (plugin cache에 쓰지 않음) |
| 출력 특성 | IDE-native; artifact는 파일로 직접 작성 |

## 성능 참조

벤치마크 기반 예상 소요 시간 (Vite + React + TypeScript 프로젝트):

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

**Opt-in `subagent-execute`:** high/epic에서 plan step마다 subagent + micro-review 루프를 쓸 때도 동일한 artifact·검증 계약을 따릅니다. micro-gate 결과는 `implementation-notes.md`에만 기록하고, stage `review-report.md`는 `/forgeflow:review`에서 작성합니다.

## 출력 정규화

어댑터 출력을 ForgeFlow artifact로 파싱할 때 적용하는 정규화 규칙:

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

스킬 내에서 조건부 동작이 필요한 경우 이 표를 참조합니다.
Slash command 매핑은 `skills/forgeflow/SKILL.md`의 Slash-style entrypoints 표를 따릅니다.
