# Codex에서 ForgeFlow 사용하기

## 설치

bootstrap 스크립트로 로컬 plugin marketplace에 ForgeFlow를 등록합니다.

```bash
curl -fsSL https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python3 - --force
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python - --force
```

기존 ForgeFlow checkout이 있으면:

```bash
python3 scripts/install_codex_plugin.py
```

설치 후 Codex Desktop을 재시작하고, local marketplace에서 ForgeFlow를 enable합니다.

생성되는 파일:

```text
~/plugins/forgeflow/
~/.agents/plugins/marketplace.json
```

버전 확인:

```powershell
(Get-Content "$HOME\plugins\forgeflow\.codex-plugin\plugin.json" | ConvertFrom-Json).version
```

## 설치 진단

파일을 변경하지 않고 설치 상태를 점검합니다:

```bash
python3 scripts/codex_plugin_doctor.py --project /path/to/your-project
```

Codex CLI, local marketplace, plugin root, project preset/CODEX 상태를 읽기 전용으로 확인합니다.

## 첫 작업

Codex에서 slash-style prompt로 사용합니다. Claude와 같은 명령어 표면입니다.

```text
/forgeflow:clarify 버튼 컴포넌트 접근성 개선해줘
```

```text
/forgeflow:init --task-id refactor-auth --objective "인증 모듈 리팩토링" --risk high
```

사용 가능한 명령어:

- `/forgeflow:clarify <task>` — 요구사항 정리
- `/forgeflow:plan` — 실행 계획 수립
- `/forgeflow:execute` — 승인된 계획 실행
- `/forgeflow:review` — 독립 검토
- `/forgeflow:ship` — 핸드오프 정리
- `/forgeflow:finish` — 작업 완료

Codex plugin은 Claude-style native slash command가 아니라 skill로 동작합니다. ForgeFlow skill이 slash-style prompt를 trigger로 받아서 같은 흐름을 실행합니다.

## 프로젝트 로컬 프리셋 (선택)

plugin 외에 프로젝트에 영구 규칙이 필요할 때 preset을 설치합니다:

```bash
python3 scripts/install_agent_presets.py --adapter codex --target /path/to/your-project --profile nextjs --install-codex-md
```

생성되는 파일:

```text
/path/to/your-project/CODEX.md
/path/to/your-project/.codex/forgeflow/forgeflow-coordinator.md
/path/to/your-project/.codex/forgeflow/forgeflow-nextjs-worker.md
/path/to/your-project/.codex/forgeflow/forgeflow-quality-reviewer.md
/path/to/your-project/.codex/rules/forgeflow-nextjs-worker.mdc
/path/to/your-project/docs/forgeflow-team-init.md
```

`CODEX.md`가 이미 있으면 보존합니다. 교체하려면 `--overwrite-codex-md`를 명시하세요.

## CODEX.md vs Plugin vs Project Preset

- **Plugin**: 기본 진입점. 모든 프로젝트에서 사용
- **CODEX.md**: 프로젝트에 영구 규칙을 추가할 때
- **Project preset**: 역할별 agent 프롬프트(coordinator, worker, reviewer)를 프로젝트에 설치

세 겹이 필요한 게 아니라, plugin만으로 충분한 경우가 대부분입니다.

## 운영 원칙

- local plugin marketplace를 기본 진입점으로 사용
- 새 작업은 `/forgeflow:clarify <task>`로 시작
- task artifact는 항상 `.forgeflow/tasks/<task-id>/` 아래에
- `.codex/forgeflow` preset은 역할 프롬프트지 두 번째 runtime이 아님
- 실제 CLI 실행이 필요하면 `scripts/run_orchestrator.py ... --adapter codex --real`

## 문제 해결

- **plugin이 안 보이면**: Codex Desktop 재시작 후 local marketplace에서 enable 확인
- **버전이 안 올라가면**: `rm -rf ~/plugins/forgeflow` 후 bootstrap 재실행
- **slash prompt가 인식 안 되면**: Codex Desktop에서 plugin이 active 상태인지 확인
