# Claude Code에서 ForgeFlow 사용하기

## 설치

Claude Code에 ForgeFlow marketplace를 추가하고 plugin을 설치합니다.

```text
/plugin marketplace add https://github.com/gimso2x/forgeflow
/plugin install forgeflow
```

터미널에서 같은 작업을 CLI로:

```bash
claude plugin marketplace add https://github.com/gimso2x/forgeflow
claude plugin install forgeflow
```

설치 후 새 Claude Code 세션을 열면 바로 사용할 수 있습니다.

## 업데이트

```bash
claude plugin marketplace update forgeflow
claude plugin update forgeflow@forgeflow
claude plugin list
```

`plugin update`가 "already at the latest version"이라고 나오는데 새 slash skill이 반영되지 않으면, repo의 `.claude-plugin/plugin.json` version이 올라갔는지 확인하세요.

## 첫 작업

```text
/forgeflow:clarify README 퀵스타트 섹션 개선해줘
```

agent가 요구사항을 정리하고 다음 단계를 제안합니다. 작은 수정은 `clarify` → `run` → `finish`로 끝나고, 리스크 있는 작업은 `plan`과 `review`를 거칩니다.

새 작업 폴더와 task-local agent scaffold를 먼저 만들고 싶으면:

```text
/forgeflow:init --task-id my-task-001 --objective "인증 모듈 리팩토링" --risk high
```

## Slash 명령어

- `/forgeflow:clarify <하고 싶은 작업>` — 요구사항 정리
- `/forgeflow:plan` — 실행 계획 수립
- `/forgeflow:execute` — 승인된 계획 실행
- `/forgeflow:review` — 독립 검토
- `/forgeflow:ship` — 핸드오프 정리
- `/forgeflow:finish` — 작업 완료

`/review`, `/ship` 같은 짧은 이름은 다른 plugin과 충돌할 수 있으므로 `/forgeflow:<stage>` 형식을 권장합니다.

## Init scaffold

`/forgeflow:init`은 `.forgeflow/tasks/<task-id>/` 아래에 작업 폴더를 만듭니다.

생성물:
- **Runtime state**: `brief.json`, `run-state.json`, `checkpoint.json`, `session-state.json`
- **Draft docs**: `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/QA.md`, `docs/DECISIONS.md`
- **Task-local agents**: `.claude/agents/planner.md`, `.claude/agents/implementer.md`, `.claude/agents/qa.md`, `.claude/agents/reviewer.md`
- **Task-local skills**: `.claude/skills/plan/SKILL.md`, `.claude/skills/build/SKILL.md`, `.claude/skills/qa-fix/SKILL.md`, `.claude/skills/review/SKILL.md`

전부 `.forgeflow/tasks/<task-id>/` 아래에만 생성됩니다. 설치 디렉터리나 전역 Claude 설정은 건드리지 않습니다.

## 설치 후 검증

repo checkout에서 post-install smoke를 실행합니다:

```bash
scripts/smoke.sh
```

generated plugin/adapter 파일, canonical route vocabulary, `/forgeflow:clarify` dry-run을 확인합니다. 실패하면 reinstall/restart/check next step을 출력합니다.

## 문제 해결

- **slash 명령어가 안 보이면**: Claude Code 재시작 후 다시 시도
- **plugin update가 반영 안 되면**: `claude plugin list`에서 version 확인. `.claude-plugin/plugin.json` version과 비교
- **task artifact가 안 생기면**: 작업 디렉터리가 `.claude`나 `.codex` plugin cache 안에 있으면 안 됩니다. 프로젝트 루트에서 실행하세요
