# Windows에서 ForgeFlow 사용하기

ForgeFlow Python runtime은 크로스플랫폼입니다. 셸 표면만 Windows 경로 처리 때문에 별도 진입점이 필요합니다.

## PowerShell 설정

ForgeFlow checkout에서:

```powershell
.\scripts\setup.ps1
.\scripts\validate.ps1
```

`setup.ps1`은 `.venv`를 만들고, `requirements.txt`를 설치하고, 환경 체크를 실행합니다.
`validate.ps1`은 같은 virtualenv로 핵심 검증 세트를 돌립니다.

Python 탐색 순서: `$env:PYTHON` → `python` → `py -3` → `python3`

## Operator CLI

```powershell
.\scripts\run_orchestrator.ps1 init --task-id my-task-001 --objective "Update README quickstart" --risk low
.\scripts\run_orchestrator.ps1 status --task-dir .\.forgeflow\tasks\my-task-001
```

Python runtime은 subprocess argument list로 로컬 체크를 실행합니다. POSIX shell pipe가 아니므로 `>/dev/null`, `2>&1` 같은 Unix 전용 문법은 피하세요.

## Codex Plugin

```powershell
# checkout에서 설치
.\scripts\install_codex_plugin.ps1

# checkout 없이 bootstrap
irm https://raw.githubusercontent.com/gimso2x/forgeflow/main/scripts/bootstrap_codex_plugin.py | python - -- --force
```

`python`이 PATH에 없어도 `py -3`이 있으면 checkout에서 `.\\scripts\\install_codex_plugin.ps1`로 설치할 수 있습니다.

버전 확인:

```powershell
(Get-Content "$HOME\plugins\forgeflow\.codex-plugin\plugin.json" | ConvertFrom-Json).version
```

## Make

GNU Make도 지원합니다. Windows에서는 `OS=Windows_NT`일 때 `.venv/Scripts/python`을 사용합니다.

## WSL / Git Bash

WSL과 Git Bash에서는 Unix-oriented 명령어를 그대로 사용합니다:

```bash
make setup
make check-env
make validate
```

## 주의사항

- native Windows에서는 PowerShell wrapper 우선
- task artifact를 plugin cache(`.codex`, `.claude`) 안에 만들지 마세요. 명시적 프로젝트 디렉터리 사용
- GitHub Actions `windows-smoke` job이 `setup.ps1` → `validate.ps1` → `run_orchestrator.ps1 init` 흐름을 검증합니다
